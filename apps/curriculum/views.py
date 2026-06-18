from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Subject, Chapter, Topic
from .serializers import (
    SubjectSerializer, SubjectDetailSerializer,
    ChapterSerializer, ChapterDetailSerializer,
    TopicSerializer
)

class SubjectViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows subjects to be viewed.
    """
    queryset = Subject.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [OrderingFilter]
    ordering_fields = ['order', 'name']
    ordering = ['order']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SubjectDetailSerializer
        return SubjectSerializer


class ChapterViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows chapters to be viewed.
    """
    queryset = Chapter.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['subject']
    ordering_fields = ['order', 'weightage']
    ordering = ['subject', 'order']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ChapterDetailSerializer
        return ChapterSerializer


class TopicViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows topics to be viewed.
    """
    queryset = Topic.objects.filter(is_active=True)
    serializer_class = TopicSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['chapter', 'chapter__subject']
    search_fields = ['name', 'description']
    ordering_fields = ['order', 'importance_score']
    ordering = ['chapter', 'order']
