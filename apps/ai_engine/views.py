import logging
import uuid
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import PromptTemplate, AISettings, ConversationLog, SuccessPrediction, ChatSession
from .serializers import (
    PromptTemplateSerializer, AISettingsSerializer,
    ConversationLogSerializer, SuccessPredictionSerializer,
    ChatSessionSerializer
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
    Supports persistent chat sessions that survive page refreshes.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_or_create_session(self, user, session_id, session_type='chat', subject=None, chapter=None, topic=None):
        """Get or create a ChatSession record for persistent tracking."""
        session, created = ChatSession.objects.get_or_create(
            id=session_id,
            defaults={
                'user': user,
                'title': 'New Chat',
                'session_type': session_type,
                'subject': subject,
                'chapter': chapter,
                'topic': topic,
            }
        )
        return session

    def _auto_title_session(self, session, user_message):
        """Generate an AI title for the session based on the first message."""
        if session.message_count > 0 and session.title != 'New Chat':
            return  # Already has a real title

        try:
            client = GeminiClient()
            title = client.generate_text(
                prompt=f"Generate a very short title (max 6 words) for a chat that starts with: \"{user_message[:200]}\". Return ONLY the title text, no quotes.",
                system_instruction="You generate ultra-short chat titles. Return ONLY the title, no formatting or quotes.",
                temperature=0.3,
                max_output_tokens=30
            )
            if title and len(title.strip()) > 0:
                session.title = title.strip()[:300]
                session.save(update_fields=['title'])
        except Exception as e:
            logger.warning(f"Auto-title generation failed: {e}")

    def _maybe_summarize_session(self, session):
        """If session has 10+ messages and no recent summary, compress old messages into a summary."""
        if session.message_count < 10:
            return
        if session.message_count % 10 != 0:
            return  # Only summarize every 10 messages

        try:
            # Get all messages in this session
            messages = ConversationLog.objects.filter(
                session_id=session.id
            ).order_by('created_at')

            chat_lines = []
            for msg in messages:
                chat_lines.append(f"Student: {msg.user_message}")
                chat_lines.append(f"Mentor: {msg.ai_response[:500]}")  # Truncate long responses

            conversation_text = "\n".join(chat_lines[-20:])  # Last 20 exchanges

            client = GeminiClient()
            summary = client.generate_text(
                prompt=(
                    f"Summarize this tutoring conversation into a concise paragraph (max 200 words). "
                    f"Focus on: topics discussed, key concepts explained, student's understanding level, "
                    f"any struggles or breakthroughs.\n\n{conversation_text}"
                ),
                system_instruction="You create concise conversation summaries for AI memory. Be factual and specific.",
                temperature=0.2,
                max_output_tokens=400
            )
            if summary:
                session.last_summary = summary.strip()
                session.save(update_fields=['last_summary'])
        except Exception as e:
            logger.warning(f"Session summary generation failed: {e}")

    @action(detail=False, methods=['post'])
    def send_message(self, request):
        query = request.data.get('message', '')
        if not query:
            return Response({'error': 'Message parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        subject_id = request.data.get('subject', None)
        chapter_id = request.data.get('chapter', None)
        session_id = request.data.get('session_id', str(uuid.uuid4()))

        # 1. Get or create persistent session
        subject = Subject.objects.filter(id=subject_id).first() if subject_id else None
        chapter = Chapter.objects.filter(id=chapter_id).first() if chapter_id else None

        session = self._get_or_create_session(
            user=request.user,
            session_id=session_id,
            session_type='chat',
            subject=subject,
            chapter=chapter
        )

        # 2. Fetch system instructions with user memory context
        system_instruction = PromptBuilder.get_system_instruction(category='chat', user=request.user)

        # 3. Build Chat prompt with RAG context + cross-session memory
        prompt, citations = PromptBuilder.build_chat_prompt(
            user=request.user,
            query=query,
            subject_id=subject_id,
            chapter_id=chapter_id,
            conversation_id=session_id
        )

        # 4. Call Gemini
        client = GeminiClient()
        ai_response = client.generate_text(
            prompt=prompt,
            system_instruction=system_instruction
        )

        # 5. Log transaction with session FK
        log_obj = ConversationLog.objects.create(
            user=request.user,
            session_id=session_id,
            chat_session=session,
            interaction_type='chat',
            user_message=query,
            ai_response=ai_response,
            subject=subject,
            chapter=chapter,
            citations=citations
        )

        # 6. Update session metadata
        session.message_count += 1
        session.save(update_fields=['message_count', 'updated_at'])

        # 7. Auto-title the session on first message
        self._auto_title_session(session, query)

        # 8. Periodically summarize the session for long-term memory
        self._maybe_summarize_session(session)

        # Record short study increment if discussing specific course subject
        if subject:
            MemoryService.record_study_session(
                user=request.user,
                subject_id=subject.id,
                chapter_id=chapter.id if chapter else None,
                duration_hours=0.05  # ~3 minutes chat credit
            )

        serializer = ConversationLogSerializer(log_obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get chat history for a specific session, or recent messages across all sessions."""
        session_id = request.query_params.get('session_id', None)
        if not session_id:
            logs = ConversationLog.objects.filter(
                user=request.user,
                interaction_type='chat'
            ).order_by('-created_at')[:50]
            logs = list(logs)
            logs.reverse()
        else:
            logs = ConversationLog.objects.filter(
                user=request.user,
                session_id=session_id,
            ).order_by('created_at')

        serializer = ConversationLogSerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def sessions(self, request):
        """List all chat sessions for the current user (for sidebar display)."""
        session_type = request.query_params.get('type', None)
        qs = ChatSession.objects.filter(user=request.user)
        if session_type:
            qs = qs.filter(session_type=session_type)
        sessions = qs.order_by('-updated_at')[:50]
        serializer = ChatSessionSerializer(sessions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path='sessions/(?P<session_pk>[^/.]+)')
    def delete_session(self, request, session_pk=None):
        """Delete a chat session and all its messages."""
        try:
            session = ChatSession.objects.get(id=session_pk, user=request.user)
            ConversationLog.objects.filter(session_id=session_pk, user=request.user).delete()
            session.delete()
            return Response({'status': 'deleted'}, status=status.HTTP_200_OK)
        except ChatSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)


class AITeachingViewSet(viewsets.ViewSet):
    """
    Interactive teaching flow (9-step concept-by-concept verification).
    Now also creates ChatSession records for persistent history.
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'])
    def teach_concept(self, request):
        topic_id = request.data.get('topic', None)
        session_id = request.data.get('session_id', None)
        message = request.data.get('message', '')  # student's reply

        if not topic_id:
            return Response({'error': 'Topic parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        if not session_id:
            return Response({'error': 'Session_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Get or create a persistent teaching session
        topic = Topic.objects.filter(id=topic_id).first()
        session, created = ChatSession.objects.get_or_create(
            id=session_id,
            defaults={
                'user': request.user,
                'title': f"Learn: {topic.name}" if topic else 'Teaching Session',
                'session_type': 'teaching',
                'topic': topic,
                'subject': topic.chapter.subject if topic else None,
                'chapter': topic.chapter if topic else None,
            }
        )

        teacher = AITeacher()

        # Check if conversation log already exists for this session to determine if we start or continue
        is_first_turn = not ConversationLog.objects.filter(session_id=session_id).exists()

        if is_first_turn:
            ai_response, citations = teacher.start_teaching_session(request.user, topic_id, session_id)
        else:
            if not message:
                return Response({'error': 'Message parameter is required to continue teaching session'}, status=status.HTTP_400_BAD_REQUEST)
            ai_response, citations = teacher.continue_teaching_session(request.user, topic_id, session_id, message)

        # Update session metadata
        session.message_count += 1
        session.save(update_fields=['message_count', 'updated_at'])

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
        user = self.request.user
        qs = SuccessPrediction.objects.filter(user=user)
        if not qs.exists():
            from apps.analytics.calculator import AnalyticsCalculator
            try:
                AnalyticsCalculator.recalculate_student_metrics(user)
                qs = SuccessPrediction.objects.filter(user=user)
            except Exception as e:
                logger.error(f"Error calculating default success prediction for {user.email}: {e}")
        return qs
