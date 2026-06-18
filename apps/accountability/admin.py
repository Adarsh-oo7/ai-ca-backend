from django.contrib import admin
from .models import DailyCheckIn, RecoveryPlan

@admin.register(DailyCheckIn)
class DailyCheckInAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'did_study', 'hours_completed', 'mood', 'productivity_rating']
    list_filter = ['did_study', 'mood', 'date']
    search_fields = ['problems_faced', 'notes']

@admin.register(RecoveryPlan)
class RecoveryPlanAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'plan_type', 'start_date', 'end_date', 'is_active', 'is_completed']
    list_filter = ['plan_type', 'is_active', 'is_completed']
