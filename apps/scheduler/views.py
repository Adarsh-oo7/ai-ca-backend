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
            duration_hours=actual_duration / 60.0,
            topic_id=task.topic.id if task.topic else None
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

    @action(detail=False, methods=['post'])
    def auto_schedule(self, request):
        """Generate AI schedules for a date range (max 7 days)."""
        from .tasks import smart_reschedule_for_user

        start_date = request.data.get('start_date', None)
        end_date = request.data.get('end_date', None)

        if not start_date or not end_date:
            return Response({'error': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

        # Validate date range is not too long
        from datetime import datetime as dt
        start = dt.strptime(start_date, '%Y-%m-%d').date()
        end = dt.strptime(end_date, '%Y-%m-%d').date()
        if (end - start).days > 7:
            return Response({'error': 'Maximum 7 days allowed'}, status=status.HTTP_400_BAD_REQUEST)

        # Fire Celery task asynchronously
        smart_reschedule_for_user.delay(str(request.user.id), start_date, end_date)

        return Response({
            'status': 'scheduling',
            'message': f'AI is generating schedules from {start_date} to {end_date}. Refresh in a moment.'
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['post'])
    def reschedule_missed(self, request):
        """Manually trigger rescheduling of yesterday's missed tasks to today."""
        yesterday = (timezone.now().date() - timezone.timedelta(days=1))
        today = timezone.now().date()

        missed_tasks = StudyTask.objects.filter(
            user=request.user,
            scheduled_date=yesterday,
            is_completed=False,
            status__in=['pending', 'in_progress']
        )

        rescheduled_count = 0
        for task in missed_tasks:
            StudyTask.objects.create(
                user=request.user,
                title=f"[Rescheduled] {task.title}",
                description=f"Rescheduled from {yesterday}. {task.description}",
                task_type=task.task_type,
                subject=task.subject,
                chapter=task.chapter,
                topic=task.topic,
                scheduled_date=today,
                duration_minutes=task.duration_minutes,
                priority=max(1, task.priority - 1),
                is_ai_generated=True,
                ai_reason=f"Manually rescheduled from {yesterday}"
            )
            task.status = 'rescheduled'
            task.save(update_fields=['status'])
            rescheduled_count += 1

        return Response({
            'rescheduled': rescheduled_count,
            'message': f'{rescheduled_count} tasks rescheduled to today'
        }, status=status.HTTP_200_OK)



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


class GoogleCalendarViewSet(viewsets.ViewSet):
    """Google Calendar OAuth2 integration endpoints."""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def status(self, request):
        """Check if Google Calendar is connected for the current user."""
        from .models import GoogleCalendarToken
        try:
            token = GoogleCalendarToken.objects.get(user=request.user, is_active=True)
            return Response({
                'connected': True,
                'calendar_id': token.calendar_id,
                'connected_since': token.created_at
            })
        except GoogleCalendarToken.DoesNotExist:
            return Response({'connected': False})

    @action(detail=False, methods=['get'])
    def connect(self, request):
        """Get the OAuth2 authorization URL to connect Google Calendar."""
        try:
            from .calendar_integration import GoogleCalendarService
            auth_url, state = GoogleCalendarService.get_auth_url(request.user)
            return Response({
                'auth_url': auth_url,
                'state': state
            })
        except ValueError as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def callback(self, request):
        """Handle OAuth2 callback with authorization code."""
        auth_code = request.data.get('code', '')
        if not auth_code:
            return Response({'error': 'Authorization code is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from .calendar_integration import GoogleCalendarService
            token_obj = GoogleCalendarService.handle_callback(request.user, auth_code)
            return Response({
                'connected': True,
                'calendar_id': token_obj.calendar_id,
                'message': 'Google Calendar connected successfully'
            })
        except Exception as e:
            return Response({
                'error': f'Failed to connect: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def disconnect(self, request):
        """Disconnect Google Calendar access."""
        from .calendar_integration import GoogleCalendarService
        result = GoogleCalendarService.disconnect(request.user)
        if result:
            return Response({'status': 'disconnected'})
        return Response({'error': 'Google Calendar is not connected'}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def sync(self, request):
        """Sync all study tasks for a given date to Google Calendar."""
        date_str = request.data.get('date', None)
        if not date_str:
            target_date = timezone.now().date()
        else:
            from datetime import datetime as dt
            target_date = dt.strptime(date_str, '%Y-%m-%d').date()

        try:
            from .calendar_integration import GoogleCalendarService
            result = GoogleCalendarService.sync_all_tasks(request.user, target_date)
            return Response(result)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Sync failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

