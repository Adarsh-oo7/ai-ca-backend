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


@shared_task(name='apps.notifications.tasks.send_missed_study_reminders')
def send_missed_study_reminders():
    """
    Check if the student has completed their daily study budget today or has pending tasks.
    If today's study hours are less than the daily budget, send a missed study reminder email.
    """
    logger.info("Starting daily missed study session scan...")
    today = timezone.now().date()
    
    # Get active student users
    users = User.objects.filter(is_active=True, is_student=True)
    sent_count = 0

    for user in users:
        # Get user's daily study hours budget
        daily_budget = 4.0  # default
        try:
            if hasattr(user, 'student_profile'):
                daily_budget = user.student_profile.daily_study_hours
        except Exception:
            pass

        # Check today's Attendance record
        from apps.scheduler.models import Attendance
        attendance = Attendance.objects.filter(user=user, date=today).first()
        
        hours_studied = 0.0
        if attendance:
            hours_studied = attendance.hours_studied

        # If they studied less than their daily budget
        if hours_studied < daily_budget:
            try:
                NotificationSender.send(
                    user=user,
                    title="⚠️ Study Session Missed!",
                    message=(
                        f"We noticed you only studied {hours_studied} hours today, which is below your daily target of {daily_budget} hours. "
                        "To clear your CA Foundation exams, you need to spend more time studying and maintain your daily consistency. "
                        "Let's get back on track tomorrow!"
                    ),
                    notification_type='missed_session',
                    priority='high',
                    action_url='/dashboard',
                    action_label='Go to Command Center'
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Error sending missed study session alert to {user.email}: {e}")

    logger.info(f"Finished missed study reminder scanner. Alerts sent to {sent_count} students.")
    return sent_count
