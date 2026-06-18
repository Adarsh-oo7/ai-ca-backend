from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.utils import timezone
from .models import MockTest, MockQuestion, MockResult, MCQAttempt
from .serializers import (
    MockTestSerializer, MockTestDetailSerializer, MockQuestionSerializer,
    MockQuestionDetailSerializer, MockResultSerializer, MCQAttemptSerializer
)
from .generator import AIMCQGenerator
from .analyzer import MockResultAnalyzer

class MockTestViewSet(viewsets.ModelViewSet):
    """
    Syllabus mock tests and quick study practice sets.
    """
    serializer_class = MockTestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['subject', 'chapter', 'test_type', 'difficulty_level', 'is_published']
    search_fields = ['title', 'description']

    def get_queryset(self):
        # Normal student view only shows published tests or AI generated ones
        return MockTest.objects.filter(is_published=True)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MockTestDetailSerializer
        return MockTestSerializer

    @action(detail=False, methods=['post'])
    def generate_practice(self, request):
        """Generates dynamic AI MCQs for a topic on-demand."""
        topic_id = request.data.get('topic', None)
        difficulty = request.data.get('difficulty', 'medium')
        count = int(request.data.get('count', 5))

        if not topic_id:
            return Response({'error': 'Topic parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        mock_test = AIMCQGenerator.generate_practice_questions(
            user=request.user,
            topic_id=topic_id,
            difficulty=difficulty,
            count=count
        )

        if mock_test:
            serializer = MockTestDetailSerializer(mock_test)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response({'error': 'Failed to generate practice test'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def start_test(self, request, pk=None):
        """Start a mock test session and record the start timestamp."""
        test = self.get_object()
        
        # Check if already in progress or create new blank result
        result = MockResult.objects.create(
            user=request.user,
            test=test,
            started_at=timezone.now()
        )
        
        serializer = MockResultSerializer(result)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def submit_test(self, request, pk=None):
        """
        Accept student answers, score the test, trigger RAG analysis, and return grades.
        Request body formats answers: {"result_id": "...", "answers": {"Q_UUID_1": "A", "Q_UUID_2": "C"}}
        """
        test = self.get_object()
        result_id = request.data.get('result_id', None)
        answers = request.data.get('answers', {}) # Dict of {question_id: selected_answer}

        if not result_id:
            return Response({'error': 'result_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = MockResult.objects.get(id=result_id, user=request.user, test=test)
        except MockResult.DoesNotExist:
            return Response({'error': 'MockResult session not found'}, status=status.HTTP_404_NOT_FOUND)

        # Clear any prior attempts for this result session (safety retry logic)
        MCQAttempt.objects.filter(result=result).delete()

        # Save student answers
        questions = test.questions.all()
        for q in questions:
            selected = answers.get(str(q.id), "") # empty string if unanswered
            
            MCQAttempt.objects.create(
                user=request.user,
                question=q,
                result=result,
                selected_answer=selected.upper().strip(),
                subject=q.subject,
                chapter=q.chapter,
                topic=q.topic,
                difficulty=q.difficulty
            )

        # Run analyzer
        analyzed_result = MockResultAnalyzer.analyze_completed_test(result.id)
        
        # Update elapsed time
        if result.started_at:
            elapsed = (timezone.now() - result.started_at).total_seconds() / 60.0
            analyzed_result.time_taken_minutes = max(1, int(elapsed))
            analyzed_result.save()

        # Update user's adaptive behavior profile
        try:
            from apps.ai_engine.adaptive import AdaptiveLearningService
            AdaptiveLearningService.adapt_learning_profile(request.user)
        except Exception:
            pass

        serializer = MockResultSerializer(analyzed_result)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MockResultViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List historical assessment results.
    """
    serializer_class = MockResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['test', 'test__subject']
    ordering_fields = ['completed_at', 'score', 'accuracy_percentage']
    ordering = ['-completed_at']

    def get_queryset(self):
        return MockResult.objects.filter(user=self.request.user)

    @action(detail=True, methods=['get'])
    def review(self, request, pk=None):
        """
        Get result details alongside full question answers and explanations.
        """
        result = self.get_object()
        questions = result.test.questions.all()
        attempts = MCQAttempt.objects.filter(result=result)
        
        # Build review list
        review_data = []
        attempts_by_qid = {str(a.question.id): a for a in attempts if a.question}

        for q in questions:
            attempt = attempts_by_qid.get(str(q.id), None)
            review_data.append({
                'question_id': q.id,
                'question_text': q.question_text,
                'options': q.options,
                'correct_answer': q.correct_answer,
                'explanation': q.explanation,
                'selected_answer': attempt.selected_answer if attempt else "",
                'is_correct': attempt.is_correct if attempt else False,
                'time_taken': attempt.time_taken_seconds if attempt else 0
            })

        return Response({
            'result': MockResultSerializer(result).data,
            'review': review_data
        }, status=status.HTTP_200_OK)


class MCQAttemptViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MCQAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return MCQAttempt.objects.filter(user=self.request.user)
