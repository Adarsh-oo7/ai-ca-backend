from datetime import datetime, timedelta
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django.utils import timezone
from .models import (
    LearningPreference, BehaviorProfile, SubjectMemory,
    ChapterMemory, ConceptMemory, MistakeMemory, MemorySummary
)
from .serializers import (
    LearningPreferenceSerializer, BehaviorProfileSerializer, SubjectMemorySerializer,
    ChapterMemorySerializer, ConceptMemorySerializer, MistakeMemorySerializer,
    MemorySummarySerializer
)
from .summarizer import MemorySummarizer

class LearningPreferenceViewSet(viewsets.ModelViewSet):
    """
    Manage the student's learning preferences.
    """
    serializer_class = LearningPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LearningPreference.objects.filter(user=self.request.user)

    def get_object(self):
        obj, _ = LearningPreference.objects.get_or_create(user=self.request.user)
        return obj


class BehaviorProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View the student's behavioral metrics and strengths.
    """
    serializer_class = BehaviorProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BehaviorProfile.objects.filter(user=self.request.user)

    def get_object(self):
        obj, _ = BehaviorProfile.objects.get_or_create(user=self.request.user)
        return obj


class SubjectMemoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Review performance metrics and strengths per subject.
    """
    serializer_class = SubjectMemorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SubjectMemory.objects.filter(user=self.request.user).order_by('-strength_score')


class ChapterMemoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Review chapter-level progress and forgetting risks.
    """
    serializer_class = ChapterMemorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['chapter__subject']

    def get_queryset(self):
        return ChapterMemory.objects.filter(user=self.request.user).order_by('chapter__subject', 'chapter__order')


class ConceptMemoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Detailed topic and concept-level mastery scores.
    """
    serializer_class = ConceptMemorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['topic__chapter', 'topic__chapter__subject']

    def get_queryset(self):
        return ConceptMemory.objects.filter(user=self.request.user).order_by('-accuracy')


class MistakeMemoryViewSet(viewsets.ModelViewSet):
    """
    List and manage student mistakes. Allow resolving them.
    """
    serializer_class = MistakeMemorySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['subject', 'chapter', 'is_resolved', 'mistake_type']
    search_fields = ['question_text', 'student_answer', 'correct_answer']

    def get_queryset(self):
        return MistakeMemory.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark a mistake as resolved."""
        mistake = self.get_object()
        mistake.is_resolved = True
        mistake.save()
        return Response({'status': 'mistake resolved'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def unresolve(self, request, pk=None):
        """Mark a mistake as active again."""
        mistake = self.get_object()
        mistake.is_resolved = False
        mistake.save()
        return Response({'status': 'mistake marked as unresolved'}, status=status.HTTP_200_OK)


class MemorySummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    View and generate periodic study summaries.
    """
    serializer_class = MemorySummarySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MemorySummary.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Trigger manual generation of a summary."""
        period = request.data.get('period', 'weekly')
        if period not in ['daily', 'weekly', 'monthly']:
            return Response({'error': 'Invalid period type'}, status=status.HTTP_400_BAD_REQUEST)

        # Determine start/end date
        end = timezone.now().date()
        if period == 'daily':
            start = end
        elif period == 'weekly':
            start = end - timedelta(days=7)
        else: # monthly
            start = end - timedelta(days=30)

        summary = MemorySummarizer.generate_summary(request.user, period, start, end)
        if summary:
            serializer = self.get_serializer(summary)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response({'error': 'Failed to generate summary'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
