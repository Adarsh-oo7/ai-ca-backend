from django.contrib import admin
from .models import PromptTemplate, AISettings, ConversationLog, SuccessPrediction, ChatSession

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'session_type', 'message_count', 'is_active', 'created_at', 'updated_at']
    list_filter = ['session_type', 'is_active']
    search_fields = ['title', 'id', 'last_summary']


@admin.register(PromptTemplate)
class PromptTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active', 'version', 'updated_at']
    list_filter = ['category', 'is_active']
    search_fields = ['name', 'template_text', 'system_prompt']

@admin.register(AISettings)
class AISettingsAdmin(admin.ModelAdmin):
    list_display = ['model_name', 'temperature', 'max_tokens', 'embedding_model', 'updated_at']

@admin.register(ConversationLog)
class ConversationLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'session_id', 'interaction_type', 'subject', 'chapter', 'created_at']
    list_filter = ['interaction_type', 'subject']
    search_fields = ['user_message', 'ai_response', 'session_id']

@admin.register(SuccessPrediction)
class SuccessPredictionAdmin(admin.ModelAdmin):
    list_display = ['user', 'readiness_score', 'pass_probability', 'risk_score', 'computed_at']
    list_filter = ['user']
