from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubjectViewSet, ChapterViewSet, TopicViewSet

router = DefaultRouter()
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'chapters', ChapterViewSet, basename='chapter')
router.register(r'topics', TopicViewSet, basename='topic')

urlpatterns = [
    path('', include(router.urls)),
]
