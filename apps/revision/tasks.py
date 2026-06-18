import logging
from celery import shared_task
from django.utils import timezone
from .models import RevisionTask
from apps.notifications.sender import NotificationSender

logger = logging.getLogger('apps.revision')

@shared_task(name='apps.revision.tasks.send_revision_reminders')
def send_revision_reminders():
    """
    Scans for due or overdue spaced repetition tasks and triggers notification alerts.
    """
    logger.info("Starting periodic revision tasks scanner...")
    today = timezone.now().date()
    
    due_tasks = RevisionTask.objects.filter(
        due_date__lte=today,
        is_completed=False
    )

    # Group by user
    users_tasks = {}
    for task in due_tasks:
        users_tasks.setdefault(task.user, []).append(task)

    sent_count = 0
    for user, tasks in users_tasks.items():
        task_names = [t.title for t in tasks[:3]]
        task_summary = ", ".join(task_names)
        if len(tasks) > 3:
            task_summary += f" and {len(tasks) - 3} more"

        try:
            # Send Notification using notification module sender
            NotificationSender.send(
                user=user,
                title="📚 Revision Session Due!",
                message=f"You have {len(tasks)} spaced repetition revisions due today: {task_summary}.",
                notification_type='revision_reminder',
                priority='high',
                action_url='/revision',
                action_label='Start Revision Now'
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send revision notification for {user.email}: {e}")

    logger.info(f"Scan complete. Sent revision alerts to {sent_count} users.")
    return sent_count
