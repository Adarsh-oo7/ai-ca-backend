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

    @action(detail=False, methods=['post'])
    def speak(self, request):
        """
        Accepts text and optional voice_name in request body,
        generates TTS audio from Gemini, and returns it as an audio stream.
        """
        text = request.data.get('text', '')
        if not text:
            return Response({'error': 'text parameter is required'}, status=status.HTTP_400_BAD_REQUEST)

        voice_name = request.data.get('voice_name', 'Aoede')
        
        client = GeminiClient()
        audio_bytes, mime_type = client.generate_audio(text, voice_name=voice_name)
        
        if not audio_bytes:
            return Response({'error': 'Failed to generate audio output'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        from django.http import HttpResponse
        response = HttpResponse(audio_bytes, content_type=mime_type)
        response['Content-Disposition'] = 'attachment; filename="speech.wav"'
        return response

    @action(detail=False, methods=['get'])
    def get_api_key(self, request):
        """
        Returns an ephemeral Gemini token + a purpose-built VOICE system instruction.
        Accepts ?session_id=<uuid> to inject recent session memory.
        Uses a concise, voice-optimised prompt (NOT the full text-chat prompt)
        so the model actually follows it instead of reverting to generic behaviour.
        """
        client = GeminiClient()
        token = client.generate_ephemeral_token()
        if not token:
            return Response({'error': 'Failed to generate ephemeral session token'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        user = request.user

        # ── 1. Pull live student data ─────────────────────────────────────────
        profile = getattr(user, 'student_profile', None)
        student_name = profile.preferred_name if profile else (user.first_name or 'there')
        exam_display = profile.get_exam_attempt_display() if profile else 'CA Foundation'
        days_until   = profile.days_until_exam if profile else 'Unknown'
        daily_hours  = profile.daily_study_hours if profile else 'Unknown'
        lang_pref    = profile.get_preferred_language_display() if profile else 'English'

        # Subject mastery snapshot
        subject_lines = []
        try:
            from apps.memory.models import SubjectMemory
            for sm in SubjectMemory.objects.filter(user=user).select_related('subject'):
                subject_lines.append(
                    f"{sm.subject.name}: strength {sm.strength_score:.0f}%, confidence {sm.confidence_score:.0f}%"
                )
        except Exception:
            pass
        mastery_text = "; ".join(subject_lines) if subject_lines else "No data yet"

        # Study behaviour
        streak = 0
        total_hours = 0.0
        try:
            from apps.memory.models import BehaviorProfile
            beh, _ = BehaviorProfile.objects.get_or_create(user=user)
            streak      = beh.study_streak
            total_hours = beh.total_study_hours
        except Exception:
            pass

        # Language rule
        if profile and profile.preferred_language == 'ml':
            lang_rule = (
                "CRITICAL LANGUAGE RULE: You MUST speak exclusively in Malayalam (മലയാളം). "
                "Do NOT speak in English sentences. NEVER speak in Hindi, Tamil, or any other language under any circumstances. "
                "Only use English for specific CA Foundation technical terms (like Ledger, Assets, Balance Sheet, Debit, Credit) "
                "within Malayalam sentences. Speak natural, grammatically correct Malayalam."
            )
        elif profile and profile.preferred_language == 'manglish':
            lang_rule = (
                "CRITICAL LANGUAGE RULE: You MUST speak exclusively in Manglish (Malayalam words written in English/Latin script). "
                "Do NOT write or speak in plain English sentences, and NEVER speak in Hindi, Tamil, or any other language. "
                "Combine Malayalam conversational phrases and English CA terms naturally. "
                "Example: 'Nammal innu study cheyyan pokunnathu Accounting-ine kurichaanu. Athil Asset ennal nammude swathu aanu.'"
            )
        else:
            lang_rule = (
                "CRITICAL LANGUAGE RULE: You MUST speak exclusively in clear, friendly English. "
                "Do NOT use Hindi, Malayalam, or any other language under any circumstances."
            )

        # ── 2. Build lean voice system instruction ────────────────────────────
        system_instruction = f"""You are Devika, a personal CA Foundation AI teacher having a live voice call with your student {student_name}.

STUDENT STATUS RIGHT NOW:
- Name: {student_name}
- Target: {exam_display} | {days_until} days to exam
- Daily study goal: {daily_hours} hours | Current streak: {streak} days | Total hours logged: {total_hours:.0f}h
- Subject mastery: {mastery_text}
- Language preference: {lang_pref}

YOUR IDENTITY & MISSION:
You are NOT a generic AI. You are Devika — {student_name}'s personal CA teacher who knows their exact study status, weak areas, and progress. Your only job on this call is to help {student_name} crack CA Foundation.

HOW TO TEACH:
- Talk like a warm, encouraging friend who happens to be a CA expert.
- Explain simply. One idea at a time. Never dump everything at once.
- Use real-life examples: cricket, food, shopping, movies, family situations.
- If they sound confused, slow down and try a story or analogy.
- If they sound confident, speed up and ask harder questions.
- Never say "wrong" — say "Almost! Let me show you another way."
- After each explanation, check understanding: "Does that make sense?" or "Can you give me an example?"
- Reference their actual weak areas and exam countdown to keep them motivated.

SCOPE — CA FOUNDATION ONLY:
Only help with: Accounting, Business Laws, Quantitative Aptitude, Business Economics.
If they go off-topic: "That is interesting! But we have {days_until} days to your exam — let us focus. Which topic shall we tackle?"

VOICE RULES (CRITICAL):
- Short spoken sentences only. No markdown, no bullet points, no numbered lists.
- Natural conversational rhythm. Pause between ideas.
- {lang_rule}
- Always end your turn with a question or prompt to keep them engaged."""

        # ── 3. Inject session memory ──────────────────────────────────────────
        session_id = request.query_params.get('session_id', None)
        memory_parts = []

        # Long-term: past session summaries (up to 2, kept short)
        try:
            past_sessions = ChatSession.objects.filter(
                user=user,
                last_summary__isnull=False,
            ).exclude(last_summary='').order_by('-updated_at')
            if session_id:
                past_sessions = past_sessions.exclude(id=session_id)
            past_sessions = past_sessions[:2]
            if past_sessions.exists():
                parts = []
                for s in past_sessions:
                    parts.append(f"[{s.title}]: {s.last_summary[:300]}")
                memory_parts.append("PAST SESSIONS:\n" + "\n".join(parts))
        except Exception as e:
            logger.warning(f"Voice memory (past sessions): {e}")

        # Recent: last 5 exchanges from current session
        if session_id:
            try:
                recent_logs = list(ConversationLog.objects.filter(
                    user=user, session_id=session_id,
                ).order_by('-created_at')[:5])
                recent_logs.reverse()
                if recent_logs:
                    lines = []
                    for log in recent_logs:
                        lines.append(f"Student: {log.user_message}")
                        lines.append(f"Devika: {log.ai_response[:400]}")
                    memory_parts.append("THIS SESSION SO FAR:\n" + "\n".join(lines))
            except Exception as e:
                logger.warning(f"Voice memory (session history): {e}")

        if memory_parts:
            system_instruction += (
                "\n\nMEMORY — USE THIS TO CONTINUE NATURALLY:\n"
                + "\n\n".join(memory_parts)
                + f"\n\nPick up naturally from where you left off. Do NOT re-introduce yourself to {student_name}."
            )

        # ── 4. Build context-aware opening greeting ───────────────────────────
        # Determines what Devika says FIRST when the call connects.
        has_memory = bool(memory_parts)
        lang_code = 'ml' if (profile and profile.preferred_language == 'ml') else \
                    'manglish' if (profile and profile.preferred_language == 'manglish') else 'en'

        if has_memory and session_id:
            # Continuing from a session — pick up naturally
            if lang_code == 'ml':
                initial_message = f"ഹേ {student_name}! ഞാൻ Devika. നമ്മൾ ഇടയ്ക്ക് ഉണ്ടായിരുന്ന ചർച്ചയിൽ നിന്ന് തുടരാം. ഏത് topic ആണ് ഇന്ന് tackle ചെയ്യേണ്ടത്?"
            elif lang_code == 'manglish':
                initial_message = f"Hey {student_name}! Njaan Devika. Nammude session continue cheyyam. Innu enthu topic cover cheyyanam?"
            else:
                initial_message = f"Hey {student_name}! Good to connect again. Let us pick up where we left off. What topic do you want to work on today?"
        elif streak > 3:
            # Student is on a streak — acknowledge it
            if lang_code == 'ml':
                initial_message = f"ഹേ {student_name}! {streak} ദിവസം streak! അടിപൊളി! ഇന്ന് CA prep-ൽ എന്ത് tackle ചെയ്യണം?"
            elif lang_code == 'manglish':
                initial_message = f"Hey {student_name}! {streak} day streak — super! Innu CA-yil enthu padikkanam?"
            else:
                initial_message = f"Hey {student_name}! {streak} day study streak — that is impressive! What are we tackling in CA today?"
        else:
            # Fresh start
            if lang_code == 'ml':
                initial_message = f"ഹേ {student_name}! ഞാൻ Devika, നിന്റെ CA Foundation teacher. {days_until} ദിവസം ബാക്കി — ഇന്ന് ഏത് subject ആണ് ചെയ്യേണ്ടത്?"
            elif lang_code == 'manglish':
                initial_message = f"Hey {student_name}! Njaan Devika, nintte CA Foundation teacher. {days_until} days baaki — innu enthu subject cheyyanam?"
            else:
                initial_message = f"Hey {student_name}! I am Devika, your CA Foundation teacher. We have {days_until} days to your exam. What subject are we working on today?"

        return Response({
            'api_key': token,
            'system_instruction': system_instruction,
            'initial_message': initial_message,
            'lang_code': lang_code,
        }, status=status.HTTP_200_OK)


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
