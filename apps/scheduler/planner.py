import logging
import json
from datetime import datetime, date, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field
from django.conf import settings
from apps.ai_engine.gemini_client import GeminiClient
from apps.curriculum.models import Topic, Subject
from apps.memory.models import ConceptMemory, SubjectMemory
from apps.revision.models import RevisionTask
from .models import StudyTask, DailySchedule

logger = logging.getLogger('apps.scheduler')

class TaskModel(BaseModel):
    title: str = Field(description="Action-oriented title of the study task")
    task_type: str = Field(description="Must be one of: 'study', 'revision', 'mcq_practice', 'mock_test', 'doubt_solving'")
    duration_minutes: int = Field(description="Estimated duration (30, 45, 60, 90, 120)")
    priority: int = Field(description="Priority level: 1 (Critical) to 4 (Low)")
    topic_name: str = Field(description="Exact curriculum topic name being studied or revised")
    ai_reason: str = Field(description="Short rationale for scheduling this task now")

class SchedulePlanModel(BaseModel):
    tasks: List[TaskModel] = Field(description="List of tasks scheduled for this study block")
    total_hours: float = Field(description="Sum of all task durations in hours")
    motivation_quote: str = Field(description="Empathetic, highly motivating mentor note for the day")

class AIStudyPlanner:
    @staticmethod
    def generate_daily_schedule(user, target_date):
        """
        Gathers user memory, weak spots, due revisions, and creates a tailored daily list of study tasks.
        """
        # 1. Fetch student daily commitment and preferred study time
        profile = user.student_profile
        daily_hours = profile.daily_study_hours or 4.0
        preferred_time = profile.get_preferred_study_time_display()
        language = profile.get_preferred_language_display()

        # 2. Gather due revisions (Spaced Repetition)
        due_revisions = RevisionTask.objects.filter(
            user=user,
            due_date__lte=target_date,
            is_completed=False
        )[:3]
        
        revisions_context = []
        for r in due_revisions:
            revisions_context.append(f"- REVISE: {r.topic.name} in {r.chapter.name} (Subject: {r.subject.name})")

        # 3. Gather weak subjects/topics
        weak_concepts = ConceptMemory.objects.filter(
            user=user,
            accuracy__lt=50.0,
            total_attempts__gt=0
        ).order_by('accuracy')[:3]

        weakness_context = []
        for wc in weak_concepts:
            weakness_context.append(f"- WEAKNESS FOCUS: {wc.topic.name} (Accuracy: {wc.accuracy:.1f}%)")

        # 4. Fetch curriculum reference to suggest new topics
        # Pick topics that have no attempts yet
        unstudied_topics = Topic.objects.filter(
            is_active=True
        ).exclude(
            student_memories__user=user
        )[:5]

        unstudied_context = []
        for ut in unstudied_topics:
            unstudied_context.append(f"- NEW TOPIC: {ut.name} (Chapter: {ut.chapter.name}, Subject: {ut.chapter.subject.name}, ID: {ut.id})")

        # 5. Build prompt
        prompt = f"""
        Generate a highly structured study plan for target date: {target_date}
        
        STUDENT PARAMETERS:
        - Study budget: {daily_hours} hours
        - Preferred study block: {preferred_time}
        - Preferred learning language: {language}
        
        ACTIVE MEMORY INPUTS:
        Due spaced repetition revisions:
        {chr(10).join(revisions_context) if revisions_context else "None"}
        
        Weak concepts needing practice:
        {chr(10).join(weakness_context) if weakness_context else "None"}
        
        Curriculum queue (unstudied topics):
        {chr(10).join(unstudied_context) if unstudied_context else "None"}
        
        INSTRUCTIONS:
        - Fill up to {daily_hours} hours with study blocks.
        - Prioritize due revisions (revision task type) first to maintain retention.
        - Add 1-2 new curriculum topics (study task type).
        - Add a mock_test or mcq_practice block (30-60 mins) for evaluation.
        - Provide exact topic names from the inputs list so we can match them.
        - Generate a highly motivating daily mentor quote ("motivation_quote"). If the student's preferred learning language is Malayalam, write this quote in standard Malayalam script. If their preferred language is Manglish, write it in Manglish (Malayalam written in English/Latin letters). Otherwise, write it in English.
        """

        system_instruction = (
            "You are the master scheduler engine for Study Commander AI. "
            "You create highly optimized, logical study sessions. "
            "You avoid over-scheduling and balance new concepts with active recall."
        )

        try:
            client = GeminiClient()
            json_text = client.generate_json(
                prompt=prompt,
                response_schema=SchedulePlanModel,
                system_instruction=system_instruction
            )

            if not json_text:
                raise ValueError("Received empty response from Gemini scheduler")

            plan = json.loads(json_text)
            
            # 6. Parse and save tasks in DB
            created_tasks = []
            for idx, t_model in enumerate(plan['tasks']):
                # Attempt to find the matching topic in DB
                topic = Topic.objects.filter(name__icontains=t_model['topic_name']).first()
                subject = topic.chapter.subject if topic else None
                chapter = topic.chapter if topic else None

                # Create task
                task = StudyTask.objects.create(
                    user=user,
                    title=t_model['title'],
                    task_type=t_model['task_type'],
                    subject=subject,
                    chapter=chapter,
                    topic=topic,
                    scheduled_date=target_date,
                    duration_minutes=t_model['duration_minutes'],
                    priority=t_model['priority'],
                    order=idx,
                    is_ai_generated=True,
                    ai_reason=t_model['ai_reason']
                )
                created_tasks.append(task)

            # Create or update DailySchedule
            daily_schedule, _ = DailySchedule.objects.get_or_create(user=user, date=target_date)
            daily_schedule.tasks.add(*created_tasks)
            daily_schedule.hours_planned = round(plan['total_hours'], 1)
            daily_schedule.ai_summary = plan['motivation_quote']
            daily_schedule.save()

            return daily_schedule

        except Exception as e:
            logger.exception("Error during AI daily schedule generation")
            return None
