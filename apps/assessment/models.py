"""
Assessment App - Models
MCQs, Mock Tests, and Results.
"""
import uuid
from django.db import models
from django.conf import settings


class MockTest(models.Model):
    """Mock tests — subject-level or full syllabus."""
    TEST_TYPES = [
        ('subject', 'Subject Test'),
        ('full', 'Full Syllabus Test'),
        ('chapter', 'Chapter Test'),
        ('quick', 'Quick Test'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    test_type = models.CharField(max_length=20, choices=TEST_TYPES)
    subject = models.ForeignKey('curriculum.Subject', on_delete=models.SET_NULL, null=True, blank=True, related_name='mock_tests')
    chapter = models.ForeignKey('curriculum.Chapter', on_delete=models.SET_NULL, null=True, blank=True, related_name='mock_tests')

    duration_minutes = models.IntegerField(default=60)
    total_marks = models.IntegerField(default=100)
    total_questions = models.IntegerField(default=30)
    passing_marks = models.IntegerField(default=40)
    negative_marking = models.BooleanField(default=True)
    negative_mark_value = models.FloatField(default=0.25)

    # AI-generated or admin-created
    is_ai_generated = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    difficulty_level = models.CharField(max_length=10, default='medium')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Mock Test'

    def __str__(self):
        return f"[{self.test_type}] {self.title}"


class MockQuestion(models.Model):
    """Questions within a mock test."""
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    test = models.ForeignKey(MockTest, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    question_image = models.ImageField(upload_to='assessment/questions/', blank=True)
    options = models.JSONField(help_text='{"A": "...", "B": "...", "C": "...", "D": "..."}')
    correct_answer = models.CharField(max_length=1, help_text='A, B, C, or D')
    explanation = models.TextField(blank=True)
    marks = models.IntegerField(default=1)
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')

    subject = models.ForeignKey('curriculum.Subject', on_delete=models.SET_NULL, null=True, blank=True)
    chapter = models.ForeignKey('curriculum.Chapter', on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.ForeignKey('curriculum.Topic', on_delete=models.SET_NULL, null=True, blank=True)

    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['test', 'order']
        verbose_name = 'Mock Question'

    def __str__(self):
        return f"Q{self.order}: {self.question_text[:60]}"


class MockResult(models.Model):
    """Results of a completed mock test."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mock_results')
    test = models.ForeignKey(MockTest, on_delete=models.CASCADE, related_name='results')

    score = models.FloatField(default=0.0)
    total_marks = models.IntegerField(default=0)
    correct_count = models.IntegerField(default=0)
    incorrect_count = models.IntegerField(default=0)
    unanswered_count = models.IntegerField(default=0)
    accuracy_percentage = models.FloatField(default=0.0)
    time_taken_minutes = models.IntegerField(default=0)

    # Analysis
    analysis_json = models.JSONField(default=dict, blank=True, help_text='Detailed score breakdown')
    weak_areas = models.JSONField(default=list, blank=True)
    strong_areas = models.JSONField(default=list, blank=True)
    improvement_plan = models.TextField(blank=True)
    ai_feedback = models.TextField(blank=True)

    # Readiness impact
    readiness_impact = models.FloatField(default=0.0, help_text='Impact on readiness score')

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at']
        verbose_name = 'Mock Result'

    def __str__(self):
        return f"{self.test.title}: {self.score}/{self.total_marks} ({self.accuracy_percentage}%)"


class MCQAttempt(models.Model):
    """Individual MCQ attempt records."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mcq_attempts')
    question = models.ForeignKey(MockQuestion, on_delete=models.CASCADE, related_name='attempts', null=True, blank=True)
    result = models.ForeignKey(MockResult, on_delete=models.CASCADE, related_name='attempts', null=True, blank=True)

    # For AI-generated standalone MCQs
    question_text = models.TextField(blank=True)
    options = models.JSONField(default=dict, blank=True)
    correct_answer = models.CharField(max_length=1, blank=True)

    selected_answer = models.CharField(max_length=1, blank=True)
    is_correct = models.BooleanField(default=False)
    time_taken_seconds = models.IntegerField(default=0)
    explanation = models.TextField(blank=True)

    subject = models.ForeignKey('curriculum.Subject', on_delete=models.SET_NULL, null=True, blank=True)
    chapter = models.ForeignKey('curriculum.Chapter', on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.ForeignKey('curriculum.Topic', on_delete=models.SET_NULL, null=True, blank=True)
    difficulty = models.CharField(max_length=10, default='medium')

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'MCQ Attempt'

    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{status} MCQ Attempt at {self.created_at}"
