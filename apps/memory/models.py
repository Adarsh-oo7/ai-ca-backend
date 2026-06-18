"""
Memory App - Models
4-Layer personal memory engine for the AI mentor.
"""
import uuid
from django.db import models
from django.conf import settings


class LearningPreference(models.Model):
    """How the student learns best — adapts over time."""
    LEARNING_STYLES = [
        ('visual', 'Visual'),
        ('auditory', 'Auditory'),
        ('reading', 'Reading/Writing'),
        ('kinesthetic', 'Kinesthetic'),
        ('mixed', 'Mixed'),
    ]

    EXPLANATION_STYLES = [
        ('simple', 'Simple & Short'),
        ('detailed', 'Detailed & Thorough'),
        ('story', 'Story-Based'),
        ('example', 'Example-Heavy'),
        ('analogy', 'Analogy-Based'),
        ('exam_focused', 'Exam-Focused'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='learning_preference')
    learning_style = models.CharField(max_length=20, choices=LEARNING_STYLES, default='mixed')
    explanation_style = models.CharField(max_length=20, choices=EXPLANATION_STYLES, default='simple')
    attention_span_minutes = models.IntegerField(default=30)
    understanding_speed = models.FloatField(default=0.5, help_text='0=slow, 1=fast')
    favorite_examples = models.JSONField(default=list, blank=True, help_text='Types of examples that work well')
    preferred_difficulty = models.FloatField(default=0.5, help_text='0=easy, 1=hard')
    responds_well_to = models.JSONField(default=list, blank=True, help_text='Teaching methods that work')
    responds_poorly_to = models.JSONField(default=list, blank=True, help_text='Teaching methods that fail')
    notes = models.TextField(blank=True, help_text='AI observations about learning patterns')

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Learning Preference'

    def __str__(self):
        return f"Learning Preferences: {self.learning_style}"


class BehaviorProfile(models.Model):
    """Track study habits and behavioral patterns."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='behavior_profile')

    # Scores (0-100)
    consistency_score = models.FloatField(default=50.0)
    discipline_score = models.FloatField(default=50.0)
    motivation_score = models.FloatField(default=50.0)

    # Patterns
    procrastination_patterns = models.JSONField(default=list, blank=True)
    productive_hours = models.JSONField(default=list, blank=True, help_text='Hours when student is most productive')
    study_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    total_study_hours = models.FloatField(default=0.0)
    average_daily_hours = models.FloatField(default=0.0)
    missed_days = models.IntegerField(default=0)

    # AI observations
    behavior_notes = models.TextField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Behavior Profile'

    def __str__(self):
        return f"Behavior: Discipline={self.discipline_score}, Streak={self.study_streak}"


class SubjectMemory(models.Model):
    """AI's memory of student's performance per subject."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subject_memories')
    subject = models.ForeignKey('curriculum.Subject', on_delete=models.CASCADE, related_name='student_memories')

    strength_score = models.FloatField(default=50.0, help_text='0-100')
    weakness_score = models.FloatField(default=50.0, help_text='0-100')
    confidence_score = models.FloatField(default=50.0, help_text='0-100')
    total_time_spent = models.FloatField(default=0.0, help_text='Hours')
    last_studied = models.DateTimeField(null=True, blank=True)
    ai_notes = models.TextField(blank=True, help_text='AI observations about this subject')

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'subject')
        verbose_name = 'Subject Memory'
        verbose_name_plural = 'Subject Memories'

    def __str__(self):
        return f"{self.subject.name}: Strength={self.strength_score}"


class ChapterMemory(models.Model):
    """AI's memory of student's performance per chapter."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chapter_memories')
    chapter = models.ForeignKey('curriculum.Chapter', on_delete=models.CASCADE, related_name='student_memories')

    understanding_score = models.FloatField(default=0.0, help_text='0-100')
    revision_count = models.IntegerField(default=0)
    forgetting_risk = models.FloatField(default=0.0, help_text='0-100, higher = more likely to forget')
    completion_percentage = models.FloatField(default=0.0)
    last_studied = models.DateTimeField(null=True, blank=True)
    last_revised = models.DateTimeField(null=True, blank=True)
    total_time_spent = models.FloatField(default=0.0, help_text='Hours')
    ai_notes = models.TextField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'chapter')
        verbose_name = 'Chapter Memory'
        verbose_name_plural = 'Chapter Memories'

    def __str__(self):
        return f"{self.chapter.name}: Understanding={self.understanding_score}"


class ConceptMemory(models.Model):
    """AI's memory of student's performance per topic/concept."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='concept_memories')
    topic = models.ForeignKey('curriculum.Topic', on_delete=models.CASCADE, related_name='student_memories')

    accuracy = models.FloatField(default=0.0, help_text='0-100')
    total_attempts = models.IntegerField(default=0)
    correct_attempts = models.IntegerField(default=0)
    mistakes_count = models.IntegerField(default=0)
    retention_score = models.FloatField(default=0.0, help_text='0-100')
    last_reviewed = models.DateTimeField(null=True, blank=True)
    review_history = models.JSONField(default=list, blank=True)
    ai_notes = models.TextField(blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'topic')
        verbose_name = 'Concept Memory'
        verbose_name_plural = 'Concept Memories'

    def __str__(self):
        return f"{self.topic.name}: Accuracy={self.accuracy}"


class MistakeMemory(models.Model):
    """Track specific mistakes for pattern recognition."""
    MISTAKE_TYPES = [
        ('conceptual', 'Conceptual Mistake'),
        ('repeated', 'Repeated Error'),
        ('careless', 'Careless Mistake'),
        ('application', 'Application Error'),
        ('calculation', 'Calculation Error'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mistake_memories')
    topic = models.ForeignKey('curriculum.Topic', on_delete=models.CASCADE, related_name='mistakes', null=True, blank=True)
    chapter = models.ForeignKey('curriculum.Chapter', on_delete=models.CASCADE, related_name='mistakes', null=True, blank=True)
    subject = models.ForeignKey('curriculum.Subject', on_delete=models.CASCADE, related_name='mistakes', null=True, blank=True)

    mistake_type = models.CharField(max_length=20, choices=MISTAKE_TYPES)
    question_text = models.TextField()
    student_answer = models.TextField()
    correct_answer = models.TextField()
    explanation = models.TextField(blank=True)
    is_resolved = models.BooleanField(default=False)
    occurrences = models.IntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Mistake Memory'
        verbose_name_plural = 'Mistake Memories'

    def __str__(self):
        return f"{self.mistake_type}: {self.question_text[:50]}"


class MemorySummary(models.Model):
    """Compressed memory summaries for efficient AI context."""
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='memory_summaries')
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    period_start = models.DateField()
    period_end = models.DateField()
    summary_text = models.TextField()
    key_insights = models.JSONField(default=list, blank=True)
    topics_covered = models.JSONField(default=list, blank=True)
    performance_data = models.JSONField(default=dict, blank=True)
    token_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-period_start']
        verbose_name = 'Memory Summary'
        verbose_name_plural = 'Memory Summaries'

    def __str__(self):
        return f"{self.period} summary: {self.period_start} to {self.period_end}"


class RevisionHistory(models.Model):
    """Track all revision events for analytics."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='revision_histories')
    topic = models.ForeignKey('curriculum.Topic', on_delete=models.CASCADE, null=True, blank=True)
    chapter = models.ForeignKey('curriculum.Chapter', on_delete=models.CASCADE, null=True, blank=True)

    quality_score = models.IntegerField(default=3, help_text='0-5, SM-2 quality rating')
    time_spent_minutes = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Revision History'
        verbose_name_plural = 'Revision Histories'

    def __str__(self):
        return f"Revision: Q={self.quality_score} at {self.created_at}"
