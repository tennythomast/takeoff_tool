# storage_retrieval/storage_service.py
"""
Storage Service Orchestrator

Main orchestrator for storing documents, chunks, and embeddings.
Coordinates between document store and vector stores.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .document_store import DocumentStore

logger = logging.getLogger(__name__)


class StorageService:
    """
    Main storage orchestrator that coordinates document storage,
    chunk storage, and vector storage.
    
    Features:
    - Atomic storage operations
    - Transaction management
    - Error handling and rollback
    - Cost tracking
    - Performance monitoring
    """
    
    def __init__(self, vector_store_type: str = 'pinecone'):
        """
        Initialize storage service.
        
        Args:
            vector_store_type: Type of vector store to use ('pinecone', 'pgvector', etc.)
        """
        self.document_store = DocumentStore()
        self.vector_store_type = vector_store_type
        self.vector_store = None
        
        # Initialize vector store if needed
        if vector_store_type == 'pinecone':
            try:
                from .vector_stores.pinecone_store import PineconeStore
                self.vector_store = PineconeStore()
                logger.info("Initialized Pinecone vector store")
            except ImportError:
                logger.warning("Pinecone not available, vector storage disabled")
        elif vector_store_type == 'pgvector':
            logger.info("PostgreSQL pgvector support coming soon")
    
    async def store_document(
        self,
        document_id: str,
        extraction_response: Dict[str, Any],
        file_metadata: Dict[str, Any],
        chunks: Optional[List[Dict[str, Any]]] = None,
        store_vectors: bool = True,
        knowledge_base_id: Optional[str] = None,
        storage_approach: str = 'chunked'
    ) -> Dict[str, Any]:
        """
        Store a complete document with extraction results and chunks.
        
        This is the main entry point for storing processed documents.
        
        Args:
            document_id: Unique document ID
            extraction_response: Complete extraction response from UnifiedExtractor
            file_metadata: File metadata (name, size, type, etc.)
            chunks: Optional pre-generated chunks (if None, will be generated for chunked approach)
            store_vectors: Whether to store embeddings in vector store
            knowledge_base_id: Knowledge base ID for vector store namespace
            storage_approach: Storage approach to use ('complete' or 'chunked')
            
        Returns:
            Storage result dictionary with status and metrics
        """
        start_time = datetime.utcnow()
        result = {
            'success': False,
            'document_id': document_id,
            'chunks_stored': 0,
            'vectors_stored': 0,
            'errors': [],
            'warnings': [],
            'storage_time_ms': 0,
        }
        
        try:
            # Add storage approach to file metadata
            file_metadata['storage_approach'] = storage_approach
            
            # Step 1: Store extraction response in PostgreSQL
            logger.info(f"Storing extraction for document: {document_id} using {storage_approach} approach")
            extraction_stored = await self.document_store.store_extraction(
                document_id=document_id,
                extraction_response=extraction_response,
                file_metadata=file_metadata
            )
            
            if not extraction_stored:
                result['errors'].append("Failed to store extraction response")
                return result
            
            # Step 2: Generate and store chunks only if using chunked approach
            if storage_approach == 'chunked':
                # Generate chunks if not provided
                if chunks is None:
                    logger.info(f"Generating chunks for document: {document_id}")
                    chunks = await self._generate_chunks(document_id, extraction_response)
                    
                    if not chunks:
                        result['warnings'].append("No chunks generated from document")
                
                # Store chunks in PostgreSQL
                if chunks:
                    logger.info(f"Storing {len(chunks)} chunks for document: {document_id}")
                    chunks_stored = await self.document_store.store_chunks(
                        document_id=document_id,
                        chunks=chunks
                    )
                    
                    if chunks_stored:
                        result['chunks_stored'] = len(chunks)
                    else:
                        result['errors'].append("Failed to store chunks")
                        return result
            else:
                # For complete storage, we don't need to store chunks
                result['chunks_stored'] = 0
            
            # Step 3: Store vectors in vector store (if enabled)
            if store_vectors and self.vector_store and knowledge_base_id:
                vectors_to_store = None
                
                # For complete storage, create a single vector from the document content
                if storage_approach == 'complete':
                    document_content = extraction_response.get('text', '')
                    if document_content:
                        vectors_to_store = [{
                            'chunk_index': 0,
                            'content': document_content,
                            'chunk_type': 'text',
                            'metadata': {
                                'storage_approach': 'complete',
                                'document_id': document_id,
                                'title': file_metadata.get('title', '')
                            },
                            'token_count': len(document_content) // 4  # Rough estimate
                        }]
                # For chunked approach, use the generated chunks
                elif chunks:
                    vectors_to_store = chunks
                
                # Store vectors if we have content
                if vectors_to_store:
                    logger.info(f"Storing vectors for document: {document_id}")
                    vectors_result = await self._store_vectors(
                        document_id=document_id,
                        chunks=vectors_to_store,
                        knowledge_base_id=knowledge_base_id
                    )
                    
                    if vectors_result['success']:
                        result['vectors_stored'] = vectors_result['count']
                    else:
                        result['warnings'].append(f"Vector storage failed: {vectors_result.get('error')}")
                else:
                    result['warnings'].append("No content available for vector storage")
            
            # Calculate storage time
            end_time = datetime.utcnow()
            result['storage_time_ms'] = int((end_time - start_time).total_seconds() * 1000)
            
            result['success'] = True
            logger.info(
                f"Successfully stored document {document_id}: "
                f"{result['chunks_stored']} chunks, {result['vectors_stored']} vectors "
                f"in {result['storage_time_ms']}ms"
            )
            
        except Exception as e:
            logger.error(f"Error storing document {document_id}: {e}", exc_info=True)
            result['errors'].append(str(e))
        
        return result
    
    async def store_chunks_only(
        self,
        document_id: str,
        chunks: List[Dict[str, Any]],
        store_vectors: bool = True,
        knowledge_base_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Store only chunks for an existing document.
        
        Useful for re-chunking or updating chunks without re-extracting.
        
        Args:
            document_id: Document ID
            chunks: List of chunk dictionaries
            store_vectors: Whether to store embeddings in vector store
            knowledge_base_id: Knowledge base ID for vector store namespace
            
        Returns:
            Storage result dictionary
        """
        result = {
            'success': False,
            'chunks_stored': 0,
            'vectors_stored': 0,
            'errors': [],
        }
        
        try:
            # Store chunks in PostgreSQL
            chunks_stored = await self.document_store.store_chunks(
                document_id=document_id,
                chunks=chunks
            )
            
            if not chunks_stored:
                result['errors'].append("Failed to store chunks")
                return result
            
            result['chunks_stored'] = len(chunks)
            
            # Store vectors if enabled
            if store_vectors and self.vector_store and knowledge_base_id:
                vectors_result = await self._store_vectors(
                    document_id=document_id,
                    chunks=chunks,
                    knowledge_base_id=knowledge_base_id
                )
                
                if vectors_result['success']:
                    result['vectors_stored'] = vectors_result['count']
                else:
                    result['errors'].append(f"Vector storage failed: {vectors_result.get('error')}")
            
            result['success'] = True
            
        except Exception as e:
            logger.error(f"Error storing chunks for document {document_id}: {e}", exc_info=True)
            result['errors'].append(str(e))
        
        return result
    
    async def delete_document(
        self,
        document_id: str,
        knowledge_base_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Delete a document and all associated data.
        
        Args:
            document_id: Document ID
            knowledge_base_id: Knowledge base ID for vector store cleanup
            
        Returns:
            Deletion result dictionary
        """
        result = {
            'success': False,
            'errors': [],
        }
        
        try:
            # Delete from PostgreSQL (soft delete)
            deleted = await self.document_store.delete_document(document_id)
            
            if not deleted:
                result['errors'].append("Failed to delete document from database")
                return result
            
            # Delete from vector store if available
            if self.vector_store and knowledge_base_id:
                try:
                    await self.vector_store.delete_document(
                        document_id=document_id,
                        namespace=knowledge_base_id
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete vectors for document {document_id}: {e}")
                    result['errors'].append(f"Vector deletion failed: {str(e)}")
            
            result['success'] = True
            logger.info(f"Deleted document: {document_id}")
            
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}", exc_info=True)
            result['errors'].append(str(e))
        
        return result
    
    async def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve complete document data.
        
        Args:
            document_id: Document ID
            
        Returns:
            Document data dictionary or None
        """
        try:
            # Get document metadata
            metadata = await self.document_store.get_document_metadata(document_id)
            if not metadata:
                return None
                
            # Get extraction data
            extraction = await self.document_store.get_extraction(document_id)
            
            # Get chunks (if any)
            storage_approach = metadata.get('storage_approach', 'chunked')
            chunks = [] if storage_approach == 'complete' else await self.document_store.get_chunks(document_id)
            
            return {
                **metadata,
                'extraction': extraction,
                'chunks': chunks,
                'content': extraction.get('text', '') if extraction else ''
            }
            
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None
    
    async def get_storage_statistics(
        self,
        knowledge_base_id: str
    ) -> Dict[str, Any]:
        """
        Get storage statistics for a knowledge base.
        
        Args:
            knowledge_base_id: Knowledge base ID
            
        Returns:
            Statistics dictionary
        """
        try:
            documents = await self.document_store.get_documents_by_knowledge_base(
                knowledge_base_id=knowledge_base_id
            )
            
            total_chunks = sum(doc['chunk_count'] for doc in documents)
            total_tokens = sum(doc['token_count'] for doc in documents)
            total_cost = sum(doc['extraction_cost_usd'] for doc in documents)
            
            avg_quality = (
                sum(doc['extraction_quality_score'] for doc in documents) / len(documents)
                if documents else 0.0
            )
            
            return {
                'document_count': len(documents),
                'total_chunks': total_chunks,
                'total_tokens': total_tokens,
                'total_extraction_cost_usd': total_cost,
                'average_quality_score': avg_quality,
                'documents': documents,
            }
            
        except Exception as e:
            logger.error(f"Error getting storage statistics for KB {knowledge_base_id}: {e}")
            return {
                'document_count': 0,
                'total_chunks': 0,
                'total_tokens': 0,
                'total_extraction_cost_usd': 0.0,
                'average_quality_score': 0.0,
                'documents': [],
            }
    
    async def _generate_chunks(
        self,
        document_id: str,
        extraction_response: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate chunks from extraction response.
        
        Args:
            document_id: Document ID
            extraction_response: Extraction response
            
        Returns:
            List of chunk dictionaries
        """
        try:
            from rag_service.services.chunking.chunking_service import ChunkingService
            from rag_service.models import Document
            from asgiref.sync import sync_to_async
            
            # Get document instance
            @sync_to_async
            def get_document():
                return Document.objects.get(id=document_id)
            
            document = await get_document()
            
            # Generate chunks
            chunking_service = ChunkingService()
            chunk_objects = chunking_service.chunk_document(extraction_response, document)
            
            # Convert to dictionaries
            chunks = []
            for chunk in chunk_objects:
                chunks.append({
                    'chunk_index': chunk.chunk_index,
                    'content': chunk.content,
                    'chunk_type': chunk.chunk_type,
                    'metadata': chunk.metadata,
                    'token_count': chunk.token_count,
                })
            
            return chunks
            
        except Exception as e:
            logger.error(f"Error generating chunks for document {document_id}: {e}")
            return []
    
    async def _store_vectors(
        self,
        document_id: str,
        chunks: List[Dict[str, Any]],
        knowledge_base_id: str
    ) -> Dict[str, Any]:
        """
        Store chunk embeddings in vector store.
        
        Args:
            document_id: Document ID
            chunks: List of chunk dictionaries
            knowledge_base_id: Knowledge base ID for namespace
            
        Returns:
            Result dictionary with success status and count
        """
        if not self.vector_store:
            return {
                'success': False,
                'error': 'Vector store not initialized',
                'count': 0
            }
        
        try:
            # Generate embeddings for chunks
            from rag_service.services.embedding.embedding_service import EmbeddingService
            
            embedding_service = EmbeddingService()
            
            # Extract text content from chunks
            texts = [chunk['content'] for chunk in chunks]
            
            # Generate embeddings
            embeddings_result = await embedding_service.generate_embeddings(
                texts=texts,
                model_name='text-embedding-3-small'  # TODO: Make configurable
            )
            
            if not embeddings_result['success']:
                return {
                    'success': False,
                    'error': embeddings_result.get('error', 'Embedding generation failed'),
                    'count': 0
                }
            
            # Prepare vectors for storage
            vectors = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings_result['embeddings'])):
                vector_id = f"{document_id}_{chunk['chunk_index']}"
                vectors.append({
                    'id': vector_id,
                    'values': embedding,
                    'metadata': {
                        'document_id': document_id,
                        'chunk_index': chunk['chunk_index'],
                        'chunk_type': chunk['chunk_type'],
                        'content': chunk['content'][:1000],  # Truncate for metadata
                        **chunk.get('metadata', {})
                    }
                })
            
            # Store in vector store
            result = await self.vector_store.upsert_vectors(
                vectors=vectors,
                namespace=knowledge_base_id
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error storing vectors for document {document_id}: {e}")
            return {
                'success': False,
                'error': str(e),
                'count': 0
            }
