from rest_framework import serializers
from .models import Notification, NotificationTemplate

class NotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type', 'notification_type_display',
            'priority', 'priority_display', 'is_read', 'read_at', 'is_email_sent',
            'email_sent_at', 'action_url', 'action_label', 'created_at'
        ]
        read_only_fields = ['id', 'is_email_sent', 'email_sent_at', 'created_at']

class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = '__all__'
