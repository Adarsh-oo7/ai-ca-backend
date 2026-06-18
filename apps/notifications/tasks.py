import logging
from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from .sender import NotificationSender
from apps.scheduler.models import StudyTask

logger = logging.getLogger('apps.notifications')
User = get_user_model()

@shared_task(name='apps.notifications.tasks.send_study_reminders')
def send_study_reminders():
    """
    Periodic task to check active student tasks scheduled for today and send study reminders.
    """
    logger.info("Starting study reminders cron scan...")
    today = timezone.now().date()
    
    # Fetch active students
    users = User.objects.filter(is_active=True, is_student=True)
    sent_count = 0

    for user in users:
        # Check if they have pending tasks today
        pending_tasks = StudyTask.objects.filter(
            user=user,
            scheduled_date=today,
            is_completed=False
        )
        
        if pending_tasks.exists():
            task_list_str = ", ".join([t.title for t in pending_tasks[:2]])
            if pending_tasks.count() > 2:
                task_list_str += f" and {pending_tasks.count() - 2} more"

            try:
                NotificationSender.send(
                    user=user,
                    title="⏰ Time to Study!",
                    message=f"You have pending tasks scheduled for today: {task_list_str}. Stay disciplined!",
                    notification_type='study_reminder',
                    priority='medium',
                    action_url='/dashboard/schedule',
                    action_label='View Study Tasks'
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Error sending daily study reminder to {user.email}: {e}")

    logger.info(f"Finished cron study reminder scanner. Alerts sent to {sent_count} students.")
    return sent_count
