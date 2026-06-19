import logging
from apps.memory.services import MemoryService
from apps.knowledge.retriever import KnowledgeRetriever
from .models import PromptTemplate, AISettings, ConversationLog

logger = logging.getLogger('apps.ai_engine')

class PromptBuilder:
    @staticmethod
    def get_system_instruction(category='chat', user=None):
        """
        Retrieves the base system instruction for the AI, custom-tailored with student memory.
        """
        # 1. Fetch template from DB or use fallback
        db_template = PromptTemplate.objects.filter(category=category, is_active=True).first()
        if db_template:
            base_instruction = db_template.template_text
        else:
            base_instruction = PromptBuilder._get_fallback_instruction(category)

        # 2. Inject student memory context if user provided
        if user:
            memory_context = MemoryService.build_system_context(user)
            
            # Extract and inject explicit instructions based on preferred language choices
            profile = getattr(user, 'student_profile', None)
            lang_instruction = ""
            if profile:
                pref_lang = profile.preferred_language
                if pref_lang in ['ml', 'manglish']:
                    lang_instruction = (
                        "\nLANGUAGE REQUIREMENT:\n"
                        "The student's preferred language is Manglish (Malayalam written using the Latin/English alphabet script). "
                        "You MUST write your response entirely in fluid, natural Manglish (e.g., 'Innu nammal padikkan pokunnath accounting enna topic-ne kurichaanu. "
                        "Athil asset ennal namukkulla swathu ennanu artham. Athu debit side-il aanu kanikkuka.'). "
                        "DO NOT write in the Malayalam script/characters. Write ONLY in the Latin/English alphabet. "
                        "Naturally blend standard English technical terms (such as Ledger, Provision, Balance Sheet, Assets, Liabilities, etc.) "
                        "into the sentences. This ensures that standard English/Indian English TTS engines can speak the output text fluently and that it is easy for the student to read."
                    )
                else:
                    lang_instruction = (
                        "\nLANGUAGE REQUIREMENT:\n"
                        "The student's preferred language is English. Respond strictly in clear, professional, and encouraging English."
                    )

            full_instruction = (
                f"{base_instruction}\n\n"
                "STUDENT MENTOR CONTEXT (L1-L4 MEMORY ENGINE):\n"
                f"{memory_context}\n\n"
                f"{lang_instruction}\n\n"
                "IMPORTANT: Review the above student details. Adapt your tone, vocabulary, language preferences, "
                "and teaching speed accordingly. Never share the raw student context with the student."
            )
            return full_instruction
        
        return base_instruction

    @staticmethod
    def build_chat_prompt(user, query, subject_id=None, chapter_id=None, conversation_id=None):
        """
        Builds a conversational RAG prompt with active memory of recent chat history.
        """
        retriever = KnowledgeRetriever()
        rag_context, citations = retriever.build_rag_context(
            query, subject_id=subject_id, chapter_id=chapter_id, conversation_id=conversation_id
        )

        # Retrieve last 10 messages in the current session
        chat_history_str = ""
        if conversation_id:
            history_logs = list(ConversationLog.objects.filter(
                user=user,
                session_id=conversation_id
            ).order_by('-created_at')[:10])
            history_logs.reverse()
            
            chat_history = []
            for log in history_logs:
                chat_history.append(f"Student: {log.user_message}")
                chat_history.append(f"Mentor: {log.ai_response}")
            chat_history_str = "\n".join(chat_history)

        prompt_parts = []
        if chat_history_str:
            prompt_parts.append(f"CONVERSATION HISTORY:\n{chat_history_str}\n")
            
        prompt_parts.append(f"ICAI REFERENCE CONTEXT:\n{rag_context}\n")
        prompt_parts.append(f"STUDENT LATEST QUERY: {query}\n")
        prompt_parts.append(
            "ANSWER INSTRUCTIONS:\n"
            "- Answer the student's latest query, referencing the history if relevant.\n"
            "- Use the ICAI Study Material context provided above to ground your response.\n"
            "- If the query cannot be answered by the context, use your general knowledge of the CA Foundation syllabus, but state so.\n"
            "- Be highly encouraging and clear. Explain complex items step-by-step.\n"
            "- Cite your sources using [Source X] notation where relevant."
        )

        prompt = "\n".join(prompt_parts)
        return prompt, citations

    @staticmethod
    def _get_fallback_instruction(category):
        """Standard fallback prompts for the AI mentor."""
        if category == 'teaching':
            return (
                "You are the premier CA Foundation AI Teacher. Your job is to teach CA Foundation subjects "
                "(Accounting, Business Laws, Quantitative Aptitude, Business Economics) concept-by-concept. "
                "Break down complex legal clauses and accounting standards into extremely simple, memorable stories, "
                "analogies, and visual explanations. Check for student understanding after every concept."
            )
        elif category == 'revision':
            return (
                "You are the CA Foundation Spaced Repetition Revision coach. Your goal is to review previously "
                "studied topics. Ask quick, active recall questions, quiz the student on key legal terms or accounting formulas, "
                "and adjust scheduling based on their retention quality (SM-2 standard)."
            )
        elif category == 'assessment':
            return (
                "You are the CA Foundation MCQ Generator and Analyzer. Generate high-quality multiple choice questions "
                "conforming to ICAI standards. Never share the correct answers upfront. Assess the student's answers, "
                "diagnose their conceptual gaps, and classify errors as conceptual, careless, or calculation."
            )
        # default to 'chat'
        return (
            "You are Study Commander AI, a highly empathetic and structured personal AI mentor for a single CA Foundation student. "
            "Help the student maintain study discipline, answer curriculum queries, resolve worries, and coach them through preparation."
        )
