from django.contrib import admin
from .models import Notification, NotificationTemplate

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'notification_type', 'priority', 'is_read', 'is_email_sent', 'created_at']
    list_filter = ['notification_type', 'priority', 'is_read']
    search_fields = ['title', 'message']

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'notification_type', 'is_active']
    list_filter = ['notification_type', 'is_active']
