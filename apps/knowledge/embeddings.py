import logging
from apps.ai_engine.gemini_client import GeminiClient

logger = logging.getLogger('apps.knowledge')

class EmbeddingService:
    def __init__(self):
        self.client = GeminiClient()

    def generate_embedding(self, text):
        """
        Generate embedding for a single text string using text-embedding-004.
        """
        if not text or not text.strip():
            return None
        return self.client.get_embedding(text)

    def generate_embeddings_batch(self, texts):
        """
        Generate embeddings for a list of text chunks.
        """
        embeddings = []
        for text in texts:
            emb = self.generate_embedding(text)
            embeddings.append(emb)
        return embeddings
