from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from django.utils import timezone
from .models import RevisionTask
from .serializers import RevisionTaskSerializer
from .sm2 import SM2Algorithm
from apps.memory.models import RevisionHistory

class RevisionTaskViewSet(viewsets.ModelViewSet):
    """
    Spaced repetition revision task management.
    """
    serializer_class = RevisionTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['subject', 'chapter', 'topic', 'status', 'is_completed']
    ordering_fields = ['due_date', 'interval_days', 'easiness_factor']
    ordering = ['due_date']

    def get_queryset(self):
        return RevisionTask.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def due(self, request):
        """Get only due and overdue tasks for today."""
        today = timezone.now().date()
        queryset = self.get_queryset().filter(
            due_date__lte=today,
            is_completed=False
        )
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def submit_score(self, request, pk=None):
        """
        Submits recall score (0-5) to SM-2 algorithm to compute next interval schedule.
        """
        task = self.get_object()
        quality_score = request.data.get('quality_score', None)
        time_spent_mins = int(request.data.get('time_spent_minutes', 0))

        if quality_score is None:
            return Response({'error': 'quality_score (0-5) is required'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Run SM-2
        result = SM2Algorithm.calculate(
            quality_score=quality_score,
            repetitions=task.repetitions,
            easiness_factor=task.easiness_factor,
            current_interval=task.interval_days
        )

        task.repetitions = result['repetitions']
        task.easiness_factor = result['easiness_factor']
        task.interval_days = result['interval_days']
        task.quality_score = int(quality_score)
        
        # 2. Update Scheduling
        today = timezone.now().date()
        task.due_date = today + timezone.timedelta(days=result['interval_days'])
        task.total_reviews += 1
        
        # Append review date
        dates = task.review_dates or []
        dates.append(timezone.now().isoformat())
        task.review_dates = dates

        # If quality_score >= 3, task is completed for today's session
        if int(quality_score) >= 3:
            task.is_completed = True
            task.status = 'completed'
            task.completed_at = timezone.now()
        else:
            task.is_completed = False
            task.status = 'due'  # remains due for review

        task.save()

        # 3. Save historical logs in Memory app
        RevisionHistory.objects.create(
            user=request.user,
            topic=task.topic,
            chapter=task.chapter,
            quality_score=int(quality_score),
            time_spent_minutes=time_spent_mins
        )

        # 4. Trigger Adaptive score calculation
        try:
            from apps.ai_engine.adaptive import AdaptiveLearningService
            AdaptiveLearningService.adapt_learning_profile(request.user)
        except Exception:
            pass

        serializer = self.get_serializer(task)
        return Response(serializer.data, status=status.HTTP_200_OK)
