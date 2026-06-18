"""
Analytics App - Models
Study analytics and dashboard data.
"""
from django.db import models
from django.conf import settings


class StudyAnalytics(models.Model):
    """Aggregated study analytics per day."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='study_analytics')
    date = models.DateField()

    hours_studied = models.FloatField(default=0.0)
    topics_covered = models.IntegerField(default=0)
    chapters_covered = models.IntegerField(default=0)
    mcqs_attempted = models.IntegerField(default=0)
    mcqs_correct = models.IntegerField(default=0)
    revisions_done = models.IntegerField(default=0)
    tasks_completed = models.IntegerField(default=0)
    tasks_total = models.IntegerField(default=0)
    discipline_score = models.FloatField(default=0.0)
    consistency_score = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']
        verbose_name = 'Study Analytics'
        verbose_name_plural = 'Study Analytics'

    def __str__(self):
        return f"Analytics: {self.date} - {self.hours_studied}h"
