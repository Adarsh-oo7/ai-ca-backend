from rest_framework import serializers
from .models import Subject, Chapter, Topic

class TopicSerializer(serializers.ModelSerializer):
    importance_display = serializers.CharField(source='get_importance_score_display', read_only=True)

    class Meta:
        model = Topic
        fields = [
            'id', 'chapter', 'name', 'description', 'order',
            'importance_score', 'importance_display', 'estimated_minutes',
            'is_active', 'frequency_in_exams', 'last_appeared_year'
        ]

class ChapterSerializer(serializers.ModelSerializer):
    topic_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Chapter
        fields = [
            'id', 'subject', 'name', 'description', 'order',
            'weightage', 'estimated_hours', 'is_active', 'topic_count'
        ]

class ChapterDetailSerializer(serializers.ModelSerializer):
    topics = TopicSerializer(many=True, read_only=True)

    class Meta:
        model = Chapter
        fields = [
            'id', 'subject', 'name', 'description', 'order',
            'weightage', 'estimated_hours', 'is_active', 'topics'
        ]

class SubjectSerializer(serializers.ModelSerializer):
    chapter_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'code', 'description', 'order',
            'icon', 'color', 'total_weightage', 'is_active', 'chapter_count'
        ]

class SubjectDetailSerializer(serializers.ModelSerializer):
    chapters = ChapterSerializer(many=True, read_only=True)

    class Meta:
        model = Subject
        fields = [
            'id', 'name', 'code', 'description', 'order',
            'icon', 'color', 'total_weightage', 'is_active', 'chapters'
        ]
