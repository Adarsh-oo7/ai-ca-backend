"""
Accounts App - Admin Configuration
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, StudentProfile, StudentPreference, ActivityLog


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_student', 'is_staff', 'date_joined')
    list_filter = ('is_student', 'is_staff', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-date_joined',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Student Status', {'fields': ('is_student',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Student Status', {'fields': ('email', 'is_student',)}),
    )


class StudentPreferenceInline(admin.StackedInline):
    model = StudentPreference
    can_delete = False


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        'preferred_name', 'exam_attempt', 'exam_date',
        'daily_study_hours', 'preferred_language', 'onboarding_completed',
        'days_until_exam',
    )
    list_filter = ('exam_attempt', 'preferred_language', 'onboarding_completed')
    readonly_fields = ('days_until_exam', 'created_at', 'updated_at')
    fieldsets = (
        ('Personal', {
            'fields': ('user', 'preferred_name', 'avatar_url'),
        }),
        ('Exam', {
            'fields': ('exam_attempt', 'exam_date', 'days_until_exam'),
        }),
        ('Study Preferences', {
            'fields': (
                'daily_study_hours', 'preferred_language',
                'preferred_study_time',
            ),
        }),
        ('Subjects', {
            'fields': ('strong_subjects', 'weak_subjects'),
        }),
        ('Status', {
            'fields': ('onboarding_completed', 'created_at', 'updated_at'),
        }),
    )


@admin.register(StudentPreference)
class StudentPreferenceAdmin(admin.ModelAdmin):
    list_display = ('user', 'theme', 'voice_enabled', 'notification_email')


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'device', 'timestamp')
    list_filter = ('action', 'timestamp')
    readonly_fields = ('user', 'action', 'details', 'ip_address', 'user_agent', 'device', 'timestamp')
    search_fields = ('user__email', 'action')
    date_hierarchy = 'timestamp'
