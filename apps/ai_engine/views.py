import logging
import uuid
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import PromptTemplate, AISettings, ConversationLog, SuccessPrediction
from .serializers import (
    PromptTemplateSerializer, AISettingsSerializer,
    ConversationLogSerializer, SuccessPredictionSerializer
)
from .gemini_client import GeminiClient
from .prompts import PromptBuilder
from .teacher import AITeacher
from apps.memory.services import MemoryService
from apps.curriculum.models import Subject, Chapter, Topic

logger = logging.getLogger('apps.ai_engine')

class AIChatViewSet(viewsets.ViewSet):
    """
    Core AI Chat interface incorporating L1-L4 Memory and pgvector RAG.
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'])
    def send_message(self, request):
        query = request.data.get('message', '')
        if not query:
            return Response({'error': 'Message parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        subject_id = request.data.get('subject', None)
        chapter_id = request.data.get('chapter', None)
        session_id = request.data.get('session_id', str(uuid.uuid4()))

        # 1. Fetch system instructions with user memory context
        system_instruction = PromptBuilder.get_system_instruction(category='chat', user=request.user)

        # 2. Build Chat prompt with RAG context
        prompt, citations = PromptBuilder.build_chat_prompt(
            user=request.user,
            query=query,
            subject_id=subject_id,
            chapter_id=chapter_id,
            conversation_id=session_id
        )

        # 3. Call Gemini
        client = GeminiClient()
        ai_response = client.generate_text(
            prompt=prompt,
            system_instruction=system_instruction
        )

        # 4. Fetch subject/chapter objects for logging if provided
        subject = Subject.objects.filter(id=subject_id).first() if subject_id else None
        chapter = Chapter.objects.filter(id=chapter_id).first() if chapter_id else None

        # 5. Log transaction
        log_obj = ConversationLog.objects.create(
            user=request.user,
            session_id=session_id,
            interaction_type='chat',
            user_message=query,
            ai_response=ai_response,
            subject=subject,
            chapter=chapter,
            citations=citations
        )

        # Record short study increment if discussing specific course subject
        if subject:
            MemoryService.record_study_session(
                user=request.user,
                subject_id=subject.id,
                chapter_id=chapter.id if chapter else None,
                duration_hours=0.05 # ~3 minutes chat credit
            )

        serializer = ConversationLogSerializer(log_obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AITeachingViewSet(viewsets.ViewSet):
    """
    Interactive teaching flow (9-step concept-by-concept verification).
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'])
    def teach_concept(self, request):
        topic_id = request.data.get('topic', None)
        session_id = request.data.get('session_id', None)
        message = request.data.get('message', '') # student's reply

        if not topic_id:
            return Response({'error': 'Topic parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not session_id:
            return Response({'error': 'Session_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        teacher = AITeacher()

        # Check if conversation log already exists for this session to determine if we start or continue
        is_first_turn = not ConversationLog.objects.filter(session_id=session_id).exists()

        if is_first_turn:
            ai_response, citations = teacher.start_teaching_session(request.user, topic_id, session_id)
        else:
            if not message:
                return Response({'error': 'Message parameter is required to continue teaching session'}, status=status.HTTP_400_BAD_REQUEST)
            ai_response, citations = teacher.continue_teaching_session(request.user, topic_id, session_id, message)

        return Response({
            'session_id': session_id,
            'topic': topic_id,
            'ai_response': ai_response,
            'citations': citations
        }, status=status.HTTP_200_OK)


class AISettingsViewSet(viewsets.ModelViewSet):
    serializer_class = AISettingsSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AISettings.objects.all()

    def get_object(self):
        return AISettings.load()


class SuccessPredictionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SuccessPredictionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SuccessPrediction.objects.filter(user=self.request.user)
