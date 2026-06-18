from rest_framework import serializers
from .models import DailyCheckIn, RecoveryPlan

class DailyCheckInSerializer(serializers.ModelSerializer):
    mood_display = serializers.CharField(source='get_mood_display', read_only=True)

    class Meta:
        model = DailyCheckIn
        fields = [
            'id', 'date', 'did_study', 'hours_completed', 'chapters_completed',
            'topics_completed', 'problems_faced', 'mood', 'mood_display',
            'productivity_rating', 'notes', 'ai_feedback', 'ai_suggestions', 'created_at'
        ]
        read_only_fields = ['id', 'ai_feedback', 'ai_suggestions', 'created_at']

class RecoveryPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecoveryPlan
        fields = '__all__'
