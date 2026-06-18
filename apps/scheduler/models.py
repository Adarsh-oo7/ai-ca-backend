"""
Scheduler App - Models
Study plans, tasks, and attendance tracking.
"""
import uuid
from django.db import models
from django.conf import settings


class StudyTask(models.Model):
    """Individual study tasks that can be scheduled and moved."""
    TASK_TYPES = [
        ('study', 'Study New Topic'),
        ('revision', 'Revision'),
        ('mcq_practice', 'MCQ Practice'),
        ('mock_test', 'Mock Test'),
        ('notes', 'Read Notes'),
        ('doubt_solving', 'Doubt Solving'),
        ('formula_review', 'Formula Review'),
        ('pyq_practice', 'Previous Year Questions'),
        ('break', 'Break'),
    ]

    PRIORITY_CHOICES = [
        (1, 'Critical'),
        (2, 'High'),
        (3, 'Medium'),
        (4, 'Low'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('skipped', 'Skipped'),
        ('rescheduled', 'Rescheduled'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='study_tasks')
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    task_type = models.CharField(max_length=20, choices=TASK_TYPES)
    subject = models.ForeignKey('curriculum.Subject', on_delete=models.SET_NULL, null=True, blank=True)
    chapter = models.ForeignKey('curriculum.Chapter', on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.ForeignKey('curriculum.Topic', on_delete=models.SET_NULL, null=True, blank=True)

    # Scheduling
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=60)
    order = models.IntegerField(default=0, help_text='Display order within the day')

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=3)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    actual_duration = models.IntegerField(null=True, blank=True)

    # AI generated
    is_ai_generated = models.BooleanField(default=False)
    ai_reason = models.TextField(blank=True, help_text='Why AI scheduled this task')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_date', 'order', 'scheduled_time']
        verbose_name = 'Study Task'

    def __str__(self):
        return f"[{self.scheduled_date}] {self.title}"


class DailySchedule(models.Model):
    """Daily schedule overview."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_schedules')
    date = models.DateField()
    tasks = models.ManyToManyField(StudyTask, blank=True, related_name='daily_schedules')
    hours_planned = models.FloatField(default=0.0)
    hours_completed = models.FloatField(default=0.0)
    notes = models.TextField(blank=True)
    is_holiday = models.BooleanField(default=False)
    ai_summary = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']
        verbose_name = 'Daily Schedule'

    def __str__(self):
        return f"Schedule: {self.date}"


class WeeklySchedule(models.Model):
    """Weekly schedule with goals."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='weekly_schedules')
    start_date = models.DateField()
    end_date = models.DateField()
    goals = models.JSONField(default=list, blank=True)
    review_notes = models.TextField(blank=True)
    hours_planned = models.FloatField(default=0.0)
    hours_completed = models.FloatField(default=0.0)
    completion_percentage = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Weekly Schedule'

    def __str__(self):
        return f"Week: {self.start_date} to {self.end_date}"


class MonthlySchedule(models.Model):
    """Monthly schedule with goals."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='monthly_schedules')
    month = models.IntegerField()
    year = models.IntegerField()
    goals = models.JSONField(default=list, blank=True)
    review_notes = models.TextField(blank=True)
    hours_planned = models.FloatField(default=0.0)
    hours_completed = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'month', 'year')
        ordering = ['-year', '-month']
        verbose_name = 'Monthly Schedule'

    def __str__(self):
        return f"Month: {self.month}/{self.year}"


class ScheduleTemplate(models.Model):
    """Pre-built schedule templates."""
    TEMPLATE_TYPES = [
        ('2_hour', '2 Hour Plan'),
        ('4_hour', '4 Hour Plan'),
        ('6_hour', '6 Hour Plan'),
        ('weekend', 'Weekend Plan'),
        ('intensive', 'Intensive Plan'),
        ('revision_week', 'Revision Week'),
        ('exam_prep', 'Exam Preparation'),
    ]

    name = models.CharField(max_length=200)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    description = models.TextField(blank=True)
    total_hours = models.FloatField()
    tasks_template = models.JSONField(default=list, help_text='Template task definitions')
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Schedule Template'

    def __str__(self):
        return f"{self.name} ({self.total_hours}h)"


class Attendance(models.Model):
    """Daily attendance and study tracking."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendance_records')
    date = models.DateField()
    is_present = models.BooleanField(default=False)
    hours_studied = models.FloatField(default=0.0)
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    tasks_completed = models.IntegerField(default=0)
    tasks_total = models.IntegerField(default=0)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'date')
        ordering = ['-date']
        verbose_name = 'Attendance'
        verbose_name_plural = 'Attendance Records'

    def __str__(self):
        status = "Present" if self.is_present else "Absent"
        return f"{self.date}: {status} ({self.hours_studied}h)"
