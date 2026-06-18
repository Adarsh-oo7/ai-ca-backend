from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LearningPreferenceViewSet, BehaviorProfileViewSet, SubjectMemoryViewSet,
    ChapterMemoryViewSet, ConceptMemoryViewSet, MistakeMemoryViewSet, MemorySummaryViewSet
)

router = DefaultRouter()
router.register(r'preferences', LearningPreferenceViewSet, basename='preference')
router.register(r'behavior', BehaviorProfileViewSet, basename='behavior')
router.register(r'subjects', SubjectMemoryViewSet, basename='subject-memory')
router.register(r'chapters', ChapterMemoryViewSet, basename='chapter-memory')
router.register(r'concepts', ConceptMemoryViewSet, basename='concept-memory')
router.register(r'mistakes', MistakeMemoryViewSet, basename='mistake')
router.register(r'summaries', MemorySummaryViewSet, basename='summary')

urlpatterns = [
    path('', include(router.urls)),
]
