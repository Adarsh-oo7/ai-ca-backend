import logging
from django.utils import timezone
from django.db.models import Avg, Sum
from apps.memory.models import LearningPreference, BehaviorProfile, ConceptMemory, MistakeMemory
from apps.scheduler.models import Attendance, StudyTask
from apps.assessment.models import MCQAttempt

logger = logging.getLogger('apps.ai_engine')

class AdaptiveLearningService:
    @staticmethod
    def adapt_learning_profile(user):
        """
        Periodically inspects assessment performance to fine-tune the user's
        understanding speed and preferred explanation styles.
        """
        try:
            pref, _ = LearningPreference.objects.get_or_create(user=pref_user=user)
        except TypeError:
            pref, _ = LearningPreference.objects.get_or_create(user=user)

        # 1. Look at MCQ attempts
        attempts = MCQAttempt.objects.filter(user=user)
        total_attempts = attempts.count()
        if total_attempts < 10:
            # Not enough data yet to make modifications
            return pref

        avg_accuracy = attempts.aggregate(Avg('is_correct'))['is_correct__avg'] or 0.5
        
        # Adjust understanding speed
        # High accuracy -> faster understanding speed
        # Low accuracy -> slower understanding speed (so AI explains in more detail)
        pref.understanding_speed = round(avg_accuracy, 2)

        # Adjust explanation styles based on mistake types
        mistakes = MistakeMemory.objects.filter(user=user, is_resolved=False)
        conceptual_count = mistakes.filter(mistake_type='conceptual').count()
        careless_count = mistakes.filter(mistake_type='careless').count()

        if conceptual_count > careless_count:
            # Need more details/examples to clear core concepts
            pref.explanation_style = 'detailed'
        elif careless_count > conceptual_count:
            # Needs to focus on exam application and practice
            pref.explanation_style = 'exam_focused'
        else:
            # Default to analogical explanations
            pref.explanation_style = 'analogy'

        pref.save()
        logger.info(f"Adapted learning profile for student {user.email}: speed={pref.understanding_speed}, style={pref.explanation_style}")
        return pref

    @staticmethod
    def adapt_behavior_profile(user):
        """
        Inspects study attendance, schedules, and streaks to compute
        real discipline and consistency scores.
        """
        profile, _ = BehaviorProfile.objects.get_or_create(user=user)
        
        # 1. Fetch study attendance for last 14 days
        today = timezone.now().date()
        two_weeks_ago = today - timezone.timedelta(days=14)
        
        attendances = Attendance.objects.filter(user=user, date__range=(two_weeks_ago, today))
        days_present = attendances.filter(is_present=True).count()
        
        # Consistency score based on percentage of days present out of 14
        profile.consistency_score = min(100.0, round((days_present / 14.0) * 100, 1))

        # 2. Discipline score: tasks completed vs planned
        tasks = StudyTask.objects.filter(user=user, scheduled_date__range=(two_weeks_ago, today))
        total_tasks = tasks.count()
        completed_tasks = tasks.filter(is_completed=True).count()

        if total_tasks > 0:
            profile.discipline_score = min(100.0, round((completed_tasks / total_tasks) * 100, 1))
        else:
            profile.discipline_score = 50.0 # baseline

        # 3. Update streaks
        # Attendance logic can increment streak, but here is a simple tracker
        # Check if they studied today or yesterday
        studied_today = Attendance.objects.filter(user=user, date=today, is_present=True).exists()
        studied_yesterday = Attendance.objects.filter(user=user, date=today - timezone.timedelta(days=1), is_present=True).exists()

        if studied_today:
            # Streak is active
            if profile.study_streak == 0:
                profile.study_streak = 1
            # Actual progression happens in Daily Check-in / Attendance tasks
        elif not studied_yesterday:
            # Streak broken
            profile.study_streak = 0

        if profile.study_streak > profile.longest_streak:
            profile.longest_streak = profile.study_streak

        profile.save()
        logger.info(f"Adapted behavior profile for student {user.email}: consistency={profile.consistency_score}, discipline={profile.discipline_score}")
        return profile
