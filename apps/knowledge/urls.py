from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    KnowledgeDocumentViewSet, PreviousYearQuestionViewSet, RTPDocumentViewSet,
    MTPDocumentViewSet, KnowledgeSummaryViewSet, RAGSearchViewSet
)

router = DefaultRouter()
router.register(r'documents', KnowledgeDocumentViewSet, basename='document')
router.register(r'pyq', PreviousYearQuestionViewSet, basename='pyq')
router.register(r'rtp', RTPDocumentViewSet, basename='rtp')
router.register(r'mtp', MTPDocumentViewSet, basename='mtp')
router.register(r'summaries', KnowledgeSummaryViewSet, basename='knowledge-summary')
router.register(r'search', RAGSearchViewSet, basename='rag-search')

urlpatterns = [
    path('', include(router.urls)),
]
