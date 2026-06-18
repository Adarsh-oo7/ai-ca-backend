"""
Curriculum App - Models
CA Foundation subjects, chapters, and topics.
"""
from django.db import models


class Subject(models.Model):
    """CA Foundation subjects."""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    icon = models.CharField(max_length=50, blank=True, help_text='Icon name for frontend')
    color = models.CharField(max_length=7, default='#6366f1', help_text='Hex color code')
    total_weightage = models.IntegerField(default=100)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'

    def __str__(self):
        return self.name

    @property
    def chapter_count(self):
        return self.chapters.count()


class Chapter(models.Model):
    """Chapters within a subject."""
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='chapters')
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    weightage = models.IntegerField(default=0, help_text='Exam weightage (marks)')
    estimated_hours = models.FloatField(default=5.0, help_text='Estimated study hours')
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['subject', 'order']
        unique_together = ('subject', 'order')
        verbose_name = 'Chapter'
        verbose_name_plural = 'Chapters'

    def __str__(self):
        return f"{self.subject.code} - {self.name}"

    @property
    def topic_count(self):
        return self.topics.count()


class Topic(models.Model):
    """Topics within a chapter."""
    IMPORTANCE_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
        (4, 'Very High'),
        (5, 'Critical'),
    ]

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='topics')
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    importance_score = models.IntegerField(choices=IMPORTANCE_CHOICES, default=3)
    estimated_minutes = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)

    # Exam intelligence
    frequency_in_exams = models.IntegerField(default=0, help_text='How many times appeared in exams')
    last_appeared_year = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['chapter', 'order']
        verbose_name = 'Topic'
        verbose_name_plural = 'Topics'

    def __str__(self):
        return f"{self.chapter.subject.code} - {self.chapter.name} - {self.name}"
