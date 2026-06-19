import logging
from django.conf import settings
from apps.curriculum.models import Topic
from apps.memory.services import MemoryService
from apps.knowledge.retriever import KnowledgeRetriever
from .models import ConversationLog, AISettings
from .gemini_client import GeminiClient
from .prompts import PromptBuilder

logger = logging.getLogger('apps.ai_engine')

class AITeacher:
    def __init__(self):
        self.gemini_client = GeminiClient()

    def start_teaching_session(self, user, topic_id, session_id):
        """
        Starts a teaching session for a given CA Foundation topic.
        """
        try:
            topic = Topic.objects.get(id=topic_id)
        except Topic.DoesNotExist:
            logger.error(f"Topic {topic_id} not found in curriculum.")
            return "Error: Topic not found.", []

        # 1. Fetch relevant study materials
        retriever = KnowledgeRetriever()
        rag_context, citations = retriever.build_rag_context(
            f"Concept explanation for {topic.name} in chapter {topic.chapter.name}",
            subject_id=topic.chapter.subject.id,
            chapter_id=topic.chapter.id,
            conversation_id=session_id
        )

        # 2. Get student details and preferences
        student_context = MemoryService.build_system_context(user, current_topic_id=topic_id)
        
        # 3. Load AI Settings
        ai_settings = AISettings.load()

        # 4. Construct System Instruction
        base_teaching_prompt = PromptBuilder.get_system_instruction(category='teaching', user=user)
        system_instruction = (
            f"{base_teaching_prompt}\n\n"
            "CURRENT SUBJECT/CHAPTER DETAIL:\n"
            f"Subject: {topic.chapter.subject.name}\n"
            f"Chapter: {topic.chapter.name} (Weightage: {topic.chapter.weightage} marks)\n"
            f"Topic/Concept: {topic.name}\n\n"
            "ICAI SYLLABUS REFERENCE CONTENT:\n"
            f"{rag_context}\n\n"
            "TEACHING INSTRUCTIONS:\n"
            "- Start by introducing the concept briefly.\n"
            "- Use a relatable analogy (e.g., business scenario for laws, ledger sheets for accounts).\n"
            "- Explain the core definition/concept clearly.\n"
            "- End the response with a direct check-for-understanding question (like a small concept question or true/false) "
            "to verify the student is following before proceeding to more details."
        )

        # 5. Generate Response
        welcome_prompt = f"Hi, I am ready to start learning the topic: {topic.name}. Please introduce it and explain it to me."
        ai_response = self.gemini_client.generate_text(
            prompt=welcome_prompt,
            system_instruction=system_instruction
        )

        # 6. Save log
        ConversationLog.objects.create(
            user=user,
            session_id=session_id,
            interaction_type='teaching',
            user_message=welcome_prompt,
            ai_response=ai_response,
            subject=topic.chapter.subject,
            chapter=topic.chapter,
            topic=topic,
            citations=citations
        )

        # Update subject last studied date
        MemoryService.record_study_session(
            user=user,
            subject_id=topic.chapter.subject.id,
            chapter_id=topic.chapter.id,
            duration_hours=0.1, # initial start increment
            topic_id=topic.id
        )

        return ai_response, citations

    def continue_teaching_session(self, user, topic_id, session_id, user_message):
        """
        Continues an interactive teaching session with the student.
        Retrieves the conversation history.
        """
        try:
            topic = Topic.objects.get(id=topic_id)
        except Topic.DoesNotExist:
            return "Error: Topic not found.", []

        # 1. Retrieve recent history for this session
        history_logs = list(ConversationLog.objects.filter(
            user=user,
            session_id=session_id
        ).order_by('-created_at')[:10])  # Get last 10 messages for context
        history_logs.reverse()

        # 2. Fetch relevant study materials
        retriever = KnowledgeRetriever()
        rag_context, citations = retriever.build_rag_context(
            user_message,
            subject_id=topic.chapter.subject.id,
            chapter_id=topic.chapter.id,
            conversation_id=session_id
        )

        # 3. Format history as prompt contents
        chat_history = []
        for log in history_logs:
            chat_history.append(f"Student: {log.user_message}")
            chat_history.append(f"Mentor: {log.ai_response}")

        chat_history_str = "\n".join(chat_history)

        # 4. Construct System Instruction
        base_teaching_prompt = PromptBuilder.get_system_instruction(category='teaching', user=user)
        system_instruction = (
            f"{base_teaching_prompt}\n\n"
            "CURRENT STUDY TOPIC:\n"
            f"Subject: {topic.chapter.subject.name}\n"
            f"Chapter: {topic.chapter.name}\n"
            f"Topic: {topic.name}\n\n"
            "ICAI SYLLABUS REFERENCE CONTENT:\n"
            f"{rag_context}\n\n"
            "ROLE INSTRUCTIONS:\n"
            "- Guide the student step-by-step.\n"
            "- Evaluate if the student answered the understanding checks correctly.\n"
            "- If they are wrong, correct them patiently using a different example.\n"
            "- If they are right, praise them and move to the next sub-concept or practical scenario.\n"
            "- Keep explanations engaging, clear, and aligned with ICAI requirements."
        )

        prompt = (
            f"CONVERSATION HISTORY:\n{chat_history_str}\n\n"
            f"Student's latest reply: {user_message}\n\n"
            "Mentor's response:"
        )

        # 5. Generate Response
        ai_response = self.gemini_client.generate_text(
            prompt=prompt,
            system_instruction=system_instruction
        )

        # 6. Save log
        ConversationLog.objects.create(
            user=user,
            session_id=session_id,
            interaction_type='teaching',
            user_message=user_message,
            ai_response=ai_response,
            subject=topic.chapter.subject,
            chapter=topic.chapter,
            topic=topic,
            citations=citations
        )

        # Increment study time
        MemoryService.record_study_session(
            user=user,
            subject_id=topic.chapter.subject.id,
            chapter_id=topic.chapter.id,
            duration_hours=0.2, # 12 mins per turn increment
            topic_id=topic.id
        )

        return ai_response, citations
