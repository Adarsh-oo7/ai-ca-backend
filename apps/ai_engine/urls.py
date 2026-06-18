from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIChatViewSet, AITeachingViewSet, AISettingsViewSet, SuccessPredictionViewSet

router = DefaultRouter()
router.register(r'chat', AIChatViewSet, basename='ai-chat')
router.register(r'teach', AITeachingViewSet, basename='ai-teach')
router.register(r'settings', AISettingsViewSet, basename='ai-settings')
router.register(r'predictions', SuccessPredictionViewSet, basename='success-prediction')

urlpatterns = [
    path('', include(router.urls)),
]
