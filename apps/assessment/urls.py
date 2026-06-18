from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MockTestViewSet, MockResultViewSet, MCQAttemptViewSet

router = DefaultRouter()
router.register(r'tests', MockTestViewSet, basename='mock-test')
router.register(r'results', MockResultViewSet, basename='mock-result')
router.register(r'attempts', MCQAttemptViewSet, basename='mcq-attempt')

urlpatterns = [
    path('', include(router.urls)),
]
