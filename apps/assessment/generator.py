import logging
import json
from typing import List
from pydantic import BaseModel, Field
from django.conf import settings
from apps.ai_engine.gemini_client import GeminiClient
from apps.curriculum.models import Topic
from apps.knowledge.retriever import KnowledgeRetriever
from .models import MockQuestion, MockTest

logger = logging.getLogger('apps.assessment')

class MCQItemModel(BaseModel):
    question_text: str = Field(description="The question prompt conforming to ICAI CA Foundation guidelines")
    option_a: str = Field(description="Option A")
    option_b: str = Field(description="Option B")
    option_c: str = Field(description="Option C")
    option_d: str = Field(description="Option D")
    correct_answer: str = Field(description="Single character correct option: 'A', 'B', 'C', or 'D'")
    explanation: str = Field(description="Detailed conceptual explanation showing why the answer is correct and why other options are wrong")

class MCQBatchModel(BaseModel):
    questions: List[MCQItemModel] = Field(description="List of multiple-choice questions")

class AIMCQGenerator:
    @staticmethod
    def generate_practice_questions(user, topic_id, difficulty='medium', count=5):
        """
        Generates MCQs using Gemini based on topic context and retrieved ICAI syllabus.
        Saves questions to a temporary Quick Practice MockTest object.
        """
        try:
            topic = Topic.objects.get(id=topic_id)
            chapter = topic.chapter
            subject = chapter.subject
        except Topic.DoesNotExist:
            logger.error(f"Topic {topic_id} not found for MCQ generation")
            return None

        # 1. Retrieve RAG context to ensure question accuracy matches ICAI materials
        retriever = KnowledgeRetriever()
        rag_context, _ = retriever.build_rag_context(
            f"Practice questions for {topic.name} ({difficulty} difficulty)",
            subject_id=subject.id,
            chapter_id=chapter.id,
            limit=3
        )

        # 2. Build AI Prompt
        prompt = f"""
        Generate {count} multiple choice questions (MCQs) for the following topic:
        Subject: {subject.name}
        Chapter: {chapter.name}
        Topic: {topic.name}
        Difficulty: {difficulty.upper()}
        
        ICAI SYLLABUS REFERENCE:
        {rag_context}
        
        GUIDELINES:
        - Questions must align with the ICAI CA Foundation exam standard.
        - Option keys must be A, B, C, D.
        - Select one single correct option (A, B, C, or D).
        - Provide a detailed, conceptual, step-by-step explanation.
        """

        system_instruction = (
            "You are the senior examiner for the ICAI Board of Studies. "
            "You write highly rigorous, non-trivial MCQs for the CA Foundation exam. "
            "You ensure all explanations cite relevant legal sections, accounting standards, or mathematical proofs."
        )

        try:
            client = GeminiClient()
            json_text = client.generate_json(
                prompt=prompt,
                response_schema=MCQBatchModel,
                system_instruction=system_instruction
            )

            if not json_text:
                raise ValueError("Empty response from MCQ generator AI")

            batch_data = json.loads(json_text)

            # Create a mock test container for this quick practice
            mock_test = MockTest.objects.create(
                title=f"Practice: {topic.name} ({difficulty.capitalize()})",
                description=f"Quick AI generated practice session for {topic.name}.",
                test_type='quick',
                subject=subject,
                chapter=chapter,
                duration_minutes=count * 2, # 2 mins per question
                total_marks=count,
                total_questions=count,
                is_ai_generated=True,
                difficulty_level=difficulty
            )

            # Save questions
            questions_created = []
            for idx, q_info in enumerate(batch_data['questions']):
                options_dict = {
                    "A": q_info['option_a'],
                    "B": q_info['option_b'],
                    "C": q_info['option_c'],
                    "D": q_info['option_d'],
                }
                
                question = MockQuestion.objects.create(
                    test=mock_test,
                    question_text=q_info['question_text'],
                    options=options_dict,
                    correct_answer=q_info['correct_answer'].upper().strip(),
                    explanation=q_info['explanation'],
                    marks=1,
                    difficulty=difficulty,
                    subject=subject,
                    chapter=chapter,
                    topic=topic,
                    order=idx
                )
                questions_created.append(question)

            return mock_test

        except Exception as e:
            logger.exception("Error during AI MCQ practice generation")
            return None
