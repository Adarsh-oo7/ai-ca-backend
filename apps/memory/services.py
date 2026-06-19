import logging
from django.utils import timezone
from django.db.models import Avg, Sum
from apps.accounts.models import StudentProfile
from apps.curriculum.models import Subject, Chapter, Topic
from .models import (
    LearningPreference, BehaviorProfile, SubjectMemory,
    ChapterMemory, ConceptMemory, MistakeMemory, MemorySummary
)

logger = logging.getLogger('apps.memory')

class MemoryService:
    @staticmethod
    def get_or_create_profiles(user):
        """Ensure all user preference and behavior profiles exist."""
        pref, _ = LearningPreference.objects.get_or_create(user=user)
        behavior, _ = BehaviorProfile.objects.get_or_create(user=user)
        return pref, behavior

    @staticmethod
    def record_study_session(user, subject_id, chapter_id, duration_hours, topic_id=None):
        """Update study time in memory for subject and chapter."""
        # Update behavior profile
        behavior, _ = BehaviorProfile.objects.get_or_create(user=user)
        behavior.total_study_hours += duration_hours
        # Calculate daily average
        profile = getattr(user, 'student_profile', None)
        if profile:
            days_since_start = (timezone.now() - profile.created_at).days or 1
            behavior.average_daily_hours = behavior.total_study_hours / max(1, days_since_start)
        behavior.save()

        # Update subject memory
        if subject_id:
            subject_mem, _ = SubjectMemory.objects.get_or_create(user=user, subject_id=subject_id)
            subject_mem.total_time_spent += duration_hours
            subject_mem.last_studied = timezone.now()
            subject_mem.save()

        # Update chapter memory
        if chapter_id:
            chapter_mem, _ = ChapterMemory.objects.get_or_create(user=user, chapter_id=chapter_id)
            chapter_mem.total_time_spent += duration_hours
            chapter_mem.last_studied = timezone.now()
            chapter_mem.save()

        # Update concept memory if topic is specified
        if topic_id:
            topic = Topic.objects.get(id=topic_id)
            concept_mem, created = ConceptMemory.objects.get_or_create(user=user, topic=topic)
            if created or concept_mem.total_attempts == 0:
                concept_mem.total_attempts = 1
                concept_mem.correct_attempts = 1
                concept_mem.accuracy = 80.0
                concept_mem.retention_score = 80.0
            concept_mem.last_reviewed = timezone.now()
            concept_mem.save()

            # Recalculate Chapter and Subject understanding averages
            c_obj = Chapter.objects.get(id=chapter_id) if chapter_id else topic.chapter
            s_obj = Subject.objects.get(id=subject_id) if subject_id else topic.chapter.subject
            MemoryService._recalculate_chapter_subject_scores(user, c_obj, s_obj)

    @staticmethod
    def record_mcq_attempt(user, topic_id, is_correct, time_spent_sec=0):
        """Update ConceptMemory based on MCQ attempt."""
        topic = Topic.objects.get(id=topic_id)
        chapter = topic.chapter
        subject = chapter.subject

        concept_mem, _ = ConceptMemory.objects.get_or_create(user=user, topic=topic)
        concept_mem.total_attempts += 1
        if is_correct:
            concept_mem.correct_attempts += 1
        else:
            concept_mem.mistakes_count += 1
        
        # Recalculate accuracy
        concept_mem.accuracy = (concept_mem.correct_attempts / concept_mem.total_attempts) * 100
        # Simple retention score: decay based on last review, boosted by accuracy
        concept_mem.retention_score = min(100.0, concept_mem.accuracy * 1.1)
        concept_mem.last_reviewed = timezone.now()
        
        # Save history item
        history_item = {
            'timestamp': timezone.now().isoformat(),
            'is_correct': is_correct,
            'time_spent': time_spent_sec
        }
        history = concept_mem.review_history or []
        history.append(history_item)
        concept_mem.review_history = history[-10:]  # Keep last 10 attempts
        concept_mem.save()

        # Update Chapter and Subject understanding averages
        MemoryService._recalculate_chapter_subject_scores(user, chapter, subject)

    @staticmethod
    def _recalculate_chapter_subject_scores(user, chapter, subject):
        """Helper to compute averages for chapter and subject memory."""
        # Chapter average
        topic_ids = chapter.topics.filter(is_active=True).values_list('id', flat=True)
        avg_concept_accuracy = ConceptMemory.objects.filter(
            user=user, topic_id__in=topic_ids
        ).aggregate(Avg('accuracy'))['accuracy__avg'] or 0.0

        chapter_mem, _ = ChapterMemory.objects.get_or_create(user=user, chapter=chapter)
        chapter_mem.understanding_score = avg_concept_accuracy
        
        # Calculate completion pct based on covered topics
        total_topics = len(topic_ids)
        covered_topics = ConceptMemory.objects.filter(
            user=user, topic_id__in=topic_ids, total_attempts__gt=0
        ).count()
        chapter_mem.completion_percentage = (covered_topics / max(1, total_topics)) * 100
        chapter_mem.save()

        # Subject average
        chapter_ids = subject.chapters.filter(is_active=True).values_list('id', flat=True)
        avg_chapter_understanding = ChapterMemory.objects.filter(
            user=user, chapter_id__in=chapter_ids
        ).aggregate(Avg('understanding_score'))['understanding_score__avg'] or 0.0

        subject_mem, _ = SubjectMemory.objects.get_or_create(user=user, subject=subject)
        subject_mem.strength_score = avg_chapter_understanding
        subject_mem.weakness_score = 100.0 - avg_chapter_understanding
        subject_mem.save()

    @staticmethod
    def record_mistake(user, topic_id, mistake_type, question_text, student_answer, correct_answer, explanation=""):
        """Record a detailed mistake for mistake memory."""
        topic = Topic.objects.get(id=topic_id)
        chapter = topic.chapter
        subject = chapter.subject

        mistake, created = MistakeMemory.objects.get_or_create(
            user=user,
            topic=topic,
            question_text=question_text,
            defaults={
                'chapter': chapter,
                'subject': subject,
                'mistake_type': mistake_type,
                'student_answer': student_answer,
                'correct_answer': correct_answer,
                'explanation': explanation,
            }
        )
        if not created:
            mistake.occurrences += 1
            mistake.student_answer = student_answer
            mistake.is_resolved = False
            mistake.save()
        
        return mistake

    @staticmethod
    def build_system_context(user, current_topic_id=None):
        """
        Gathers Layer 1 (Profile), Layer 2 (Active Learning / Recent behavior),
        Layer 3 (Mistakes / Weaknesses) and Layer 4 (Latest Summary) into a text
        format suitable for Gemini Prompt injection.
        """
        context = []
        
        # Layer 1: Core Student Profile
        profile = getattr(user, 'student_profile', None)
        if profile:
            context.append("=== STUDENT PROFILE ===")
            context.append(f"Preferred Name: {profile.preferred_name}")
            context.append(f"Target Exam: {profile.get_exam_attempt_display()}")
            context.append(f"Days Until Exam: {profile.days_until_exam} days")
            context.append(f"Preferred Language for explanations: {profile.get_preferred_language_display()}")
            context.append(f"Daily Study Commitment: {profile.daily_study_hours} hours")
            
            # Learning Preference
            pref, _ = LearningPreference.objects.get_or_create(user=user)
            context.append(f"Learning Style: {pref.get_learning_style_display()}")
            context.append(f"Explanation Style Preference: {pref.get_explanation_style_display()}")

        # Layer 2: Recent Behavior & Streaks
        behavior, _ = BehaviorProfile.objects.get_or_create(user=user)
        context.append("\n=== RECENT STUDY BEHAVIOR ===")
        context.append(f"Current Streak: {behavior.study_streak} days (Longest: {behavior.longest_streak})")
        context.append(f"Total Study Time: {behavior.total_study_hours:.1f} hours")
        context.append(f"Average Daily Hours: {behavior.average_daily_hours:.1f} hours")
        if behavior.behavior_notes:
            context.append(f"Behavior notes: {behavior.behavior_notes}")

        # Layer 3: Subject & Topic Strength/Weakness Memory
        context.append("\n=== CURRICULUM MASTERY ===")
        sub_mems = SubjectMemory.objects.filter(user=user)
        if sub_mems.exists():
            for sm in sub_mems:
                context.append(f"- {sm.subject.name}: Strength={sm.strength_score:.1f}%, Confidence={sm.confidence_score:.1f}%")
        else:
            context.append("No subject study records yet.")

        # Focus Topic / Concept Memory context if specified
        if current_topic_id:
            try:
                topic = Topic.objects.get(id=current_topic_id)
                concept_mem = ConceptMemory.objects.filter(user=user, topic=topic).first()
                context.append(f"\n=== CURRENT CONCEPT FOCUS ===")
                context.append(f"Topic: {topic.name} (Chapter: {topic.chapter.name})")
                if concept_mem:
                    context.append(f"Concept understanding: Accuracy={concept_mem.accuracy:.1f}%, Attempts={concept_mem.total_attempts}")
                    if concept_mem.ai_notes:
                        context.append(f"Mentor notes on topic: {concept_mem.ai_notes}")
                
                # Active mistakes for this topic
                recent_mistakes = MistakeMemory.objects.filter(user=user, topic=topic, is_resolved=False)[:3]
                if recent_mistakes.exists():
                    context.append("Recent active errors/misconceptions:")
                    for idx, m in enumerate(recent_mistakes):
                        context.append(f"  {idx+1}. Question: {m.question_text[:100]}... Student thought: {m.student_answer}. Correct: {m.correct_answer}")
            except Topic.DoesNotExist:
                pass

        # Layer 4: Memory Summaries (Keeping older memories in context)
        summaries = list(MemorySummary.objects.filter(user=user).order_by('-period_start')[:4])
        summaries.reverse()
        if summaries:
            context.append("\n=== HISTORICAL PROGRESS & MEMORY SUMMARIES ===")
            for s in summaries:
                context.append(f"[{s.period.capitalize()} Summary: {s.period_start} to {s.period_end}]")
                context.append(s.summary_text)
                if s.key_insights:
                    context.append(f"Key Insights: {', '.join(s.key_insights)}")

        return "\n".join(context)
