import logging
from celery import shared_task
from .pipeline import DocumentPipeline

logger = logging.getLogger('apps.knowledge')

@shared_task(name='apps.knowledge.tasks.process_document_task')
def process_document_task(document_id):
    """
    Celery task wrapper to process uploaded documents (chunking, embedding).
    """
    logger.info(f"Triggered celery document processing task for ID: {document_id}")
    pipeline = DocumentPipeline()
    success = pipeline.process_document(document_id)
    if success:
        logger.info(f"Finished processing document: {document_id}")
    else:
        logger.error(f"Failed to process document: {document_id}")
    return success
