from django.contrib import admin
from .models import Subject, Chapter, Topic

class TopicInline(admin.TabularInline):
    model = Topic
    extra = 1
    fields = ['name', 'order', 'importance_score', 'estimated_minutes', 'is_active']

class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 1
    fields = ['name', 'order', 'weightage', 'estimated_hours', 'is_active']

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'order', 'total_weightage', 'chapter_count', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'code']
    inlines = [ChapterInline]

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'order', 'weightage', 'estimated_hours', 'topic_count', 'is_active']
    list_filter = ['subject', 'is_active']
    list_editable = ['order', 'is_active']
    search_fields = ['name']
    inlines = [TopicInline]

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ['name', 'chapter', 'order', 'importance_score', 'estimated_minutes', 'is_active']
    list_filter = ['chapter__subject', 'chapter', 'importance_score', 'is_active']
    list_editable = ['order', 'importance_score', 'is_active']
    search_fields = ['name', 'description']
