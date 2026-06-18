from rest_framework import serializers
from .models import (
    LearningPreference, BehaviorProfile, SubjectMemory,
    ChapterMemory, ConceptMemory, MistakeMemory, MemorySummary, RevisionHistory
)

class LearningPreferenceSerializer(serializers.ModelSerializer):
    learning_style_display = serializers.CharField(source='get_learning_style_display', read_only=True)
    explanation_style_display = serializers.CharField(source='get_explanation_style_display', read_only=True)

    class Meta:
        model = LearningPreference
        fields = [
            'id', 'learning_style', 'learning_style_display', 'explanation_style',
            'explanation_style_display', 'attention_span_minutes', 'understanding_speed',
            'favorite_examples', 'preferred_difficulty', 'responds_well_to',
            'responds_poorly_to', 'notes', 'updated_at'
        ]

class BehaviorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BehaviorProfile
        fields = [
            'id', 'consistency_score', 'discipline_score', 'motivation_score',
            'procrastination_patterns', 'productive_hours', 'study_streak',
            'longest_streak', 'total_study_hours', 'average_daily_hours',
            'missed_days', 'behavior_notes', 'updated_at'
        ]

class SubjectMemorySerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)
    color = serializers.CharField(source='subject.color', read_only=True)

    class Meta:
        model = SubjectMemory
        fields = [
            'id', 'subject', 'subject_name', 'subject_code', 'color',
            'strength_score', 'weakness_score', 'confidence_score',
            'total_time_spent', 'last_studied', 'ai_notes', 'updated_at'
        ]

class ChapterMemorySerializer(serializers.ModelSerializer):
    chapter_name = serializers.CharField(source='chapter.name', read_only=True)
    subject_name = serializers.CharField(source='chapter.subject.name', read_only=True)

    class Meta:
        model = ChapterMemory
        fields = [
            'id', 'chapter', 'chapter_name', 'subject_name', 'understanding_score',
            'revision_count', 'forgetting_risk', 'completion_percentage',
            'last_studied', 'last_revised', 'total_time_spent', 'ai_notes', 'updated_at'
        ]

class ConceptMemorySerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(source='topic.name', read_only=True)
    chapter_name = serializers.CharField(source='topic.chapter.name', read_only=True)

    class Meta:
        model = ConceptMemory
        fields = [
            'id', 'topic', 'topic_name', 'chapter_name', 'accuracy',
            'total_attempts', 'correct_attempts', 'mistakes_count',
            'retention_score', 'last_reviewed', 'review_history', 'ai_notes', 'updated_at'
        ]

class MistakeMemorySerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(source='topic.name', read_only=True)
    chapter_name = serializers.CharField(source='chapter.name', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    mistake_type_display = serializers.CharField(source='get_mistake_type_display', read_only=True)

    class Meta:
        model = MistakeMemory
        fields = [
            'id', 'topic', 'topic_name', 'chapter', 'chapter_name', 'subject', 'subject_name',
            'mistake_type', 'mistake_type_display', 'question_text', 'student_answer',
            'correct_answer', 'explanation', 'is_resolved', 'occurrences', 'created_at', 'updated_at'
        ]

class MemorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = MemorySummary
        fields = [
            'id', 'period', 'period_start', 'period_end', 'summary_text',
            'key_insights', 'topics_covered', 'performance_data', 'created_at'
        ]

class RevisionHistorySerializer(serializers.ModelSerializer):
    topic_name = serializers.CharField(source='topic.name', read_only=True)
    chapter_name = serializers.CharField(source='chapter.name', read_only=True)

    class Meta:
        model = RevisionHistory
        fields = [
            'id', 'topic', 'topic_name', 'chapter', 'chapter_name',
            'quality_score', 'time_spent_minutes', 'notes', 'created_at'
        ]
