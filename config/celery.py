"""
Study Commander AI - Celery Configuration
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('studycommander')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    # Generate daily revision reminders at 6 AM IST
    'daily-revision-reminder': {
        'task': 'apps.revision.tasks.send_revision_reminders',
        'schedule': crontab(hour=6, minute=0),
    },
    # Update memory summaries weekly (Sunday midnight)
    'weekly-memory-summary': {
        'task': 'apps.memory.tasks.generate_weekly_summary',
        'schedule': crontab(hour=0, minute=0, day_of_week='sunday'),
    },
    # Calculate success predictions daily at midnight
    'daily-success-prediction': {
        'task': 'apps.analytics.tasks.calculate_predictions',
        'schedule': crontab(hour=0, minute=0),
    },
    # Send study reminders at preferred study time
    'study-reminder': {
        'task': 'apps.notifications.tasks.send_study_reminders',
        'schedule': crontab(minute='*/30'),  # Check every 30 min
    },
    # Clean old activity logs monthly
    'monthly-cleanup': {
        'task': 'apps.accounts.tasks.cleanup_old_logs',
        'schedule': crontab(hour=2, minute=0, day_of_month='1'),
    },
    # Auto-generate tomorrow's study schedule at 9 PM IST
    'auto-generate-tomorrow-schedule': {
        'task': 'apps.scheduler.tasks.auto_generate_tomorrow_schedule',
        'schedule': crontab(hour=21, minute=0),
    },
    # Reschedule missed tasks at 6 AM IST
    'reschedule-missed-tasks': {
        'task': 'apps.scheduler.tasks.reschedule_missed_tasks',
        'schedule': crontab(hour=6, minute=30),
    },
    # Weekly plan review Sunday 10 PM IST
    'weekly-plan-review': {
        'task': 'apps.scheduler.tasks.weekly_plan_review',
        'schedule': crontab(hour=22, minute=0, day_of_week='sunday'),
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
