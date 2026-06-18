from django.contrib import admin
from .models import MockTest, MockQuestion, MockResult, MCQAttempt

class MockQuestionInline(admin.TabularInline):
    model = MockQuestion
    extra = 3
    fields = ['question_text', 'correct_answer', 'marks', 'difficulty']

@admin.register(MockTest)
class MockTestAdmin(admin.ModelAdmin):
    list_display = ['title', 'test_type', 'subject', 'chapter', 'duration_minutes', 'total_questions', 'is_published']
    list_filter = ['test_type', 'is_published', 'difficulty_level', 'subject']
    search_fields = ['title', 'description']
    inlines = [MockQuestionInline]

@admin.register(MockQuestion)
class MockQuestionAdmin(admin.ModelAdmin):
    list_display = ['question_text_preview', 'test', 'correct_answer', 'marks', 'difficulty', 'subject', 'chapter']
    list_filter = ['difficulty', 'subject', 'test']
    search_fields = ['question_text', 'explanation']

    def question_text_preview(self, obj):
        return obj.question_text[:60]
    question_text_preview.short_description = 'Question Text'

@admin.register(MockResult)
class MockResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'test', 'score', 'accuracy_percentage', 'time_taken_minutes', 'completed_at']
    list_filter = ['completed_at', 'test__test_type']

@admin.register(MCQAttempt)
class MCQAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'question_preview', 'selected_answer', 'is_correct', 'created_at']
    list_filter = ['is_correct', 'difficulty', 'subject']

    def question_preview(self, obj):
        if obj.question:
            return obj.question.question_text[:50]
        return obj.question_text[:50]
    question_preview.short_description = 'Question'
