from rest_framework import serializers
from .models import StudyAnalytics

class StudyAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyAnalytics
        fields = [
            'id', 'date', 'hours_studied', 'topics_covered', 'chapters_covered',
            'mcqs_attempted', 'mcqs_correct', 'revisions_done', 'tasks_completed',
            'tasks_total', 'discipline_score', 'consistency_score', 'created_at'
        ]
