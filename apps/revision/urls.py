from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RevisionTaskViewSet

router = DefaultRouter()
router.register(r'tasks', RevisionTaskViewSet, basename='revision-task')

urlpatterns = [
    path('', include(router.urls)),
]
