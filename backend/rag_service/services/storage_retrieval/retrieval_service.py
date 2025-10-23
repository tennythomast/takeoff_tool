# storage_retrieval/retrieval_service.py
"""
Retrieval Service

Orchestrates document retrieval with vector search, hybrid search, and reranking.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .document_store import DocumentStore

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    Retrieval service that orchestrates vector search, hybrid search, and reranking.
    
    Features:
    - Vector similarity search
    - Hybrid search (vector + keyword)
    - Result reranking
    - Metadata filtering
    - Performance tracking
    """
    
    def __init__(self, vector_store_type: str = 'pinecone'):
        """
        Initialize retrieval service.
        
        Args:
            vector_store_type: Type of vector store ('pinecone', 'pgvector', etc.)
        """
        self.document_store = DocumentStore()
        self.vector_store_type = vector_store_type
        self.vector_store = None
        
        # Initialize vector store
        if vector_store_type == 'pinecone':
            try:
                from .vector_stores.pinecone_store import PineconeStore
                self.vector_store = PineconeStore()
                logger.info("Initialized Pinecone vector store for retrieval")
            except ImportError:
                logger.warning("Pinecone not available, retrieval limited to database only")
    
    async def retrieve(
        self,
        query: str,
        knowledge_base_id: str,
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
        use_reranking: bool = False,
        rerank_top_k: int = 20,
        organization=None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: Query text
            knowledge_base_id: Knowledge base ID
            top_k: Number of results to return
            filter: Optional metadata filter
            use_reranking: Whether to use reranking
            rerank_top_k: Number of candidates to retrieve before reranking
            organization: Organization for API key lookup
            
        Returns:
            List of result dictionaries with:
                - chunk_id: str
                - content: str
                - score: float
                - metadata: Dict
                - document_id: str
        """
        start_time = datetime.utcnow()
        
        try:
            # Generate query embedding
            from rag_service.services.embedding.embedding_service import EmbeddingService
            
            embedding_service = VoyageEmbeddingService()
            embedding_result = await embedding_service.generate_embeddings(
                texts=[query],
                model_name='text-embedding-3-small'  # TODO: Make configurable
            )
            
            if not embedding_result['success']:
                logger.error(f"Failed to generate query embedding: {embedding_result.get('error')}")
                return []
            
            query_vector = embedding_result['embeddings'][0]
            
            # Determine how many candidates to retrieve
            candidates_k = rerank_top_k if use_reranking else top_k
            
            # Search vector store
            if self.vector_store:
                # Initialize if needed
                if not self.vector_store.index:
                    await self.vector_store.initialize(create_if_not_exists=False)
                
                # Search
                search_results = await self.vector_store.search(
                    query_vector=query_vector,
                    top_k=candidates_k,
                    filter=filter,
                    namespace=knowledge_base_id,
                    include_metadata=True
                )
                
                # Convert to result format
                results = []
                for result in search_results:
                    results.append({
                        'chunk_id': result.chunk_id,
                        'content': result.content,
                        'score': result.score,
                        'metadata': result.metadata,
                        'document_id': result.metadata.get('document_id', ''),
                    })
            else:
                logger.warning("No vector store available, cannot perform retrieval")
                return []
            
            # Apply reranking if requested
            if use_reranking and results:
                from .reranker import Reranker
                
                reranker = Reranker()
                results = await reranker.rerank(
                    query=query,
                    results=results,
                    top_k=top_k
                )
            else:
                # Limit to top_k
                results = results[:top_k]
            
            # Update chunk statistics
            for result in results:
                await self.document_store.update_chunk_statistics(
                    chunk_id=result['chunk_id'],
                    relevance_score=result['score']
                )
            
            # Calculate retrieval time
            end_time = datetime.utcnow()
            retrieval_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            logger.info(
                f"Retrieved {len(results)} chunks for query in {retrieval_time_ms}ms "
                f"(KB: {knowledge_base_id}, reranking: {use_reranking})"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Error during retrieval: {e}", exc_info=True)
            return []
    
    async def retrieve_by_document(
        self,
        document_id: str,
        query: str,
        top_k: int = 5,
        use_reranking: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieve chunks from a specific document.
        
        Args:
            document_id: Document ID
            query: Query text
            top_k: Number of results
            use_reranking: Whether to use reranking
            
        Returns:
            List of result dictionaries
        """
        # Use document_id as filter
        filter = {'document_id': document_id}
        
        # Get document to find knowledge base
        doc_metadata = await self.document_store.get_document_metadata(document_id)
        if not doc_metadata:
            logger.error(f"Document not found: {document_id}")
            return []
        
        # Retrieve with filter
        return await self.retrieve(
            query=query,
            knowledge_base_id=doc_metadata.get('knowledge_base_id', ''),
            top_k=top_k,
            filter=filter,
            use_reranking=use_reranking
        )
    
    async def get_chunk_context(
        self,
        chunk_id: str,
        context_window: int = 2
    ) -> Dict[str, Any]:
        """
        Get a chunk with surrounding context chunks.
        
        Args:
            chunk_id: Chunk ID
            context_window: Number of chunks before/after to include
            
        Returns:
            Dictionary with chunk and context
        """
        try:
            # Get the target chunk
            chunk = await self.document_store.get_chunk_by_id(chunk_id)
            if not chunk:
                return {}
            
            document_id = chunk['document_id']
            chunk_index = chunk['chunk_index']
            
            # Get all chunks for the document
            all_chunks = await self.document_store.get_chunks(document_id)
            
            # Find surrounding chunks
            context_before = []
            context_after = []
            
            for c in all_chunks:
                if c['chunk_index'] < chunk_index and c['chunk_index'] >= chunk_index - context_window:
                    context_before.append(c)
                elif c['chunk_index'] > chunk_index and c['chunk_index'] <= chunk_index + context_window:
                    context_after.append(c)
            
            # Sort context
            context_before.sort(key=lambda x: x['chunk_index'])
            context_after.sort(key=lambda x: x['chunk_index'])
            
            return {
                'chunk': chunk,
                'context_before': context_before,
                'context_after': context_after,
                'full_context': context_before + [chunk] + context_after
            }
            
        except Exception as e:
            logger.error(f"Error getting chunk context: {e}")
            return {}
