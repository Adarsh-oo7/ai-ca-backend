from rest_framework import serializers
from .models import PromptTemplate, AISettings, ConversationLog, SuccessPrediction, ChatSession

class PromptTemplateSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = PromptTemplate
        fields = [
            'id', 'name', 'category', 'category_display', 'description',
            'template_text', 'system_prompt', 'variables', 'is_active',
            'version', 'created_at', 'updated_at'
        ]

class AISettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AISettings
        fields = '__all__'

class ChatSessionSerializer(serializers.ModelSerializer):
    """Full chat session detail with messages."""
    session_type_display = serializers.CharField(source='get_session_type_display', read_only=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True, default=None)
    topic_name = serializers.CharField(source='topic.name', read_only=True, default=None)

    class Meta:
        model = ChatSession
        fields = [
            'id', 'title', 'session_type', 'session_type_display',
            'is_active', 'message_count', 'subject', 'subject_name',
            'topic', 'topic_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class ConversationLogSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    chapter_name = serializers.CharField(source='chapter.name', read_only=True)
    topic_name = serializers.CharField(source='topic.name', read_only=True)
    interaction_type_display = serializers.CharField(source='get_interaction_type_display', read_only=True)

    class Meta:
        model = ConversationLog
        fields = [
            'id', 'session_id', 'interaction_type', 'interaction_type_display',
            'user_message', 'ai_response', 'subject', 'subject_name',
            'chapter', 'chapter_name', 'topic', 'topic_name',
            'memory_tokens_used', 'rag_chunks_used', 'citations',
            'was_helpful', 'feedback', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'ai_response', 'citations']

class SuccessPredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuccessPrediction
        fields = '__all__'

