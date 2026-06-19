"""
AI Engine App - Models
Prompt templates, AI settings, and success predictions.
"""
import uuid
from django.db import models
from django.conf import settings


class PromptTemplate(models.Model):
    """Admin-editable prompt templates for different AI interactions."""
    CATEGORIES = [
        ('teaching', 'Teaching'),
        ('revision', 'Revision'),
        ('mcq_generation', 'MCQ Generation'),
        ('mock_test', 'Mock Test'),
        ('analysis', 'Analysis'),
        ('motivation', 'Motivation'),
        ('explanation', 'Explanation'),
        ('voice', 'Voice Interaction'),
        ('summary', 'Summary Generation'),
        ('checkin', 'Daily Check-in'),
    ]

    name = models.CharField(max_length=200, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    description = models.TextField(blank=True)
    template_text = models.TextField(help_text='Use {variable_name} for dynamic content')
    system_prompt = models.TextField(blank=True, help_text='System context for AI')
    variables = models.JSONField(default=list, blank=True, help_text='List of variable names')
    is_active = models.BooleanField(default=True)
    version = models.IntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Prompt Template'

    def __str__(self):
        return f"[{self.category}] {self.name}"

    def render(self, **kwargs):
        """Render the template with provided variables."""
        rendered = self.template_text
        for key, value in kwargs.items():
            rendered = rendered.replace(f'{{{key}}}', str(value))
        return rendered


class AISettings(models.Model):
    """Global AI configuration — singleton model."""
    model_name = models.CharField(max_length=100, default='gemini-2.5-pro')
    temperature = models.FloatField(default=0.7)
    max_tokens = models.IntegerField(default=8192)
    memory_token_limit = models.IntegerField(default=3000)
    max_memory_token_limit = models.IntegerField(default=5000)
    embedding_model = models.CharField(max_length=100, default='text-embedding-004')
    embedding_dimensions = models.IntegerField(default=768)

    # Teaching style defaults
    default_teaching_steps = models.IntegerField(default=9)
    use_stories = models.BooleanField(default=True)
    use_funny_examples = models.BooleanField(default=True)
    use_memory_tricks = models.BooleanField(default=True)

    # RAG settings
    rag_top_k = models.IntegerField(default=5, help_text='Number of chunks to retrieve')
    rag_similarity_threshold = models.FloatField(default=0.7, help_text='Minimum cosine similarity')
    rag_priority_icai = models.BooleanField(default=True, help_text='Prioritize ICAI content')

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'AI Settings'
        verbose_name_plural = 'AI Settings'

    def __str__(self):
        return f"AI Settings (Model: {self.model_name})"

    def save(self, *args, **kwargs):
        # Ensure singleton
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class ChatSession(models.Model):
    """
    Persistent chat session record. Every conversation (chat, teaching, revision)
    is grouped under a ChatSession for long-term memory and sidebar display.
    """
    SESSION_TYPES = [
        ('chat', 'Chat'),
        ('teaching', 'Teaching Session'),
        ('revision', 'Revision'),
    ]

    id = models.CharField(max_length=100, primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=300, default='New Chat')
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES, default='chat')
    is_active = models.BooleanField(default=True)
    message_count = models.IntegerField(default=0)
    last_summary = models.TextField(blank=True, help_text='AI-compressed summary of this session for long-term memory')
    subject = models.ForeignKey('curriculum.Subject', on_delete=models.SET_NULL, null=True, blank=True)
    chapter = models.ForeignKey('curriculum.Chapter', on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.ForeignKey('curriculum.Topic', on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Chat Session'

    def __str__(self):
        return f"[{self.session_type}] {self.title}"


class ConversationLog(models.Model):
    """Store AI conversation history for context."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversations')
    session_id = models.CharField(max_length=100, db_index=True)
    chat_session = models.ForeignKey(ChatSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')

    INTERACTION_TYPES = [
        ('chat', 'Chat'),
        ('teaching', 'Teaching Session'),
        ('revision', 'Revision'),
        ('voice', 'Voice Interaction'),
        ('mcq', 'MCQ Practice'),
        ('doubt', 'Doubt Solving'),
    ]

    interaction_type = models.CharField(max_length=20, choices=INTERACTION_TYPES, default='chat')
    user_message = models.TextField()
    ai_response = models.TextField()
    subject = models.ForeignKey('curriculum.Subject', on_delete=models.SET_NULL, null=True, blank=True)
    chapter = models.ForeignKey('curriculum.Chapter', on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.ForeignKey('curriculum.Topic', on_delete=models.SET_NULL, null=True, blank=True)

    # Context tracking
    memory_tokens_used = models.IntegerField(default=0)
    rag_chunks_used = models.IntegerField(default=0)
    citations = models.JSONField(default=list, blank=True)

    # Feedback
    was_helpful = models.BooleanField(null=True, blank=True)
    feedback = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Conversation Log'

    def __str__(self):
        return f"[{self.interaction_type}] {self.user_message[:50]}"


class SuccessPrediction(models.Model):
    """Exam readiness and pass probability predictions."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='success_predictions')

    readiness_score = models.FloatField(default=0.0, help_text='0-100')
    pass_probability = models.FloatField(default=0.0, help_text='0-100')
    risk_score = models.FloatField(default=50.0, help_text='0-100, higher = more risk')
    subject_risks = models.JSONField(default=dict, blank=True, help_text='Risk per subject')
    strengths = models.JSONField(default=list, blank=True)
    weaknesses = models.JSONField(default=list, blank=True)
    recommendations = models.JSONField(default=list, blank=True)

    # Factors
    study_hours_factor = models.FloatField(default=0.0)
    consistency_factor = models.FloatField(default=0.0)
    revision_factor = models.FloatField(default=0.0)
    test_score_factor = models.FloatField(default=0.0)

    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-computed_at']
        verbose_name = 'Success Prediction'

    def __str__(self):
        return f"Readiness: {self.readiness_score}%, Pass: {self.pass_probability}%"
