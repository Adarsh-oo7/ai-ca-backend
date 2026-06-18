from django.contrib import admin
from .models import (
    KnowledgeDocument, DocumentChunk, KnowledgeCitation,
    PreviousYearQuestion, RTPDocument, MTPDocument, KnowledgeSummary
)
from .tasks import process_document_task

@admin.action(description="Re-run embedding process pipeline")
def reprocess_documents(modeladmin, request, queryset):
    for doc in queryset:
        process_document_task.delay(str(doc.id))

@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'doc_type', 'subject', 'chapter', 'status', 'chunk_count', 'created_at']
    list_filter = ['doc_type', 'status', 'subject']
    search_fields = ['title', 'description']
    actions = [reprocess_documents]

@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ['document', 'chunk_index', 'page_number', 'token_count', 'subject', 'chapter']
    list_filter = ['document', 'subject']
    search_fields = ['content']

@admin.register(KnowledgeCitation)
class KnowledgeCitationAdmin(admin.ModelAdmin):
    list_display = ['chunk', 'conversation_id', 'relevance_score', 'was_helpful', 'created_at']
    list_filter = ['was_helpful']

@admin.register(PreviousYearQuestion)
class PreviousYearQuestionAdmin(admin.ModelAdmin):
    list_display = ['subject', 'chapter', 'year', 'marks', 'difficulty', 'frequency_score', 'probability_score']
    list_filter = ['subject', 'difficulty', 'year']
    search_fields = ['question_text']

@admin.register(RTPDocument)
class RTPDocumentAdmin(admin.ModelAdmin):
    list_display = ['document', 'year', 'session']

@admin.register(MTPDocument)
class MTPDocumentAdmin(admin.ModelAdmin):
    list_display = ['document', 'year', 'session']

@admin.register(KnowledgeSummary)
class KnowledgeSummaryAdmin(admin.ModelAdmin):
    list_display = ['title', 'document', 'chapter', 'summary_type', 'created_at']
    list_filter = ['summary_type']
    search_fields = ['title', 'content']
