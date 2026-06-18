import logging
from django.db.models import Avg
from apps.memory.services import MemoryService
from apps.memory.models import ConceptMemory
from apps.curriculum.models import Chapter
from .models import MockResult, MCQAttempt, MockQuestion

logger = logging.getLogger('apps.assessment')

class MockResultAnalyzer:
    @staticmethod
    def analyze_completed_test(mock_result_id):
        """
        Calculates final scores, negative marks, parses weak areas,
        updates student Memory models, and logs incorrect answers.
        """
        try:
            result = MockResult.objects.get(id=mock_result_id)
        except MockResult.DoesNotExist:
            logger.error(f"MockResult {mock_result_id} not found.")
            return None

        test = result.test
        attempts = MCQAttempt.objects.filter(result=result)
        
        correct = 0
        incorrect = 0
        unanswered = 0
        score = 0.0

        weak_chapters = {}
        strong_chapters = {}

        # 1. Evaluate questions
        for attempt in attempts:
            # Standalone generated check
            if attempt.question:
                correct_ans = attempt.question.correct_answer
                topic = attempt.question.topic
                chapter = attempt.question.chapter
            else:
                correct_ans = attempt.correct_answer
                topic = attempt.topic
                chapter = attempt.chapter

            # Check if correct
            if not attempt.selected_answer:
                unanswered += 1
                attempt.is_correct = False
            elif attempt.selected_answer.upper().strip() == correct_ans.upper().strip():
                correct += 1
                attempt.is_correct = True
                score += 1.0
                if chapter:
                    strong_chapters[chapter.id] = strong_chapters.get(chapter.id, 0) + 1
            else:
                incorrect += 1
                attempt.is_correct = False
                if test.negative_marking:
                    score -= test.negative_mark_value
                if chapter:
                    weak_chapters[chapter.id] = weak_chapters.get(chapter.id, 0) + 1

                # Log this incorrect answer in MistakeMemory
                if topic:
                    explanation = attempt.question.explanation if attempt.question else attempt.explanation
                    MemoryService.record_mistake(
                        user=result.user,
                        topic_id=topic.id,
                        mistake_type='conceptual', # Default categorization
                        question_text=attempt.question.question_text if attempt.question else attempt.question_text,
                        student_answer=attempt.selected_answer,
                        correct_answer=correct_ans,
                        explanation=explanation
                    )

            attempt.save()

            # 2. Inform memory engine of concept accuracy progress
            if topic:
                MemoryService.record_mcq_attempt(
                    user=result.user,
                    topic_id=topic.id,
                    is_correct=attempt.is_correct,
                    time_spent_sec=attempt.time_taken_seconds
                )

        # 3. Compile analytics
        total_q = test.total_questions or max(1, len(attempts))
        result.correct_count = correct
        result.incorrect_count = incorrect
        result.unanswered_count = unanswered
        result.score = max(0.0, round(score, 2))
        result.accuracy_percentage = round((correct / total_q) * 100, 1)

        # Map weak and strong chapters to titles
        weak_list = []
        strong_list = []
        
        for c_id, count in weak_chapters.items():
            ch = Chapter.objects.filter(id=c_id).first()
            if ch:
                weak_list.append(ch.name)

        for c_id, count in strong_chapters.items():
            ch = Chapter.objects.filter(id=c_id).first()
            if ch:
                # If a chapter is present in both (some correct, some incorrect),
                # check if correct count is higher than incorrect count
                is_weak = weak_chapters.get(c_id, 0) >= count
                if not is_weak:
                    strong_list.append(ch.name)

        result.weak_areas = weak_list[:4]
        result.strong_areas = strong_list[:4]

        # 4. Generate coaching feedback based on performance
        if result.accuracy_percentage >= 80.0:
            result.ai_feedback = "Excellent mastery shown! You have solid conceptual understanding here. Move on to next chapters."
            result.readiness_impact = 2.5 # Positive readiness boost
        elif result.accuracy_percentage >= 50.0:
            result.ai_feedback = "Good attempt. You have some conceptual gaps. Revise mistake logs and retry incorrect questions."
            result.readiness_impact = 0.5
        else:
            result.ai_feedback = "High risk of forgetting or core misconceptions. Schedule conceptual review blocks before practicing more."
            result.readiness_impact = -1.5

        result.save()

        # Recalculate User Success Readiness predictions
        # (This will be defined in analytics app)
        try:
            from apps.analytics.calculator import AnalyticsCalculator
            AnalyticsCalculator.recalculate_student_metrics(result.user)
        except Exception as e:
            logger.error(f"Error recalculating student metrics in assessment analyzer: {e}")

        return result
