import logging
from celery import shared_task
from django.contrib.auth import get_user_model
from .calculator import AnalyticsCalculator

logger = logging.getLogger('apps.analytics')
User = get_user_model()

@shared_task(name='apps.analytics.tasks.calculate_predictions')
def calculate_predictions():
    """
    Periodic task to recalculate readiness and pass probability metrics for all students.
    """
    logger.info("Starting periodic student success predictions task...")
    users = User.objects.filter(is_active=True)
    count = 0
    for user in users:
        try:
            AnalyticsCalculator.recalculate_student_metrics(user)
            count += 1
        except Exception as e:
            logger.error(f"Error calculating predictions for user {user.email}: {e}")
            
    logger.info(f"Finished recalculating success predictions for {count} users.")
    return count
