"""
Accounts App - Models
Custom User model and Student Profile for a single-student system.
"""
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    """Custom user model with email as primary identifier."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    is_student = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email


class StudentProfile(models.Model):
    """
    Single student profile - the heart of the personal AI mentor system.
    Only ONE record should ever exist.
    """
    EXAM_ATTEMPTS = [
        ('may_2025', 'May 2025'),
        ('nov_2025', 'November 2025'),
        ('may_2026', 'May 2026'),
        ('nov_2026', 'November 2026'),
        ('may_2027', 'May 2027'),
        ('nov_2027', 'November 2027'),
    ]

    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('ml', 'Malayalam'),
        ('manglish', 'Manglish'),
    ]

    STUDY_TIME_CHOICES = [
        ('early_morning', 'Early Morning (4-7 AM)'),
        ('morning', 'Morning (7-10 AM)'),
        ('afternoon', 'Afternoon (12-3 PM)'),
        ('evening', 'Evening (4-7 PM)'),
        ('night', 'Night (8-11 PM)'),
        ('late_night', 'Late Night (11 PM - 2 AM)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='student_profile')
    preferred_name = models.CharField(max_length=100, blank=True)
    exam_attempt = models.CharField(max_length=20, choices=EXAM_ATTEMPTS, blank=True)
    exam_date = models.DateField(null=True, blank=True)
    daily_study_hours = models.FloatField(default=4.0)
    preferred_language = models.CharField(max_length=20, choices=LANGUAGE_CHOICES, default='en')
    preferred_study_time = models.CharField(max_length=20, choices=STUDY_TIME_CHOICES, default='evening')
    strong_subjects = models.JSONField(default=list, blank=True)
    weak_subjects = models.JSONField(default=list, blank=True)
    onboarding_completed = models.BooleanField(default=False)
    avatar_url = models.URLField(blank=True)

    # Computed fields
    days_until_exam = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Student Profile'
        verbose_name_plural = 'Student Profile'

    def __str__(self):
        return self.preferred_name or self.user.email

    def save(self, *args, **kwargs):
        if self.exam_date:
            self.days_until_exam = (self.exam_date - timezone.now().date()).days
        super().save(*args, **kwargs)


class StudentPreference(models.Model):
    """Student customizable settings."""
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('system', 'System'),
    ]

    VOICE_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('neutral', 'Neutral'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='system')
    voice_type = models.CharField(max_length=10, choices=VOICE_CHOICES, default='female')
    voice_enabled = models.BooleanField(default=True)
    notification_email = models.BooleanField(default=True)
    notification_inapp = models.BooleanField(default=True)
    notification_study_reminder = models.BooleanField(default=True)
    notification_revision_reminder = models.BooleanField(default=True)
    notification_goal_reminder = models.BooleanField(default=True)
    notification_mock_reminder = models.BooleanField(default=True)
    notification_missed_session = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Student Preferences'
        verbose_name_plural = 'Student Preferences'

    def __str__(self):
        return f"Preferences for {self.user.email}"


class ActivityLog(models.Model):
    """Login and activity tracking."""
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('study_start', 'Study Started'),
        ('study_end', 'Study Ended'),
        ('test_taken', 'Test Taken'),
        ('revision_done', 'Revision Done'),
        ('checkin', 'Daily Check-in'),
        ('profile_update', 'Profile Updated'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device = models.CharField(max_length=100, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'

    def __str__(self):
        return f"{self.user.email} - {self.action} at {self.timestamp}"
