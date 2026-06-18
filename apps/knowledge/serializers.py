from rest_framework import serializers
from .models import (
    KnowledgeDocument, DocumentChunk, KnowledgeCitation,
    PreviousYearQuestion, RTPDocument, MTPDocument, KnowledgeSummary
)

class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    doc_type_display = serializers.CharField(source='get_doc_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    chapter_name = serializers.CharField(source='chapter.name', read_only=True)

    class Meta:
        model = KnowledgeDocument
        fields = [
            'id', 'title', 'description', 'doc_type', 'doc_type_display',
            'file', 'file_type', 'file_size', 'page_count', 'subject', 'subject_name',
            'chapter', 'chapter_name', 'year', 'session', 'status', 'status_display',
            'error_message', 'chunk_count', 'processing_time', 'priority', 'created_at'
        ]
        read_only_fields = [
            'id', 'file_type', 'file_size', 'page_count', 'status',
            'error_message', 'chunk_count', 'processing_time', 'created_at'
        ]

class DocumentChunkSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentChunk
        fields = ['id', 'document', 'content', 'chunk_index', 'page_number', 'token_count']

class PreviousYearQuestionSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    chapter_name = serializers.CharField(source='chapter.name', read_only=True)
    topic_name = serializers.CharField(source='topic.name', read_only=True)

    class Meta:
        model = PreviousYearQuestion
        fields = [
            'id', 'subject', 'subject_name', 'chapter', 'chapter_name',
            'topic', 'topic_name', 'question_text', 'answer_text', 'marks',
            'year', 'session', 'question_type', 'difficulty', 'frequency_score',
            'probability_score', 'source_document', 'created_at'
        ]

class RTPDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RTPDocument
        fields = ['id', 'document', 'year', 'session', 'analysis_json', 'trending_topics', 'importance_scores']

class MTPDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = MTPDocument
        fields = ['id', 'document', 'year', 'session', 'analysis_json', 'trending_topics', 'importance_scores']

class KnowledgeSummarySerializer(serializers.ModelSerializer):
    summary_type_display = serializers.CharField(source='get_summary_type_display', read_only=True)
    chapter_name = serializers.CharField(source='chapter.name', read_only=True)

    class Meta:
        model = KnowledgeSummary
        fields = [
            'id', 'document', 'chapter', 'chapter_name', 'summary_type',
            'summary_type_display', 'title', 'content', 'created_at', 'updated_at'
        ]
