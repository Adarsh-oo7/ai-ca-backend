import logging
import json
from datetime import datetime, date
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Avg, Sum, Count
from apps.ai_engine.gemini_client import GeminiClient
from apps.curriculum.models import Topic
from apps.scheduler.models import StudyTask
from apps.accountability.models import DailyCheckIn
from apps.assessment.models import MCQAttempt
from apps.revision.models import RevisionTask
from .models import MemorySummary, ConceptMemory

logger = logging.getLogger('apps.memory')
User = get_user_model()

class MemorySummarizer:
    @staticmethod
    def generate_summary(user, period='weekly', start_date=None, end_date=None):
        """
        Aggregate user study logs and performance metrics and generate an AI summary.
        """
        if not start_date or not end_date:
            logger.error("start_date and end_date are required for summary generation.")
            return None

        # 1. Fetch study tasks completed in this time range
        tasks = StudyTask.objects.filter(
            user=user,
            scheduled_date__range=(start_date, end_date),
            is_completed=True
        )
        total_study_mins = tasks.aggregate(Sum('duration_minutes'))['duration_minutes__sum'] or 0
        tasks_completed = tasks.count()

        # 2. Fetch daily checkins
        checkins = DailyCheckIn.objects.filter(
            user=user,
            date__range=(start_date, end_date)
        )
        avg_mood = checkins.aggregate(Avg('mood_score'))['mood_score__avg'] or 0.0
        avg_productivity = checkins.aggregate(Avg('productivity_score'))['productivity_score__avg'] or 0.0
        avg_discipline = checkins.aggregate(Avg('discipline_score'))['discipline_score__avg'] or 0.0

        # 3. Fetch MCQ attempts
        mcqs = MCQAttempt.objects.filter(
            user=user,
            created_at__date__range=(start_date, end_date)
        )
        total_mcqs = mcqs.count()
        correct_mcqs = mcqs.filter(is_correct=True).count()
        mcq_accuracy = (correct_mcqs / total_mcqs * 100) if total_mcqs > 0 else 0.0

        # 4. Fetch revisions done
        revisions = RevisionTask.objects.filter(
            topic__student_memories__user=user, # Check revisions for topic
            due_date__range=(start_date, end_date),
            is_completed=True
        ).count()

        # 5. Formulate aggregation dictionary
        activity_report = {
            "period": period,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_study_hours": round(total_study_mins / 60, 1),
            "tasks_completed_count": tasks_completed,
            "average_mood_rating_1_10": round(avg_mood, 1),
            "average_productivity_rating_1_10": round(avg_productivity, 1),
            "average_discipline_rating_1_10": round(avg_discipline, 1),
            "mcq_questions_attempted": total_mcqs,
            "mcq_accuracy_percentage": round(mcq_accuracy, 1),
            "spaced_repetition_revisions_completed": revisions
        }

        # 6. Call Gemini to create the summary & extract key insights
        prompt = f"""
        You are the personal CA Foundation AI Mentor for this student. 
        Analyze the student's study activity and performance stats for this {period} period:
        
        {json.dumps(activity_report, indent=2)}
        
        Provide a constructive, highly personalized coaching summary. 
        Focus on:
        1. Praise for consistency, streaks, or high MCQ accuracy.
        2. Diagnosis of weak areas or drops in discipline/productivity.
        3. Strategic advice on how to improve next week (specific CA Foundation topics/habits).
        
        Output MUST be in two sections:
        - Summary: A friendly but firm, professional mentor narrative (approx 150-250 words).
        - Insights: Bullet points of key insights (max 4).
        """

        system_instruction = (
            "You are a professional Chartered Accountant (CA) and premier CA Foundation exam mentor. "
            "Your feedback is highly specific, actionable, encouraging, and maintains high discipline standards."
        )

        try:
            client = GeminiClient()
            ai_response = client.generate_text(prompt, system_instruction=system_instruction)
            
            # Extract bullet points from AI response for insights
            insights = []
            summary_text = ai_response
            
            if "Insights:" in ai_response:
                parts = ai_response.split("Insights:")
                summary_text = parts[0].replace("Summary:", "").strip()
                insight_lines = parts[1].strip().split("\n")
                for line in insight_lines:
                    cleaned = line.strip().lstrip("-").lstrip("*").strip()
                    if cleaned:
                        insights.append(cleaned)
            
            # Clean up formatting
            if not insights:
                insights = ["Focus on weak subjects next week.", "Maintain the current streak.", "Review incorrect MCQ attempts."]

            # 7. Save to DB
            summary_obj = MemorySummary.objects.create(
                user=user,
                period=period,
                period_start=start_date,
                period_end=end_date,
                summary_text=summary_text,
                key_insights=insights,
                performance_data=activity_report
            )
            return summary_obj
        except Exception as e:
            logger.error(f"Error generating memory summary: {e}")
            return None
