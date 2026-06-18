import logging
from django.conf import settings
from .models import DocumentChunk, KnowledgeCitation
from .embeddings import EmbeddingService

logger = logging.getLogger('apps.knowledge')

try:
    is_sqlite = settings.DATABASES.get('default', {}).get('ENGINE', '').endswith('sqlite3')
except Exception:
    is_sqlite = False

if is_sqlite:
    CosineDistance = None
else:
    from pgvector.django import CosineDistance

class KnowledgeRetriever:
    def __init__(self):
        self.embedding_service = EmbeddingService()

    def retrieve_relevant_chunks(self, query, subject_id=None, chapter_id=None, limit=5, min_score=0.3):
        """
        Retrieves top relevant chunks from pgvector based on Cosine Similarity.
        On SQLite, falls back to text-based matching.
        """
        # Start queryset
        # Select only active documents
        queryset = DocumentChunk.objects.filter(document__status='ready')

        # Apply optional filters
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        if chapter_id:
            queryset = queryset.filter(chapter_id=chapter_id)

        if is_sqlite:
            # Simple keyword search fallback for SQLite
            matching_chunks = queryset.filter(content__icontains=query)[:limit]
            results = []
            for idx, chunk in enumerate(matching_chunks):
                results.append({
                    'chunk': chunk,
                    'similarity_score': 0.85 - (idx * 0.05),
                    'content': chunk.content,
                    'source': chunk.document.title,
                    'doc_type': chunk.document.get_doc_type_display(),
                    'page': chunk.page_number
                })
            return results

        query_embedding = self.embedding_service.generate_embedding(query)
        if not query_embedding:
            logger.error("Failed to generate query embedding.")
            return []

        # Annotate with cosine distance
        queryset = queryset.annotate(
            distance=CosineDistance('embedding', query_embedding)
        )

        # Retrieve chunks with distance <= threshold (lower distance means closer)
        # Cosine distance limit of 0.7 corresponds to similarity score of 0.3
        max_distance = 1.0 - min_score
        queryset = queryset.filter(distance__lte=max_distance).order_by('distance')[:limit]

        results = []
        for chunk in queryset:
            similarity = 1.0 - chunk.distance
            results.append({
                'chunk': chunk,
                'similarity_score': similarity,
                'content': chunk.content,
                'source': chunk.document.title,
                'doc_type': chunk.document.get_doc_type_display(),
                'page': chunk.page_number
            })
            
        return results

    def build_rag_context(self, query, subject_id=None, chapter_id=None, limit=5, conversation_id=None):
        """
        Queries relevant chunks, logs citations, and structures them into text block for LLM.
        """
        chunks_info = self.retrieve_relevant_chunks(
            query, subject_id=subject_id, chapter_id=chapter_id, limit=limit
        )

        if not chunks_info:
            return "No relevant ICAI study material found in the database. Rely on standard CA Foundation syllabus knowledge.", []

        context_parts = []
        citations_logged = []

        context_parts.append("=== ICAI STUDY MATERIAL CONTEXT ===")
        for idx, item in enumerate(chunks_info):
            chunk = item['chunk']
            score = item['similarity_score']
            context_parts.append(
                f"Source [{idx+1}]: {item['source']} (Page {item['page'] or 'N/A'}, Similarity: {score:.2f})\n"
                f"Content: {item['content']}\n"
                "----------------------------------------"
            )
            
            # Log citation for analytics/audit if conversation_id provided
            if conversation_id:
                try:
                    KnowledgeCitation.objects.create(
                        chunk=chunk,
                        conversation_id=conversation_id,
                        relevance_score=score
                    )
                except Exception as e:
                    logger.error(f"Error creating KnowledgeCitation: {e}")
            
            citations_logged.append({
                'source_num': idx + 1,
                'title': item['source'],
                'doc_type': item['doc_type'],
                'page': item['page'],
                'score': float(score)
            })

        return "\n".join(context_parts), citations_logged
