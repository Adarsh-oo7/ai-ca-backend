"""
Scheduler App - Celery Tasks
Automated study scheduling, missed task rescheduling, and weekly review.
"""
import logging
from datetime import date, timedelta
from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model

logger = logging.getLogger('apps.scheduler')
User = get_user_model()


@shared_task(name='apps.scheduler.tasks.auto_generate_tomorrow_schedule')
def auto_generate_tomorrow_schedule():
    """
    Runs nightly at 9 PM IST via Celery Beat.
    For each active student who has no tasks for tomorrow, 
    auto-generate a study schedule using the AI planner.
    """
    from .planner import AIStudyPlanner
    from .models import StudyTask

    tomorrow = date.today() + timedelta(days=1)
    
    # Find all students with profiles
    students = User.objects.filter(
        is_student=True,
        is_active=True,
        student_profile__onboarding_completed=True
    )

    generated_count = 0
    for student in students:
        # Skip if tasks already exist for tomorrow
        existing_tasks = StudyTask.objects.filter(
            user=student,
            scheduled_date=tomorrow
        ).count()

        if existing_tasks > 0:
            logger.info(f"Skipping {student.email}: {existing_tasks} tasks already exist for {tomorrow}")
            continue

        try:
            result = AIStudyPlanner.generate_daily_schedule(student, tomorrow)
            if result:
                generated_count += 1
                logger.info(f"Auto-generated schedule for {student.email} on {tomorrow}")
            else:
                logger.warning(f"AI planner returned None for {student.email}")
        except Exception as e:
            logger.error(f"Failed to auto-generate schedule for {student.email}: {e}")

    logger.info(f"Auto-scheduling complete: generated for {generated_count}/{students.count()} students")
    return f"Generated schedules for {generated_count} students"


@shared_task(name='apps.scheduler.tasks.reschedule_missed_tasks')
def reschedule_missed_tasks():
    """
    Runs daily at 6 AM IST via Celery Beat.
    Finds yesterday's incomplete tasks and reschedules them to today
    with boosted priority.
    """
    from .models import StudyTask

    yesterday = date.today() - timedelta(days=1)
    today = date.today()

    students = User.objects.filter(is_student=True, is_active=True)
    rescheduled_count = 0

    for student in students:
        missed_tasks = StudyTask.objects.filter(
            user=student,
            scheduled_date=yesterday,
            is_completed=False,
            status__in=['pending', 'in_progress']
        )

        for task in missed_tasks:
            # Create a rescheduled copy for today
            StudyTask.objects.create(
                user=student,
                title=f"[Rescheduled] {task.title}",
                description=f"Rescheduled from {yesterday}. {task.description}",
                task_type=task.task_type,
                subject=task.subject,
                chapter=task.chapter,
                topic=task.topic,
                scheduled_date=today,
                duration_minutes=task.duration_minutes,
                priority=max(1, task.priority - 1),  # Boost priority by 1 level
                is_ai_generated=True,
                ai_reason=f"Auto-rescheduled from {yesterday} (missed)"
            )

            # Mark original as rescheduled
            task.status = 'rescheduled'
            task.save(update_fields=['status'])
            rescheduled_count += 1

    logger.info(f"Rescheduled {rescheduled_count} missed tasks")
    return f"Rescheduled {rescheduled_count} tasks"


@shared_task(name='apps.scheduler.tasks.weekly_plan_review')
def weekly_plan_review():
    """
    Runs Sunday night via Celery Beat.
    Generates an AI analysis of the week's task completion rate
    and creates a notification with recommendations.
    """
    from .models import StudyTask
    from apps.notifications.models import Notification
    from apps.ai_engine.gemini_client import GeminiClient

    week_start = date.today() - timedelta(days=7)
    week_end = date.today()

    students = User.objects.filter(is_student=True, is_active=True)

    for student in students:
        total_tasks = StudyTask.objects.filter(
            user=student,
            scheduled_date__range=(week_start, week_end)
        ).count()

        completed_tasks = StudyTask.objects.filter(
            user=student,
            scheduled_date__range=(week_start, week_end),
            is_completed=True
        ).count()

        if total_tasks == 0:
            continue

        completion_rate = (completed_tasks / total_tasks) * 100

        try:
            client = GeminiClient()
            review = client.generate_text(
                prompt=(
                    f"The student completed {completed_tasks}/{total_tasks} tasks this week "
                    f"({completion_rate:.0f}% completion rate). "
                    f"Write a brief (2-3 sentence) motivational review with one specific suggestion "
                    f"for next week. Be encouraging but honest."
                ),
                system_instruction="You are a supportive CA Foundation study mentor. Be concise.",
                temperature=0.5,
                max_output_tokens=150
            )

            if review:
                Notification.objects.create(
                    user=student,
                    title=f"Weekly Review: {completion_rate:.0f}% tasks completed",
                    message=review,
                    notification_type='ai_insight',
                    priority='medium' if completion_rate >= 70 else 'high',
                    action_url='/dashboard/schedule',
                    action_label='View Schedule'
                )
                logger.info(f"Weekly review sent to {student.email}")
        except Exception as e:
            logger.error(f"Weekly review failed for {student.email}: {e}")

    return "Weekly reviews complete"


@shared_task(name='apps.scheduler.tasks.smart_reschedule_for_user')
def smart_reschedule_for_user(user_id, start_date_str, end_date_str):
    """
    On-demand task: Generate smart schedules for a date range for a specific user.
    Considers forgetting curves, stagnant subjects, and mood data.
    """
    from .planner import AIStudyPlanner
    from .models import StudyTask
    from datetime import datetime

    try:
        user = User.objects.get(id=user_id)
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except (User.DoesNotExist, ValueError) as e:
        logger.error(f"smart_reschedule_for_user error: {e}")
        return str(e)

    current_date = start_date
    generated = 0

    while current_date <= end_date:
        # Remove existing AI tasks for this day
        StudyTask.objects.filter(
            user=user,
            scheduled_date=current_date,
            is_completed=False,
            is_ai_generated=True
        ).delete()

        result = AIStudyPlanner.generate_daily_schedule(user, current_date)
        if result:
            generated += 1
        current_date += timedelta(days=1)

    return f"Generated {generated} days of schedules for {user.email}"
