from rest_framework import serializers
from .models import RevisionTask

class RevisionTaskSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    chapter_name = serializers.CharField(source='chapter.name', read_only=True)
    topic_name = serializers.CharField(source='topic.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = RevisionTask
        fields = [
            'id', 'subject', 'subject_name', 'chapter', 'chapter_name', 'topic', 'topic_name',
            'title', 'interval_days', 'easiness_factor', 'repetitions', 'quality_score',
            'due_date', 'status', 'status_display', 'is_completed', 'completed_at',
            'total_reviews', 'review_dates', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'interval_days', 'easiness_factor', 'repetitions',
            'status', 'is_completed', 'completed_at', 'total_reviews',
            'review_dates', 'created_at', 'updated_at'
        ]
