# storage_retrieval/document_store.py
"""
Document Store for PostgreSQL

Stores extracted JSON data and metadata in PostgreSQL.
Keeps the full extraction response for reference without chunking.
This provides a simpler storage model for complete document content.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class DocumentStore:
    """
    Stores extracted JSON data and metadata in PostgreSQL.
    Keeps the full extraction response for reference without chunking.
    
    Features:
    - Atomic storage operations with transactions
    - Complete extraction response preservation
    - Direct document content storage
    - Cost and quality tracking
    - Status management
    """
    
    def __init__(self):
        """Initialize document store"""
        pass
    
    async def store_extraction(
        self,
        document_id: str,
        extraction_response: Dict[str, Any],
        file_metadata: Dict[str, Any]
    ) -> bool:
        """
        Store the complete extraction response.
        
        Args:
            document_id: Unique document ID
            extraction_response: Complete extraction response from UnifiedExtractor
                Expected fields:
                - text: str
                - layout_blocks: List[Dict]
                - tables: List[Dict]
                - entities: List[Dict]
                - summary: str
                - metadata: Dict
                - cost_usd: float
                - processing_time_ms: int
                - model_used: str
                - provider_used: str
                - success: bool
                - error: Optional[str]
                - warnings: List[str]
            file_metadata: File metadata (name, size, type, etc.)
        
        Returns:
            Success status
        """
        from rag_service.models import Document
        
        try:
            # Prepare extraction metadata
            extraction_metadata = {
                'text': extraction_response.get('text', ''),
                'layout_blocks': extraction_response.get('layout_blocks', []),
                'tables': extraction_response.get('tables', []),
                'entities': extraction_response.get('entities', []),
                'summary': extraction_response.get('summary', ''),
                'visual_elements': extraction_response.get('visual_elements'),
                'drawing_metadata': extraction_response.get('drawing_metadata'),
                'warnings': extraction_response.get('warnings', []),
                'success': extraction_response.get('success', True),
                'error': extraction_response.get('error'),
            }
            
            # Prepare document metadata
            document_metadata = {
                **file_metadata,
                'extraction_method': extraction_response.get('extraction_method', 'unified'),
                'extraction_timestamp': datetime.utcnow().isoformat(),
                'model_used': extraction_response.get('model_used'),
                'provider_used': extraction_response.get('provider_used'),
                'processing_time_ms': extraction_response.get('processing_time_ms', 0),
            }
            
            # Update or create document record
            @sync_to_async
            def update_document():
                document, created = Document.objects.update_or_create(
                    id=document_id,
                    defaults={
                        'extraction_metadata': extraction_metadata,
                        'metadata': document_metadata,
                        'extraction_method': extraction_response.get('extraction_method', 'unified'),
                        'extraction_cost_usd': Decimal(str(extraction_response.get('cost_usd', 0))),
                        'extraction_quality_score': self._calculate_quality_score(extraction_response),
                        'content': extraction_response.get('text', ''),
                        'status': 'completed' if extraction_response.get('success', True) else 'failed',
                        'processing_error': extraction_response.get('error', ''),
                        'processed_at': datetime.utcnow()
                    }
                )
                return document, created
            
            document, created = await update_document()
            
            logger.info(
                f"{'Created' if created else 'Updated'} document: {document_id} "
                f"(cost: ${extraction_response.get('cost_usd', 0):.4f}, "
                f"time: {extraction_response.get('processing_time_ms', 0)}ms)"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to store extraction for document {document_id}: {e}", exc_info=True)
            return False
    
    async def store_complete_extraction(
        self,
        document_id: str,
        extraction_response: Dict[str, Any],
        include_vector_embedding: bool = False
    ) -> bool:
        """
        Store the complete extraction response without chunking.
        
        Args:
            document_id: Document ID
            extraction_response: Complete extraction response with all content
                Expected fields:
                - text: str (Full document text)
                - tables: List[Dict] (Table data if available)
                - layout_blocks: List[Dict] (Layout information if available)
                - metadata: Dict (Document metadata)
                - model_used: str (Model used for extraction)
                - provider_used: str (Provider used for extraction)
            include_vector_embedding: Whether to include vector embedding in document
                
        Returns:
            Success status
        """
        from rag_service.models import Document
        
        try:
            # Get document
            @sync_to_async
            def get_document():
                try:
                    return Document.objects.get(id=document_id)
                except Document.DoesNotExist:
                    logger.error(f"Document not found: {document_id}")
                    return None
                    
            document = await get_document()
            if not document:
                return False
                
            # Update document with complete extraction
            @sync_to_async
            def update_document():
                with transaction.atomic():
                    # Update document content
                    document.content = extraction_response.get('text', '')
                    
                    # Store complete extraction response in metadata
                    document.extraction_metadata = {
                        'text': extraction_response.get('text', ''),
                        'tables': extraction_response.get('tables', []),
                        'layout_blocks': extraction_response.get('layout_blocks', []),
                        'entities': extraction_response.get('entities', []),
                        'summary': extraction_response.get('summary', ''),
                        'visual_elements': extraction_response.get('visual_elements', []),
                        'extraction_method': extraction_response.get('extraction_method', 'unified'),
                        'model_used': extraction_response.get('model_used'),
                        'provider_used': extraction_response.get('provider_used'),
                    }
                    
                    # Update document statistics
                    document.status = 'completed'
                    document.processed_at = datetime.utcnow()
                    document.extraction_cost_usd = Decimal(str(extraction_response.get('cost_usd', 0)))
                    document.save()
                    
                    # Update knowledge base statistics
                    document.knowledge_base.update_statistics()
            
            await update_document()
            
            logger.info(f"Stored complete extraction for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store extraction for document {document_id}: {e}", exc_info=True)
            return False
    
    async def get_extraction(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve complete extraction data for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            Complete extraction data or None if not found
        """
        from rag_service.models import Document
        
        try:
            @sync_to_async
            def get_document_data():
                try:
                    document = Document.objects.get(id=document_id)
                    
                    # Construct a complete extraction response from the document
                    extraction_data = {
                        'id': str(document.id),
                        'title': document.title,
                        'content': document.content,
                        'text': document.content,  # For consistency with extraction response format
                        'document_type': document.document_type,
                        'status': document.status,
                        'created_at': document.created_at.isoformat() if document.created_at else None,
                        'processed_at': document.processed_at.isoformat() if document.processed_at else None,
                        
                        # Include all extraction metadata
                        'tables': document.extraction_metadata.get('tables', []),
                        'layout_blocks': document.extraction_metadata.get('layout_blocks', []),
                        'entities': document.extraction_metadata.get('entities', []),
                        'summary': document.extraction_metadata.get('summary', ''),
                        'visual_elements': document.extraction_metadata.get('visual_elements', []),
                        
                        # Include document metadata
                        'metadata': document.metadata,
                        'extraction_metadata': document.extraction_metadata,
                        'extraction_method': document.extraction_method,
                        'model_used': document.extraction_metadata.get('model_used'),
                        'provider_used': document.extraction_metadata.get('provider_used'),
                        'cost_usd': float(document.extraction_cost_usd) if document.extraction_cost_usd else 0.0,
                    }
                    
                    # Record access
                    document.record_access()
                    
                    return extraction_data
                except Document.DoesNotExist:
                    return None
            
            return await get_document_data()
            
        except Exception as e:
            logger.error(f"Failed to get extraction for document {document_id}: {e}", exc_info=True)
            return None
    
    async def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve document metadata.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document metadata dictionary or None if not found
        """
        from rag_service.models import Document
        
        try:
            @sync_to_async
            def get_document():
                return Document.objects.get(id=document_id)
            
            document = await get_document()
            return {
                'id': str(document.id),
                'title': document.title,
                'document_type': document.document_type,
                'status': document.status,
                'extraction_method': document.extraction_method,
                'extraction_cost_usd': float(document.extraction_cost_usd),
                'extraction_quality_score': document.extraction_quality_score,
                'chunk_count': document.chunk_count,
                'token_count': document.token_count,
                'metadata': document.metadata,
                'created_at': document.created_at.isoformat() if document.created_at else None,
                'processed_at': document.processed_at.isoformat() if document.processed_at else None,
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve metadata for document {document_id}: {e}")
            return None
    
    async def get_chunks(
        self,
        document_id: str,
        chunk_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all chunks for a document.
        
        Args:
            document_id: Document ID
            chunk_type: Optional filter by chunk type
            
        Returns:
            List of chunk dictionaries
        """
        from rag_service.models import Chunk
        
        try:
            @sync_to_async
            def get_chunks_list():
                queryset = Chunk.objects.filter(document_id=document_id)
                if chunk_type:
                    queryset = queryset.filter(chunk_type=chunk_type)
                return list(queryset.order_by('chunk_index').values(
                    'id', 'chunk_index', 'content', 'chunk_type', 'metadata',
                    'token_count', 'embedding_vector_id', 'page_number'
                ))
            
            chunks = await get_chunks_list()
            
            # Convert to serializable format
            return [
                {
                    'id': str(chunk['id']),
                    'chunk_index': chunk['chunk_index'],
                    'content': chunk['content'],
                    'chunk_type': chunk['chunk_type'],
                    'metadata': chunk['metadata'],
                    'token_count': chunk['token_count'],
                    'embedding_vector_id': chunk['embedding_vector_id'],
                    'page_number': chunk['page_number'],
                }
                for chunk in chunks
            ]
            
        except Exception as e:
            logger.error(f"Failed to retrieve chunks for document {document_id}: {e}")
            return []
    
    async def get_chunk_by_id(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific chunk by ID.
        
        Args:
            chunk_id: Chunk ID
            
        Returns:
            Chunk dictionary or None if not found
        """
        from rag_service.models import Chunk
        
        try:
            @sync_to_async
            def get_chunk():
                return Chunk.objects.select_related('document').get(id=chunk_id)
            
            chunk = await get_chunk()
            
            return {
                'id': str(chunk.id),
                'document_id': str(chunk.document_id),
                'chunk_index': chunk.chunk_index,
                'content': chunk.content,
                'chunk_type': chunk.chunk_type,
                'metadata': chunk.metadata,
                'token_count': chunk.token_count,
                'embedding_vector_id': chunk.embedding_vector_id,
                'page_number': chunk.page_number,
                'retrieval_count': chunk.retrieval_count,
                'relevance_score_avg': chunk.relevance_score_avg,
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve chunk {chunk_id}: {e}")
            return None
    
    async def update_chunk_statistics(
        self,
        chunk_id: str,
        relevance_score: Optional[float] = None
    ) -> bool:
        """
        Update chunk retrieval statistics.
        
        Args:
            chunk_id: Chunk ID
            relevance_score: Optional relevance score to track
            
        Returns:
            Success status
        """
        from rag_service.models import Chunk
        
        try:
            @sync_to_async
            def update_stats():
                chunk = Chunk.objects.get(id=chunk_id)
                chunk.record_retrieval(relevance_score)
                return True
            
            await update_stats()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update statistics for chunk {chunk_id}: {e}")
            return False
    
    async def delete_document(self, document_id: str) -> bool:
        """
        Delete a document and all its chunks.
        
        Args:
            document_id: Document ID
            
        Returns:
            Success status
        """
        from rag_service.models import Document
        
        try:
            @sync_to_async
            @transaction.atomic
            def delete_doc():
                document = Document.objects.get(id=document_id)
                # Soft delete (sets is_active=False)
                document.delete()
                return True
            
            await delete_doc()
            logger.info(f"Deleted document: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False
    
    def _calculate_quality_score(self, extraction_response: Dict[str, Any]) -> float:
        """
        Calculate a quality score for the extraction.
        
        Args:
            extraction_response: Extraction response
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        score = 0.0
        
        # Base score for successful extraction
        if extraction_response.get('success', True):
            score += 0.3
        
        # Score for having text content
        if extraction_response.get('text'):
            score += 0.2
        
        # Score for having structured data
        if extraction_response.get('tables'):
            score += 0.15
        
        if extraction_response.get('layout_blocks'):
            score += 0.15
        
        if extraction_response.get('entities'):
            score += 0.1
        
        # Score for having summary
        if extraction_response.get('summary'):
            score += 0.1
        
        # Penalty for warnings
        warning_count = len(extraction_response.get('warnings', []))
        if warning_count > 0:
            score -= min(0.1 * warning_count, 0.3)
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))
    
    async def get_documents_by_knowledge_base(
        self,
        knowledge_base_id: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents for a knowledge base.
        
        Args:
            knowledge_base_id: Knowledge base ID
            status: Optional status filter
            limit: Maximum number of documents to return
            offset: Offset for pagination
            
        Returns:
            List of document metadata dictionaries
        """
        from rag_service.models import Document
        
        try:
            @sync_to_async
            def get_documents():
                queryset = Document.objects.filter(
                    knowledge_base_id=knowledge_base_id,
                    is_active=True
                )
                if status:
                    queryset = queryset.filter(status=status)
                
                return list(queryset.order_by('-created_at')[offset:offset+limit].values(
                    'id', 'title', 'document_type', 'status', 'extraction_method',
                    'extraction_cost_usd', 'extraction_quality_score', 'chunk_count',
                    'token_count', 'created_at', 'processed_at'
                ))
            
            documents = await get_documents()
            
            return [
                {
                    'id': str(doc['id']),
                    'title': doc['title'],
                    'document_type': doc['document_type'],
                    'status': doc['status'],
                    'extraction_method': doc['extraction_method'],
                    'extraction_cost_usd': float(doc['extraction_cost_usd']),
                    'extraction_quality_score': doc['extraction_quality_score'],
                    'chunk_count': doc['chunk_count'],
                    'token_count': doc['token_count'],
                    'created_at': doc['created_at'].isoformat() if doc['created_at'] else None,
                    'processed_at': doc['processed_at'].isoformat() if doc['processed_at'] else None,
                }
                for doc in documents
            ]
            
        except Exception as e:
            logger.error(f"Failed to retrieve documents for KB {knowledge_base_id}: {e}")
            return []
            
    async def search_documents_by_content(self, knowledge_base_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for documents by content using simple text search.
        
        Args:
            knowledge_base_id: Knowledge base ID to search within
            query: Text query to search for
            limit: Maximum number of results to return
            
        Returns:
            List of document dictionaries matching the query
        """
        from rag_service.models import Document
        from django.db.models import Q
        
        try:
            @sync_to_async
            def search_docs():
                # Perform a simple text search across document content and metadata
                return list(Document.objects.filter(
                    knowledge_base_id=knowledge_base_id,
                    is_active=True
                ).filter(
                    Q(content__icontains=query) |
                    Q(title__icontains=query) |
                    Q(extraction_metadata__text__icontains=query)
                ).order_by('-created_at')[:limit].values(
                    'id', 'title', 'content', 'document_type', 'status',
                    'created_at', 'processed_at', 'metadata', 'extraction_metadata'
                ))
                
            documents = await search_docs()
            return [{
                'id': str(doc['id']),
                'title': doc['title'],
                'content_preview': doc['content'][:200] + '...' if len(doc['content']) > 200 else doc['content'],
                'document_type': doc['document_type'],
                'status': doc['status'],
                'created_at': doc['created_at'].isoformat() if doc['created_at'] else None,
                'processed_at': doc['processed_at'].isoformat() if doc['processed_at'] else None,
                'metadata': doc['metadata'],
                'extraction_metadata': {
                    'tables_count': len(doc['extraction_metadata'].get('tables', [])),
                    'layout_blocks_count': len(doc['extraction_metadata'].get('layout_blocks', [])),
                    'has_summary': bool(doc['extraction_metadata'].get('summary')),
                }
            } for doc in documents]
            
        except Exception as e:
            logger.error(f"Failed to search documents in knowledge base {knowledge_base_id}: {e}", exc_info=True)
            return []
