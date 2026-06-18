"""
Knowledge App - Models
ICAI Knowledge Brain with document storage, chunks, and vector embeddings.
"""
import uuid
from django.db import models
from django.conf import settings

# Dynamic pgvector fallback for SQLite
try:
    is_sqlite = settings.DATABASES.get('default', {}).get('ENGINE', '').endswith('sqlite3')
except Exception:
    is_sqlite = False

if is_sqlite:
    class VectorField(models.TextField):
        def __init__(self, *args, **kwargs):
            kwargs.pop('dimensions', None)
            super().__init__(*args, **kwargs)
else:
    from pgvector.django import VectorField


class KnowledgeDocument(models.Model):
    """Uploaded study materials — ICAI, RTP, MTP, Notes, etc."""
    DOC_TYPES = [
        ('icai_material', 'ICAI Study Material'),
        ('icai_module', 'ICAI Module'),
        ('icai_publication', 'ICAI Publication'),
        ('icai_notes', 'ICAI Notes'),
        ('rtp', 'Revision Test Paper'),
        ('mtp', 'Mock Test Paper'),
        ('pyq', 'Previous Year Question Paper'),
        ('suggested_answer', 'Suggested Answers'),
        ('teacher_notes', 'Teacher Notes'),
        ('question_bank', 'Question Bank'),
        ('formula_sheet', 'Formula Sheet'),
        ('chapter_notes', 'Chapter Notes'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('chunking', 'Chunking'),
        ('embedding', 'Generating Embeddings'),
        ('ready', 'Ready'),
        ('error', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    doc_type = models.CharField(max_length=30, choices=DOC_TYPES)
    file = models.FileField(upload_to='knowledge/documents/')
    file_type = models.CharField(max_length=10, blank=True)  # pdf, docx, txt
    file_size = models.IntegerField(default=0, help_text='Bytes')
    page_count = models.IntegerField(default=0)

    # Categorization
    subject = models.ForeignKey('curriculum.Subject', on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    chapter = models.ForeignKey('curriculum.Chapter', on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    year = models.IntegerField(null=True, blank=True, help_text='Exam year for PYQ/RTP/MTP')
    session = models.CharField(max_length=20, blank=True, help_text='May/November')

    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    error_message = models.TextField(blank=True)
    chunk_count = models.IntegerField(default=0)
    processing_time = models.FloatField(default=0.0, help_text='Seconds')

    # Priority
    priority = models.IntegerField(default=5, help_text='1=highest, 10=lowest for RAG retrieval')

    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', '-created_at']
        verbose_name = 'Knowledge Document'
        verbose_name_plural = 'Knowledge Documents'

    def __str__(self):
        return f"[{self.get_doc_type_display()}] {self.title}"


class DocumentChunk(models.Model):
    """Individual text chunks from documents with vector embeddings."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name='chunks')
    content = models.TextField()
    chunk_index = models.IntegerField(default=0)
    page_number = models.IntegerField(null=True, blank=True)
    token_count = models.IntegerField(default=0)

    # Vector embedding (768 dimensions for Gemini text-embedding-004)
    embedding = VectorField(dimensions=768, null=True, blank=True)

    # Categorization
    subject = models.ForeignKey('curriculum.Subject', on_delete=models.SET_NULL, null=True, blank=True)
    chapter = models.ForeignKey('curriculum.Chapter', on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.ForeignKey('curriculum.Topic', on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['document', 'chunk_index']
        verbose_name = 'Document Chunk'
        verbose_name_plural = 'Document Chunks'
        indexes = [
            models.Index(fields=['document', 'chunk_index']),
        ]

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document.title[:50]}"


class KnowledgeCitation(models.Model):
    """Track which document chunks were used in AI responses."""
    chunk = models.ForeignKey(DocumentChunk, on_delete=models.CASCADE, related_name='citations')
    conversation_id = models.CharField(max_length=100)
    relevance_score = models.FloatField(default=0.0)
    was_helpful = models.BooleanField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Knowledge Citation'

    def __str__(self):
        return f"Citation: {self.chunk.document.title[:30]} (score={self.relevance_score:.2f})"


class PreviousYearQuestion(models.Model):
    """Extracted previous year questions for exam intelligence."""
    subject = models.ForeignKey('curriculum.Subject', on_delete=models.CASCADE, related_name='pyq_questions')
    chapter = models.ForeignKey('curriculum.Chapter', on_delete=models.SET_NULL, null=True, blank=True, related_name='pyq_questions')
    topic = models.ForeignKey('curriculum.Topic', on_delete=models.SET_NULL, null=True, blank=True, related_name='pyq_questions')

    question_text = models.TextField()
    answer_text = models.TextField(blank=True)
    marks = models.IntegerField(default=1)
    year = models.IntegerField()
    session = models.CharField(max_length=20, blank=True)
    question_type = models.CharField(max_length=20, default='mcq')
    difficulty = models.CharField(max_length=10, default='medium')

    # Exam intelligence
    frequency_score = models.FloatField(default=1.0, help_text='How often similar questions appear')
    probability_score = models.FloatField(default=0.5, help_text='Probability of appearing in next exam')

    source_document = models.ForeignKey(KnowledgeDocument, on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-year', 'subject']
        verbose_name = 'Previous Year Question'

    def __str__(self):
        return f"[{self.year}] {self.question_text[:80]}"


class RTPDocument(models.Model):
    """RTP-specific metadata and analysis."""
    document = models.OneToOneField(KnowledgeDocument, on_delete=models.CASCADE, related_name='rtp_metadata')
    year = models.IntegerField()
    session = models.CharField(max_length=20)
    analysis_json = models.JSONField(default=dict, blank=True, help_text='AI-generated analysis')
    trending_topics = models.JSONField(default=list, blank=True)
    importance_scores = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'RTP Document'

    def __str__(self):
        return f"RTP {self.year} {self.session}"


class MTPDocument(models.Model):
    """MTP-specific metadata and analysis."""
    document = models.OneToOneField(KnowledgeDocument, on_delete=models.CASCADE, related_name='mtp_metadata')
    year = models.IntegerField()
    session = models.CharField(max_length=20)
    analysis_json = models.JSONField(default=dict, blank=True)
    trending_topics = models.JSONField(default=list, blank=True)
    importance_scores = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'MTP Document'

    def __str__(self):
        return f"MTP {self.year} {self.session}"


class KnowledgeSummary(models.Model):
    """Auto-generated summaries from uploaded documents."""
    SUMMARY_TYPES = [
        ('short_notes', 'Short Notes'),
        ('revision_notes', 'Revision Notes'),
        ('formula_sheet', 'Formula Sheet'),
        ('memory_tricks', 'Memory Tricks'),
        ('chapter_summary', 'Chapter Summary'),
        ('mind_map', 'Mind Map'),
    ]

    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name='summaries', null=True, blank=True)
    chapter = models.ForeignKey('curriculum.Chapter', on_delete=models.CASCADE, related_name='knowledge_summaries', null=True, blank=True)
    summary_type = models.CharField(max_length=20, choices=SUMMARY_TYPES)
    title = models.CharField(max_length=300)
    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Knowledge Summary'
        verbose_name_plural = 'Knowledge Summaries'

    def __str__(self):
        return f"[{self.get_summary_type_display()}] {self.title}"
