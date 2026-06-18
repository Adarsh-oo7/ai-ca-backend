from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DailyCheckInViewSet, RecoveryPlanViewSet

router = DefaultRouter()
router.register(r'checkin', DailyCheckInViewSet, basename='checkin')
router.register(r'recovery', RecoveryPlanViewSet, basename='recovery')

urlpatterns = [
    path('', include(router.urls)),
]
