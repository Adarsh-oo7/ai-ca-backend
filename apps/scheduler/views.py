from datetime import datetime
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from .models import StudyTask, DailySchedule, WeeklySchedule, MonthlySchedule, ScheduleTemplate, Attendance
from .serializers import (
    StudyTaskSerializer, DailyScheduleSerializer, WeeklyScheduleSerializer,
    MonthlyScheduleSerializer, ScheduleTemplateSerializer, AttendanceSerializer
)
from .planner import AIStudyPlanner
from apps.memory.services import MemoryService

class StudyTaskViewSet(viewsets.ModelViewSet):
    """
    CRUD study tasks. Supports drag-and-drop ordering.
    """
    serializer_class = StudyTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['scheduled_date', 'status', 'priority', 'subject', 'is_completed']
    search_fields = ['title', 'description']
    ordering_fields = ['scheduled_date', 'order', 'scheduled_time']
    ordering = ['scheduled_date', 'order']

    def get_queryset(self):
        return StudyTask.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Mark a study task as completed and log details in memory."""
        task = self.get_object()
        actual_duration = request.data.get('actual_duration', task.duration_minutes)
        
        task.status = 'completed'
        task.is_completed = True
        task.completed_at = timezone.now()
        task.actual_duration = actual_duration
        task.save()

        # 1. Update memory record of study time
        MemoryService.record_study_session(
            user=request.user,
            subject_id=task.subject.id if task.subject else None,
            chapter_id=task.chapter.id if task.chapter else None,
            duration_hours=actual_duration / 60.0
        )

        # 2. Update daily schedule completed hours
        daily_sch = DailySchedule.objects.filter(user=request.user, date=task.scheduled_date).first()
        if daily_sch:
            daily_sch.hours_completed = sum(
                t.actual_duration or t.duration_minutes for t in daily_sch.tasks.filter(is_completed=True)
            ) / 60.0
            daily_sch.save()

        # 3. Update attendance record hours
        attendance, _ = Attendance.objects.get_or_create(
            user=request.user,
            date=task.scheduled_date
        )
        attendance.is_present = True
        attendance.hours_studied = sum(
            t.actual_duration or t.duration_minutes for t in StudyTask.objects.filter(
                user=request.user, scheduled_date=task.scheduled_date, is_completed=True
            )
        ) / 60.0
        attendance.tasks_completed = StudyTask.objects.filter(
            user=request.user, scheduled_date=task.scheduled_date, is_completed=True
        ).count()
        attendance.tasks_total = StudyTask.objects.filter(
            user=request.user, scheduled_date=task.scheduled_date
        ).count()
        attendance.save()

        serializer = self.get_serializer(task)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DailyScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = DailyScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DailySchedule.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get or generate empty schedule for today."""
        today_date = timezone.now().date()
        daily_sch, _ = DailySchedule.objects.get_or_create(user=request.user, date=today_date)
        serializer = self.get_serializer(daily_sch)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Call AI Study Planner to generate full set of tasks for target date."""
        target_date_str = request.data.get('date', None)
        if target_date_str:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        else:
            target_date = timezone.now().date()

        # Remove existing pending AI tasks for this day to avoid duplicates
        StudyTask.objects.filter(
            user=request.user,
            scheduled_date=target_date,
            is_completed=False,
            is_ai_generated=True
        ).delete()

        daily_sch = AIStudyPlanner.generate_daily_schedule(request.user, target_date)
        if daily_sch:
            serializer = self.get_serializer(daily_sch)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response({'error': 'Failed to generate plan'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WeeklyScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = WeeklyScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WeeklySchedule.objects.filter(user=self.request.user)


class MonthlyScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = MonthlyScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MonthlySchedule.objects.filter(user=self.request.user)


class ScheduleTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ScheduleTemplate.objects.filter(is_active=True)
    serializer_class = ScheduleTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Attendance.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def check_in(self, request):
        today = timezone.now().date()
        attendance, created = Attendance.objects.get_or_create(
            user=request.user,
            date=today
        )
        attendance.is_present = True
        attendance.check_in_time = timezone.now().time()
        attendance.save()
        
        # Increment streak in behavior profile
        profile = request.user.behavior_profile
        if not Attendance.objects.filter(user=request.user, date=today - timezone.timedelta(days=1), is_present=True).exists():
            # If they didn't check in yesterday, reset streak to 1
            profile.study_streak = 1
        else:
            # studied yesterday, increment streak
            # Only increment if they haven't checked in already today
            if created or not attendance.check_in_time:
                profile.study_streak += 1
        
        if profile.study_streak > profile.longest_streak:
            profile.longest_streak = profile.study_streak
        profile.save()

        serializer = self.get_serializer(attendance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def check_out(self, request):
        today = timezone.now().date()
        attendance = Attendance.objects.filter(user=request.user, date=today).first()
        if not attendance:
            return Response({'error': 'No check-in record for today'}, status=status.HTTP_400_BAD_REQUEST)
        
        attendance.check_out_time = timezone.now().time()
        attendance.save()

        serializer = self.get_serializer(attendance)
        return Response(serializer.data, status=status.HTTP_200_OK)
