import logging
from django.utils import timezone
from django.db.models import Avg, Sum
from apps.memory.models import BehaviorProfile, SubjectMemory, RevisionHistory, ChapterMemory
from apps.assessment.models import MockResult, MCQAttempt
from apps.scheduler.models import StudyTask
from apps.ai_engine.models import SuccessPrediction

logger = logging.getLogger('apps.analytics')

class AnalyticsCalculator:
    @staticmethod
    def recalculate_student_metrics(user):
        """
        Gathers performance parameters across apps and saves a new SuccessPrediction entry.
        """
        # 1. Behavior factor
        behavior, _ = BehaviorProfile.objects.get_or_create(user=user)
        profile = user.student_profile
        
        target_hours = profile.daily_study_hours or 4.0
        avg_studied_hours = behavior.average_daily_hours or 0.0
        
        # study_hours_factor: scale 0.0 to 1.0 (capped at 1.0)
        study_hours_factor = min(1.0, avg_studied_hours / max(1.0, target_hours))
        consistency_factor = behavior.consistency_score / 100.0 # 0.0 to 1.0

        # 2. Revision factor
        # Look at revision tasks completion rate in the last 30 days
        thirty_days_ago = timezone.now().date() - timezone.timedelta(days=30)
        total_revs = StudyTask.objects.filter(
            user=user, 
            task_type='revision', 
            scheduled_date__gte=thirty_days_ago
        ).count()
        completed_revs = StudyTask.objects.filter(
            user=user, 
            task_type='revision', 
            scheduled_date__gte=thirty_days_ago, 
            is_completed=True
        ).count()
        
        revision_factor = (completed_revs / total_revs) if total_revs > 0 else 0.5

        # 3. Test score factor
        # Average mock test scores percentage
        avg_test_score = MockResult.objects.filter(user=user).aggregate(Avg('accuracy_percentage'))['accuracy_percentage__avg']
        if avg_test_score is not None:
            test_score_factor = avg_test_score / 100.0
        else:
            test_score_factor = 0.5 # default baseline

        # 4. Calculate Readiness (0-100)
        # Weights: study_hours (20%), consistency (30%), revisions (20%), test_scores (30%)
        readiness_score = (
            (study_hours_factor * 0.20) + 
            (consistency_factor * 0.30) + 
            (revision_factor * 0.20) + 
            (test_score_factor * 0.30)
        ) * 100.0
        readiness_score = round(min(100.0, max(0.0, readiness_score)), 1)

        # 5. Calculate Pass Probability
        # CA Foundation requires min 40% in each subject and 50% aggregate.
        # Check subject memories
        subject_mems = SubjectMemory.objects.filter(user=user)
        subject_risks = {}
        high_risk_subjects = []
        low_confidence_subjects = []
        
        for sm in subject_mems:
            subj_name = sm.subject.name
            strength = sm.strength_score
            subject_risks[sm.subject.code] = {
                'strength': strength,
                'confidence': sm.confidence_score,
                'risk': 'high' if strength < 40 else ('medium' if strength < 60 else 'low')
            }
            if strength < 45.0:
                high_risk_subjects.append(subj_name)
            if sm.confidence_score < 50.0:
                low_confidence_subjects.append(subj_name)

        # Base pass probability formula
        base_prob = readiness_score * 0.95
        if high_risk_subjects:
            # Penalty for having failing subjects
            base_prob -= (len(high_risk_subjects) * 15)
        
        pass_probability = round(min(99.0, max(5.0, base_prob)), 1)
        risk_score = round(100.0 - readiness_score, 1)

        # 6. Build Recommendations and Strengths/Weaknesses list
        strengths = []
        weaknesses = []
        recommendations = []

        if consistency_factor > 0.75:
            strengths.append("High study consistency. You study regularly.")
        else:
            weaknesses.append("Discipline drops periodically.")
            recommendations.append("Build consistency by studying at your preferred Early Morning block.")

        if test_score_factor > 0.70:
            strengths.append("Strong accuracy in completed practice tests.")
        else:
            weaknesses.append("Low scoring rate in MCQ assessments.")
            recommendations.append("Review detailed explanations in your Mistake logs before retaking MCQ practices.")

        if revision_factor < 0.60:
            weaknesses.append("Spaced repetition schedule is backing up.")
            recommendations.append("Complete due Spaced Repetition tasks daily to prevent forgetting previously learned topics.")

        for hrs_sub in high_risk_subjects:
            recommendations.append(f"Spend extra study blocks on weak subject: {hrs_sub}.")

        # Defaults
        if not strengths:
            strengths.append("Ready to learn and build discipline.")
        if not recommendations:
            recommendations.append("Keep doing daily check-ins and mock test revisions.")

        # 7. Save to SuccessPrediction
        prediction = SuccessPrediction.objects.create(
            user=user,
            readiness_score=readiness_score,
            pass_probability=pass_probability,
            risk_score=risk_score,
            subject_risks=subject_risks,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            study_hours_factor=round(study_hours_factor, 2),
            consistency_factor=round(consistency_factor, 2),
            revision_factor=round(revision_factor, 2),
            test_score_factor=round(test_score_factor, 2)
        )
        
        logger.info(f"Generated new success prediction for {user.email}: readiness={readiness_score}%, pass_prob={pass_probability}%")
        return prediction
