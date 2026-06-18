from django.contrib import admin
from .models import StudyAnalytics

@admin.register(StudyAnalytics)
class StudyAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'hours_studied', 'mcqs_attempted', 'mcqs_correct', 'tasks_completed', 'consistency_score']
    list_filter = ['date']
