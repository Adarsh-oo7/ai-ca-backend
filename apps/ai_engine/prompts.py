import logging
from apps.memory.services import MemoryService
from apps.knowledge.retriever import KnowledgeRetriever
from .models import PromptTemplate, AISettings

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
            full_instruction = (
                f"{base_instruction}\n\n"
                "STUDENT MENTOR CONTEXT (L1-L4 MEMORY ENGINE):\n"
                f"{memory_context}\n\n"
                "IMPORTANT: Review the above student details. Adapt your tone, vocabulary, language preferences, "
                "and teaching speed accordingly. Never share the raw student context with the student."
            )
            return full_instruction
        
        return base_instruction

    @staticmethod
    def build_chat_prompt(user, query, subject_id=None, chapter_id=None, conversation_id=None):
        """
        Builds a conversational RAG prompt.
        """
        retriever = KnowledgeRetriever()
        rag_context, citations = retriever.build_rag_context(
            query, subject_id=subject_id, chapter_id=chapter_id, conversation_id=conversation_id
        )

        prompt = (
            f"{rag_context}\n\n"
            f"STUDENT QUERY: {query}\n\n"
            "ANSWER INSTRUCTIONS:\n"
            "- Answer the student's query using the ICAI Study Material context provided above.\n"
            "- If the query cannot be answered by the context, use your general knowledge of the CA Foundation syllabus, but state so.\n"
            "- Be highly encouraging and clear. Explain complex items step-by-step.\n"
            "- Cite your sources using [Source X] notation where relevant."
        )
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
