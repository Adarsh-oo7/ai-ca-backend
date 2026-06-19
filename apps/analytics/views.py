from datetime import datetime, timedelta
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from .models import StudyAnalytics
from .serializers import StudyAnalyticsSerializer
from apps.memory.models import BehaviorProfile, SubjectMemory, ChapterMemory, MemorySummary
from apps.scheduler.models import Attendance, StudyTask
from apps.assessment.models import MockResult, MCQAttempt
from apps.ai_engine.models import SuccessPrediction
from apps.accountability.models import DailyCheckIn
from apps.memory.summarizer import MemorySummarizer

class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Aggregates dashboard stats for the React frontend dashboard shell.
        """
        user = request.user
        today = timezone.now().date()
        
        # 1. Streaks and Total Hours (from Behavior Profile)
        behavior, _ = BehaviorProfile.objects.get_or_create(user=user)
        
        # 2. Today's details
        today_attendance = Attendance.objects.filter(user=user, date=today).first()
        today_hours = today_attendance.hours_studied if today_attendance else 0.0

        # 3. Latest Success Prediction
        latest_pred = SuccessPrediction.objects.filter(user=user).order_by('-computed_at').first()
        readiness = latest_pred.readiness_score if latest_pred else 50.0
        pass_prob = latest_pred.pass_probability if latest_pred else 50.0
        recommendations = latest_pred.recommendations if latest_pred else ["Start your daily check-in to see custom advice!"]

        # 4. Weekly chart data (last 7 days)
        weekly_chart = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            # Find tasks planned vs completed for this day
            day_tasks = StudyTask.objects.filter(user=user, scheduled_date=d)
            planned = sum(t.duration_minutes for t in day_tasks) / 60.0
            completed = sum(t.actual_duration or t.duration_minutes for t in day_tasks.filter(is_completed=True)) / 60.0

            # MCQ accuracy for this day
            day_mcq = MCQAttempt.objects.filter(user=user, created_at__date=d)
            mcq_total = day_mcq.count()
            mcq_correct = day_mcq.filter(is_correct=True).count()
            acc = round((mcq_correct / mcq_total) * 100, 1) if mcq_total > 0 else 0.0

            weekly_chart.append({
                'day': d.strftime("%a"),
                'date': str(d),
                'planned_hours': round(planned, 1),
                'completed_hours': round(completed, 1),
                'mcq_accuracy': acc
            })

        # 5. Subject list progress
        subjects_data = []
        sub_mems = SubjectMemory.objects.filter(user=user)
        for sm in sub_mems:
            # Chapter count
            chap_ids = sm.subject.chapters.values_list('id', flat=True)
            avg_understanding = ChapterMemory.objects.filter(
                user=user, chapter_id__in=chap_ids
            ).aggregate(Avg('understanding_score'))['understanding_score__avg'] or 0.0

            subjects_data.append({
                'subject_id': sm.subject.id,
                'name': sm.subject.name,
                'code': sm.subject.code,
                'color': sm.subject.color,
                'strength': round(sm.strength_score, 1),
                'confidence': round(sm.confidence_score, 1),
                'average_understanding': round(avg_understanding, 1),
                'hours_spent': round(sm.total_time_spent, 1)
            })

        return Response({
            'streak': behavior.study_streak,
            'longest_streak': behavior.longest_streak,
            'total_study_hours': round(behavior.total_study_hours, 1),
            'today_hours': round(today_hours, 1),
            'readiness_score': readiness,
            'pass_probability': pass_prob,
            'recommendations': recommendations,
            'weekly_progress': weekly_chart,
            'subjects': subjects_data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def study_hours(self, request):
        """Get study hours history for custom date range."""
        user = request.user
        start_date_str = request.query_params.get('start_date', None)
        end_date_str = request.query_params.get('end_date', None)

        today = timezone.now().date()
        
        # Defaults to 30 days
        start_date = today - timedelta(days=30)
        end_date = today

        if start_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        if end_date_str:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        records = Attendance.objects.filter(user=user, date__range=(start_date, end_date)).order_by('date')
        
        data = []
        for r in records:
            data.append({
                'date': str(r.date),
                'hours_studied': r.hours_studied,
                'is_present': r.is_present
            })

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='previous-day')
    def previous_day(self, request):
        """
        Returns a detailed report of the student's activities from the previous day.
        """
        user = request.user
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        
        # 1. Study Hours & Attendance for yesterday
        attendance = Attendance.objects.filter(user=user, date=yesterday).first()
        hours_studied = attendance.hours_studied if attendance else 0.0
        is_present = attendance.is_present if attendance else False
        check_in_time = attendance.check_in_time.strftime("%H:%M") if (attendance and attendance.check_in_time) else None
        check_out_time = attendance.check_out_time.strftime("%H:%M") if (attendance and attendance.check_out_time) else None
        attendance_notes = attendance.notes if attendance else ""

        # 2. Study Tasks for yesterday
        tasks = StudyTask.objects.filter(user=user, scheduled_date=yesterday)
        tasks_data = []
        tasks_completed_count = 0
        tasks_total_count = tasks.count()
        for t in tasks:
            if t.is_completed:
                tasks_completed_count += 1
            tasks_data.append({
                'id': str(t.id),
                'title': t.title,
                'task_type': t.get_task_type_display(),
                'status': t.status,
                'priority': t.get_priority_display(),
                'is_completed': t.is_completed,
                'duration_minutes': t.duration_minutes,
                'actual_duration': t.actual_duration or 0,
                'completed_at': t.completed_at.isoformat() if t.completed_at else None,
                'subject': t.subject.name if t.subject else None,
                'chapter': t.chapter.name if t.chapter else None,
            })

        # 3. MCQ Attempts for yesterday
        mcqs = MCQAttempt.objects.filter(user=user, created_at__date=yesterday)
        mcq_total = mcqs.count()
        mcq_correct = mcqs.filter(is_correct=True).count()
        mcq_accuracy = round((mcq_correct / mcq_total) * 100, 1) if mcq_total > 0 else 0.0
        
        mcqs_data = []
        for m in mcqs[:15]: # return last 15 attempts for detail
            mcqs_data.append({
                'id': str(m.id),
                'question_text': m.question_text[:120] + '...' if len(m.question_text) > 120 else m.question_text,
                'is_correct': m.is_correct,
                'selected_answer': m.selected_answer,
                'correct_answer': m.correct_answer,
                'time_taken_seconds': m.time_taken_seconds,
                'subject': m.subject.name if m.subject else None,
                'chapter': m.chapter.name if m.chapter else None,
                'topic': m.topic.name if m.topic else None,
            })

        # 4. Mock Test Results for yesterday
        mocks = MockResult.objects.filter(user=user, completed_at__date=yesterday)
        mocks_data = []
        for m in mocks:
            mocks_data.append({
                'id': str(m.id),
                'test_title': m.test.title,
                'test_type': m.test.get_test_type_display(),
                'score': m.score,
                'total_marks': m.total_marks,
                'accuracy_percentage': m.accuracy_percentage,
                'time_taken_minutes': m.time_taken_minutes,
                'completed_at': m.completed_at.isoformat(),
                'ai_feedback': m.ai_feedback,
            })

        # 5. Daily Check-in for yesterday
        checkin = DailyCheckIn.objects.filter(user=user, date=yesterday).first()
        checkin_data = None
        if checkin:
            checkin_data = {
                'did_study': checkin.did_study,
                'hours_completed': checkin.hours_completed,
                'mood': checkin.get_mood_display(),
                'productivity_rating': checkin.productivity_rating,
                'problems_faced': checkin.problems_faced,
                'notes': checkin.notes,
                'ai_feedback': checkin.ai_feedback,
                'ai_suggestions': checkin.ai_suggestions,
            }

        # 6. Fetch/Generate Daily Memory Summary for yesterday
        yesterday_summary = MemorySummary.objects.filter(user=user, period='daily', period_start=yesterday).first()
        if not yesterday_summary:
            # Only trigger summary generation if there was some study or check-in activity
            has_activity = (hours_studied > 0.0 or tasks_completed_count > 0 or mcq_total > 0 or mocks.exists() or checkin is not None)
            if has_activity:
                # Generate summary dynamically using the summarizer
                yesterday_summary = MemorySummarizer.generate_summary(user, 'daily', yesterday, yesterday)

        summary_data = None
        if yesterday_summary:
            summary_data = {
                'summary_text': yesterday_summary.summary_text,
                'key_insights': yesterday_summary.key_insights,
                'performance_data': yesterday_summary.performance_data
            }

        return Response({
            'date': str(yesterday),
            'hours_studied': round(hours_studied, 1),
            'is_present': is_present,
            'check_in_time': check_in_time,
            'check_out_time': check_out_time,
            'attendance_notes': attendance_notes,
            'tasks_completed': tasks_completed_count,
            'tasks_total': tasks_total_count,
            'tasks': tasks_data,
            'mcq_total': mcq_total,
            'mcq_correct': mcq_correct,
            'mcq_accuracy': mcq_accuracy,
            'mcqs': mcqs_data,
            'mock_results': mocks_data,
            'check_in': checkin_data,
            'ai_summary': summary_data
        }, status=status.HTTP_200_OK)
