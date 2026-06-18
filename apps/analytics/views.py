from datetime import datetime, timedelta
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum, Avg, Count
from django.utils import timezone
from .models import StudyAnalytics
from .serializers import StudyAnalyticsSerializer
from apps.memory.models import BehaviorProfile, SubjectMemory, ChapterMemory
from apps.scheduler.models import Attendance, StudyTask
from apps.assessment.models import MockResult, MCQAttempt
from apps.ai_engine.models import SuccessPrediction

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
