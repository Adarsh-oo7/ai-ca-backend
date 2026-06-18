"""
Revision App - Models
Spaced repetition tasks using SM-2 algorithm.
"""
import uuid
from django.db import models
from django.conf import settings


class RevisionTask(models.Model):
    """Spaced repetition revision tasks."""
    STATUS_CHOICES = [
        ('due', 'Due'),
        ('completed', 'Completed'),
        ('overdue', 'Overdue'),
        ('upcoming', 'Upcoming'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='revision_tasks')

    # What to revise
    subject = models.ForeignKey('curriculum.Subject', on_delete=models.CASCADE, related_name='revision_tasks')
    chapter = models.ForeignKey('curriculum.Chapter', on_delete=models.CASCADE, related_name='revision_tasks')
    topic = models.ForeignKey('curriculum.Topic', on_delete=models.SET_NULL, null=True, blank=True, related_name='revision_tasks')
    title = models.CharField(max_length=300)

    # SM-2 algorithm fields
    interval_days = models.IntegerField(default=1, help_text='Days until next review')
    easiness_factor = models.FloatField(default=2.5, help_text='SM-2 EF, min 1.3')
    repetitions = models.IntegerField(default=0, help_text='Consecutive correct recalls')
    quality_score = models.IntegerField(default=0, help_text='Last quality score 0-5')

    # Scheduling
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    # History
    total_reviews = models.IntegerField(default=0)
    review_dates = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_date']
        verbose_name = 'Revision Task'

    def __str__(self):
        return f"[{self.due_date}] {self.title} (EF={self.easiness_factor:.2f})"
