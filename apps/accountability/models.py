"""
Accountability App - Models
Daily check-ins, streaks, and discipline tracking.
"""
from django.db import models
from django.conf import settings


class DailyCheckIn(models.Model):
    """Daily accountability check-in form."""
    MOOD_CHOICES = [
        ('great', '😊 Great'),
        ('good', '🙂 Good'),
        ('okay', '😐 Okay'),
        ('bad', '😟 Bad'),
        ('terrible', '😞 Terrible'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_checkins')
    date = models.DateField()

    did_study = models.BooleanField(default=False)
    hours_completed = models.FloatField(default=0.0)
    chapters_completed = models.JSONField(default=list, blank=True)
    topics_completed = models.JSONField(default=list, blank=True)
    problems_faced = models.TextField(blank=True)
    mood = models.CharField(max_length=10, choices=MOOD_CHOICES, default='okay')
    productivity_rating = models.IntegerField(default=5, help_text='1-10')
    notes = models.TextField(blank=True)

    # AI-generated feedback
    ai_feedback = models.TextField(blank=True)
    ai_suggestions = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']
        verbose_name = 'Daily Check-in'

    def __str__(self):
        return f"Check-in: {self.date} - {'Studied' if self.did_study else 'Missed'}"


class RecoveryPlan(models.Model):
    """AI-generated recovery/catch-up plans."""
    PLAN_TYPES = [
        ('recovery', 'Recovery Plan'),
        ('catchup', 'Catch-up Plan'),
        ('extra_revision', 'Extra Revision Plan'),
        ('intensive', 'Intensive Plan'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recovery_plans')
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    title = models.CharField(max_length=300)
    description = models.TextField()
    tasks = models.JSONField(default=list)
    reason = models.TextField(blank=True, help_text='Why this plan was generated')
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Recovery Plan'

    def __str__(self):
        return f"[{self.plan_type}] {self.title}"
