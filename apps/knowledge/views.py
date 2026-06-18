from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import (
    KnowledgeDocument, PreviousYearQuestion, RTPDocument,
    MTPDocument, KnowledgeSummary
)
from .serializers import (
    KnowledgeDocumentSerializer, PreviousYearQuestionSerializer,
    RTPDocumentSerializer, MTPDocumentSerializer, KnowledgeSummarySerializer
)
from .tasks import process_document_task
from .retriever import KnowledgeRetriever

class KnowledgeDocumentViewSet(viewsets.ModelViewSet):
    """
    Manage uploaded study documents and materials.
    Automatically triggers vector chunking/embedding on creation.
    """
    serializer_class = KnowledgeDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['subject', 'chapter', 'doc_type', 'status']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'priority', 'title']
    ordering = ['priority', '-created_at']

    def get_queryset(self):
        return KnowledgeDocument.objects.all()

    def perform_create(self, serializer):
        doc = serializer.save(uploaded_by=self.request.user)
        # Trigger async Celery pipeline task
        process_document_task.delay(str(doc.id))


class PreviousYearQuestionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read PYQs and see analysis.
    """
    serializer_class = PreviousYearQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['subject', 'chapter', 'topic', 'year', 'difficulty', 'question_type']
    search_fields = ['question_text', 'answer_text']
    ordering_fields = ['year', 'probability_score', 'frequency_score']
    ordering = ['-year', 'subject', 'chapter']

    def get_queryset(self):
        return PreviousYearQuestion.objects.all()


class RTPDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = RTPDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['year', 'session']

    def get_queryset(self):
        return RTPDocument.objects.all()


class MTPDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MTPDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['year', 'session']

    def get_queryset(self):
        return MTPDocument.objects.all()


class KnowledgeSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read summaries generated for books/notes.
    """
    serializer_class = KnowledgeSummarySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['document', 'chapter', 'summary_type']
    search_fields = ['title', 'content']

    def get_queryset(self):
        return KnowledgeSummary.objects.all()


class RAGSearchViewSet(viewsets.ViewSet):
    """
    Endpoints for semantic searching across uploaded CA Foundation materials.
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def query(self, request):
        query_str = request.query_params.get('q', '')
        if not query_str:
            return Response({'error': 'Query parameter q is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        subject_id = request.query_params.get('subject', None)
        chapter_id = request.query_params.get('chapter', None)
        limit = int(request.query_params.get('limit', 5))
        
        retriever = KnowledgeRetriever()
        context, citations = retriever.build_rag_context(
            query_str,
            subject_id=subject_id,
            chapter_id=chapter_id,
            limit=limit,
            conversation_id="direct_search"
        )
        
        return Response({
            'query': query_str,
            'rag_context': context,
            'citations': citations
        }, status=status.HTTP_200_OK)
