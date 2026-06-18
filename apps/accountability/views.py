import logging
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
import json
from .models import DailyCheckIn, RecoveryPlan
from .serializers import DailyCheckInSerializer, RecoveryPlanSerializer
from apps.ai_engine.gemini_client import GeminiClient
from apps.analytics.calculator import AnalyticsCalculator
from apps.scheduler.models import Attendance

logger = logging.getLogger('apps.accountability')

class DailyCheckInViewSet(viewsets.ModelViewSet):
    """
    Manage student daily check-ins. On submit, triggers AI mentoring response.
    """
    serializer_class = DailyCheckInSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['date', 'did_study', 'mood']

    def get_queryset(self):
        return DailyCheckIn.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        checkin = serializer.save(user=user)

        # 1. Fetch details to feed to AI
        mood_str = checkin.get_mood_display()
        study_status = "studied" if checkin.did_study else "did not study"
        problems = checkin.problems_faced or "None mentioned"
        notes = checkin.notes or "None mentioned"

        # 2. Call Gemini for mentor review
        prompt = f"""
        Provide constructive, direct coaching feedback for this student's daily check-in:
        Date: {checkin.date}
        Study Status: Student {study_status} (Hours: {checkin.hours_completed})
        Mood: {mood_str}
        Productivity Rating: {checkin.productivity_rating}/10
        Problems faced: {problems}
        Notes: {notes}
        
        Give a short personal mentor comment (max 120 words) and up to 3 action steps.
        Provide response in JSON matching this schema:
        {{
            "feedback": "Mentor comment here...",
            "action_steps": ["Step 1", "Step 2", "Step 3"]
        }}
        """

        system_instruction = (
            "You are the senior personal CA Foundation AI mentor. "
            "You hold the student to high discipline standards, but maintain empathy. "
            "Suggest adjustments to their schedule, study habits, or review methods."
        )

        try:
            client = GeminiClient()
            # We want structured JSON response
            # Let's outline a simple schema description
            response_schema = {
                "type": "OBJECT",
                "properties": {
                    "feedback": {"type": "STRING"},
                    "action_steps": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"}
                    }
                },
                "required": ["feedback", "action_steps"]
            }

            json_text = client.generate_json(
                prompt=prompt,
                response_schema=response_schema,
                system_instruction=system_instruction
            )
            
            if json_text:
                result = json.loads(json_text)
                checkin.ai_feedback = result.get('feedback', '')
                checkin.ai_suggestions = result.get('action_steps', [])
                checkin.save()
        except Exception as e:
            logger.error(f"Error generating checkin AI feedback: {e}")
            checkin.ai_feedback = "Keep maintaining consistency! You are on a good track. Keep studying hard."
            checkin.ai_suggestions = ["Review notes", "Complete next revision set"]
            checkin.save()

        # 3. Update attendance
        attendance, _ = Attendance.objects.get_or_create(user=user, date=checkin.date)
        attendance.is_present = checkin.did_study
        if checkin.did_study:
            attendance.hours_studied = checkin.hours_completed
        attendance.save()

        # 4. Trigger prediction recalculation
        try:
            AnalyticsCalculator.recalculate_student_metrics(user)
        except Exception:
            pass


class RecoveryPlanViewSet(viewsets.ModelViewSet):
    serializer_class = RecoveryPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RecoveryPlan.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def active(self, request):
        plan = self.get_queryset().filter(is_active=True, is_completed=False).first()
        if plan:
            serializer = self.get_serializer(plan)
            return Response(serializer.data)
        return Response({'status': 'no active recovery plan'}, status=status.HTTP_200_OK)
