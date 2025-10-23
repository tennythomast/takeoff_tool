# storage_retrieval/hybrid_search.py
"""
Hybrid Search

Combines vector similarity search with keyword/BM25 search for better results.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class HybridSearch:
    """
    Hybrid search that combines vector and keyword search.
    
    Strategies:
    - Vector search: Semantic similarity
    - Keyword search: BM25 or full-text search
    - Fusion: Reciprocal Rank Fusion (RRF) or weighted combination
    """
    
    def __init__(
        self,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        fusion_method: str = 'rrf'
    ):
        """
        Initialize hybrid search.
        
        Args:
            vector_weight: Weight for vector search results (0-1)
            keyword_weight: Weight for keyword search results (0-1)
            fusion_method: Method to combine results ('rrf', 'weighted')
        """
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.fusion_method = fusion_method
    
    async def search(
        self,
        query: str,
        query_vector: List[float],
        knowledge_base_id: str,
        top_k: int = 5,
        filter: Optional[Dict[str, Any]] = None,
        vector_store=None,
        document_store=None
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector and keyword search.
        
        Args:
            query: Query text
            query_vector: Query embedding vector
            knowledge_base_id: Knowledge base ID
            top_k: Number of results to return
            filter: Optional metadata filter
            vector_store: Vector store instance
            document_store: Document store instance
            
        Returns:
            List of search results
        """
        try:
            # Perform vector search
            vector_results = []
            if vector_store:
                vector_results = await vector_store.search(
                    query_vector=query_vector,
                    top_k=top_k * 2,  # Get more candidates for fusion
                    filter=filter,
                    namespace=knowledge_base_id
                )
            
            # Perform keyword search
            keyword_results = []
            if document_store:
                keyword_results = await self._keyword_search(
                    query=query,
                    knowledge_base_id=knowledge_base_id,
                    top_k=top_k * 2,
                    filter=filter,
                    document_store=document_store
                )
            
            # Fuse results
            if self.fusion_method == 'rrf':
                fused_results = self._reciprocal_rank_fusion(
                    vector_results=vector_results,
                    keyword_results=keyword_results,
                    k=60  # RRF parameter
                )
            else:
                fused_results = self._weighted_fusion(
                    vector_results=vector_results,
                    keyword_results=keyword_results
                )
            
            # Return top_k results
            return fused_results[:top_k]
            
        except Exception as e:
            logger.error(f"Error during hybrid search: {e}", exc_info=True)
            return []
    
    async def _keyword_search(
        self,
        query: str,
        knowledge_base_id: str,
        top_k: int,
        filter: Optional[Dict[str, Any]],
        document_store
    ) -> List[Dict[str, Any]]:
        """
        Perform keyword search using PostgreSQL full-text search.
        
        Args:
            query: Query text
            knowledge_base_id: Knowledge base ID
            top_k: Number of results
            filter: Optional filter
            document_store: Document store instance
            
        Returns:
            List of search results
        """
        # TODO: Implement full-text search using PostgreSQL
        # For now, return empty list
        logger.warning("Keyword search not yet implemented")
        return []
    
    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Any],
        keyword_results: List[Any],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Combine results using Reciprocal Rank Fusion (RRF).
        
        RRF formula: score = sum(1 / (k + rank))
        
        Args:
            vector_results: Vector search results
            keyword_results: Keyword search results
            k: RRF constant (typically 60)
            
        Returns:
            Fused results sorted by RRF score
        """
        # Build score map
        scores = {}
        
        # Add vector results
        for rank, result in enumerate(vector_results, start=1):
            chunk_id = result.chunk_id if hasattr(result, 'chunk_id') else result.get('chunk_id')
            if chunk_id not in scores:
                scores[chunk_id] = {
                    'rrf_score': 0,
                    'result': result
                }
            scores[chunk_id]['rrf_score'] += 1 / (k + rank)
        
        # Add keyword results
        for rank, result in enumerate(keyword_results, start=1):
            chunk_id = result.get('chunk_id')
            if chunk_id not in scores:
                scores[chunk_id] = {
                    'rrf_score': 0,
                    'result': result
                }
            scores[chunk_id]['rrf_score'] += 1 / (k + rank)
        
        # Sort by RRF score
        sorted_results = sorted(
            scores.values(),
            key=lambda x: x['rrf_score'],
            reverse=True
        )
        
        # Convert to result format
        fused = []
        for item in sorted_results:
            result = item['result']
            
            # Convert SearchResult to dict if needed
            if hasattr(result, 'chunk_id'):
                fused.append({
                    'chunk_id': result.chunk_id,
                    'content': result.content,
                    'score': item['rrf_score'],
                    'metadata': result.metadata,
                    'fusion_method': 'rrf'
                })
            else:
                result_dict = {**result}
                result_dict['score'] = item['rrf_score']
                result_dict['fusion_method'] = 'rrf'
                fused.append(result_dict)
        
        return fused
    
    def _weighted_fusion(
        self,
        vector_results: List[Any],
        keyword_results: List[Any]
    ) -> List[Dict[str, Any]]:
        """
        Combine results using weighted score fusion.
        
        Args:
            vector_results: Vector search results
            keyword_results: Keyword search results
            
        Returns:
            Fused results sorted by weighted score
        """
        # Build score map
        scores = {}
        
        # Add vector results
        for result in vector_results:
            chunk_id = result.chunk_id if hasattr(result, 'chunk_id') else result.get('chunk_id')
            if chunk_id not in scores:
                scores[chunk_id] = {
                    'vector_score': 0,
                    'keyword_score': 0,
                    'result': result
                }
            scores[chunk_id]['vector_score'] = result.score if hasattr(result, 'score') else result.get('score', 0)
        
        # Add keyword results
        for result in keyword_results:
            chunk_id = result.get('chunk_id')
            if chunk_id not in scores:
                scores[chunk_id] = {
                    'vector_score': 0,
                    'keyword_score': 0,
                    'result': result
                }
            scores[chunk_id]['keyword_score'] = result.get('score', 0)
        
        # Calculate weighted scores
        for chunk_id, data in scores.items():
            data['weighted_score'] = (
                self.vector_weight * data['vector_score'] +
                self.keyword_weight * data['keyword_score']
            )
        
        # Sort by weighted score
        sorted_results = sorted(
            scores.values(),
            key=lambda x: x['weighted_score'],
            reverse=True
        )
        
        # Convert to result format
        fused = []
        for item in sorted_results:
            result = item['result']
            
            # Convert SearchResult to dict if needed
            if hasattr(result, 'chunk_id'):
                fused.append({
                    'chunk_id': result.chunk_id,
                    'content': result.content,
                    'score': item['weighted_score'],
                    'metadata': result.metadata,
                    'fusion_method': 'weighted',
                    'vector_score': item['vector_score'],
                    'keyword_score': item['keyword_score']
                })
            else:
                result_dict = {**result}
                result_dict['score'] = item['weighted_score']
                result_dict['fusion_method'] = 'weighted'
                result_dict['vector_score'] = item['vector_score']
                result_dict['keyword_score'] = item['keyword_score']
                fused.append(result_dict)
        
        return fused
