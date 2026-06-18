from django.contrib import admin
from .models import StudyTask, DailySchedule, WeeklySchedule, MonthlySchedule, ScheduleTemplate, Attendance

@admin.register(StudyTask)
class StudyTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'task_type', 'subject', 'chapter', 'scheduled_date', 'status', 'is_completed']
    list_filter = ['task_type', 'status', 'scheduled_date', 'subject']
    search_fields = ['title', 'description']

@admin.register(DailySchedule)
class DailyScheduleAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'hours_planned', 'hours_completed', 'is_holiday']
    list_filter = ['is_holiday', 'date']

@admin.register(WeeklySchedule)
class WeeklyScheduleAdmin(admin.ModelAdmin):
    list_display = ['user', 'start_date', 'end_date', 'hours_planned', 'hours_completed', 'completion_percentage']

@admin.register(MonthlySchedule)
class MonthlyScheduleAdmin(admin.ModelAdmin):
    list_display = ['user', 'month', 'year', 'hours_planned', 'hours_completed']

@admin.register(ScheduleTemplate)
class ScheduleTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'total_hours', 'is_active']
    list_filter = ['template_type', 'is_active']

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'is_present', 'hours_studied', 'check_in_time', 'check_out_time']
    list_filter = ['is_present', 'date']
