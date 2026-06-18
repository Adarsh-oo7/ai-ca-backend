from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    StudyTaskViewSet, DailyScheduleViewSet, WeeklyScheduleViewSet,
    MonthlyScheduleViewSet, ScheduleTemplateViewSet, AttendanceViewSet
)

router = DefaultRouter()
router.register(r'tasks', StudyTaskViewSet, basename='task')
router.register(r'daily', DailyScheduleViewSet, basename='daily-schedule')
router.register(r'weekly', WeeklyScheduleViewSet, basename='weekly-schedule')
router.register(r'monthly', MonthlyScheduleViewSet, basename='monthly-schedule')
router.register(r'templates', ScheduleTemplateViewSet, basename='template')
router.register(r'attendance', AttendanceViewSet, basename='attendance')

urlpatterns = [
    path('', include(router.urls)),
]
