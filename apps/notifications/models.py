"""
Notifications App - Models
Email and in-app notifications.
"""
import uuid
from django.db import models
from django.conf import settings


class Notification(models.Model):
    """In-app and email notifications."""
    NOTIFICATION_TYPES = [
        ('study_reminder', 'Study Reminder'),
        ('revision_reminder', 'Revision Reminder'),
        ('goal_reminder', 'Goal Reminder'),
        ('mock_reminder', 'Mock Test Reminder'),
        ('missed_session', 'Missed Session Alert'),
        ('streak_update', 'Streak Update'),
        ('achievement', 'Achievement'),
        ('ai_insight', 'AI Insight'),
        ('schedule_update', 'Schedule Update'),
        ('system', 'System Notification'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=300)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')

    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)

    # Links
    action_url = models.CharField(max_length=500, blank=True)
    action_label = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'

    def __str__(self):
        return f"[{self.notification_type}] {self.title}"


class NotificationTemplate(models.Model):
    """Admin-editable notification templates."""
    name = models.CharField(max_length=200, unique=True)
    notification_type = models.CharField(max_length=20)
    title_template = models.CharField(max_length=300)
    message_template = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Notification Template'

    def __str__(self):
        return self.name
