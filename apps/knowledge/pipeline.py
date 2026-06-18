import os
import re
import logging
import PyPDF2
import docx
import tiktoken
from django.conf import settings
from django.utils import timezone
from .models import KnowledgeDocument, DocumentChunk
from .embeddings import EmbeddingService

logger = logging.getLogger('apps.knowledge')

class DocumentPipeline:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception:
            self.tokenizer = tiktoken.get_encoding("gpt2")

    def count_tokens(self, text):
        return len(self.tokenizer.encode(text))

    def extract_text(self, file_path, file_type):
        """Extract text from PDF, DOCX, or TXT file."""
        text = ""
        page_count = 0
        pages_text = []

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        if file_type == 'pdf':
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                page_count = len(reader.pages)
                for page_num in range(page_count):
                    page_text = reader.pages[page_num].extract_text() or ""
                    pages_text.append((page_num + 1, page_text))
                    text += page_text

        elif file_type == 'docx':
            doc = docx.Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs]
            text = "\n".join(paragraphs)
            page_count = max(1, len(paragraphs) // 15)  # Estimate pages
            pages_text.append((1, text))

        else: # txt/other
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
            page_count = 1
            pages_text.append((1, text))

        return text, page_count, pages_text

    def clean_text(self, text):
        """Standard cleaning of text."""
        # Replace multiple spaces/newlines
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n+', '\n', text)
        return text.strip()

    def chunk_text(self, pages_text, chunk_size=512, overlap=50):
        """
        Token-aware chunking keeping track of page numbers.
        """
        chunks = []
        
        for page_num, p_text in pages_text:
            cleaned = self.clean_text(p_text)
            tokens = self.tokenizer.encode(cleaned)
            
            i = 0
            while i < len(tokens):
                chunk_tokens = tokens[i : i + chunk_size]
                chunk_text = self.tokenizer.decode(chunk_tokens)
                
                if chunk_text.strip():
                    chunks.append({
                        'content': chunk_text,
                        'page_number': page_num,
                        'token_count': len(chunk_tokens)
                    })
                
                i += (chunk_size - overlap)
                
        return chunks

    def process_document(self, document_id):
        """
        Process document end-to-end: Extract, Clean, Chunk, Embed, Store.
        """
        start_time = timezone.now()
        
        try:
            doc = KnowledgeDocument.objects.get(id=document_id)
        except KnowledgeDocument.DoesNotExist:
            logger.error(f"KnowledgeDocument {document_id} not found.")
            return False

        try:
            doc.status = 'processing'
            doc.save()

            file_path = doc.file.path
            file_ext = os.path.splitext(file_path)[1].lower().replace('.', '')
            doc.file_type = file_ext
            doc.file_size = os.path.getsize(file_path)
            doc.save()

            # 1. Extract
            doc.status = 'chunking'
            doc.save()
            text, page_count, pages_text = self.extract_text(file_path, file_ext)
            
            doc.page_count = page_count
            doc.save()

            # 2. Chunk
            chunk_size = getattr(settings, 'CHUNK_SIZE', 512)
            overlap = getattr(settings, 'CHUNK_OVERLAP', 50)
            chunks_data = self.chunk_text(pages_text, chunk_size, overlap)

            if not chunks_data:
                raise ValueError("No text extracted or chunks generated from document.")

            doc.status = 'embedding'
            doc.save()

            # Remove any existing chunks for this document (re-processing safety)
            DocumentChunk.objects.filter(document=doc).delete()

            # 3. Embed & Store
            created_chunks = []
            for idx, chunk_info in enumerate(chunks_data):
                # Generate embedding
                embedding = self.embedding_service.generate_embedding(chunk_info['content'])
                
                chunk_obj = DocumentChunk(
                    document=doc,
                    content=chunk_info['content'],
                    chunk_index=idx,
                    page_number=chunk_info['page_number'],
                    token_count=chunk_info['token_count'],
                    embedding=embedding,
                    subject=doc.subject,
                    chapter=doc.chapter
                )
                created_chunks.append(chunk_obj)

            # Bulk create chunks to optimize db writes (pgvector handles bulk inserts too)
            DocumentChunk.objects.bulk_create(created_chunks)

            # 4. Finalize
            end_time = timezone.now()
            doc.status = 'ready'
            doc.chunk_count = len(created_chunks)
            doc.processing_time = (end_time - start_time).total_seconds()
            doc.error_message = ""
            doc.save()
            
            logger.info(f"Successfully processed document: {doc.title}. Chunks: {doc.chunk_count}")
            return True

        except Exception as e:
            logger.exception(f"Error processing document {document_id}")
            doc.status = 'error'
            doc.error_message = str(e)
            doc.save()
            return False
