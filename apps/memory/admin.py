from django.contrib import admin
from .models import (
    LearningPreference, BehaviorProfile, SubjectMemory,
    ChapterMemory, ConceptMemory, MistakeMemory, MemorySummary, RevisionHistory
)

@admin.register(LearningPreference)
class LearningPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'learning_style', 'explanation_style', 'attention_span_minutes', 'understanding_speed']
    search_fields = ['user__email']

@admin.register(BehaviorProfile)
class BehaviorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'consistency_score', 'discipline_score', 'study_streak', 'total_study_hours']
    search_fields = ['user__email']

@admin.register(SubjectMemory)
class SubjectMemoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'subject', 'strength_score', 'confidence_score', 'total_time_spent', 'last_studied']
    list_filter = ['subject', 'user']

@admin.register(ChapterMemory)
class ChapterMemoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'chapter', 'understanding_score', 'forgetting_risk', 'completion_percentage', 'last_revised']
    list_filter = ['chapter__subject', 'user']

@admin.register(ConceptMemory)
class ConceptMemoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'topic', 'accuracy', 'total_attempts', 'mistakes_count', 'retention_score']
    list_filter = ['topic__chapter__subject', 'user']

@admin.register(MistakeMemory)
class MistakeMemoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'topic', 'mistake_type', 'is_resolved', 'occurrences', 'created_at']
    list_filter = ['mistake_type', 'is_resolved', 'user']
    search_fields = ['question_text', 'student_answer']

@admin.register(MemorySummary)
class MemorySummaryAdmin(admin.ModelAdmin):
    list_display = ['user', 'period', 'period_start', 'period_end', 'created_at']
    list_filter = ['period', 'user']

@admin.register(RevisionHistory)
class RevisionHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'topic', 'quality_score', 'time_spent_minutes', 'created_at']
    list_filter = ['quality_score', 'user']
