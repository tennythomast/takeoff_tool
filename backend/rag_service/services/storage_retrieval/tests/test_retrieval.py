# storage_retrieval/tests/test_retrieval.py
"""
Tests for Retrieval Service
"""

import pytest
from django.test import TestCase
from unittest.mock import Mock, patch, AsyncMock
import uuid

from rag_service.services.storage_retrieval import RetrievalService
from rag_service.services.storage_retrieval.vector_stores.base import SearchResult


class TestRetrievalService(TestCase):
    """Test RetrievalService functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.retrieval_service = RetrievalService(vector_store_type='pinecone')
        self.knowledge_base_id = str(uuid.uuid4())
    
    @pytest.mark.asyncio
    async def test_retrieve(self):
        """Test basic retrieval"""
        query = "What are the safety requirements?"
        
        # Mock embedding service
        mock_embedding_result = {
            'success': True,
            'embeddings': [[0.1] * 1536]  # Mock embedding vector
        }
        
        # Mock search results
        mock_search_results = [
            SearchResult(
                chunk_id='chunk-1',
                score=0.95,
                metadata={'document_id': 'doc-1', 'page': 1},
                content='Safety requirement content'
            ),
            SearchResult(
                chunk_id='chunk-2',
                score=0.85,
                metadata={'document_id': 'doc-1', 'page': 2},
                content='Additional safety info'
            )
        ]
        
        with patch('rag_service.services.embedding.embedding_service.EmbeddingService') as MockEmbedding, \
             patch.object(self.retrieval_service.vector_store, 'initialize',
                         new_callable=AsyncMock) as mock_init, \
             patch.object(self.retrieval_service.vector_store, 'search',
                         new_callable=AsyncMock) as mock_search, \
             patch.object(self.retrieval_service.document_store, 'update_chunk_statistics',
                         new_callable=AsyncMock) as mock_update_stats:
            
            # Setup mocks
            mock_embedding_service = MockEmbedding.return_value
            mock_embedding_service.generate_embeddings = AsyncMock(
                return_value=mock_embedding_result
            )
            mock_init.return_value = True
            mock_search.return_value = mock_search_results
            mock_update_stats.return_value = True
            
            # Perform retrieval
            results = await self.retrieval_service.retrieve(
                query=query,
                knowledge_base_id=self.knowledge_base_id,
                top_k=5
            )
            
            # Assertions
            assert len(results) == 2
            assert results[0]['chunk_id'] == 'chunk-1'
            assert results[0]['score'] == 0.95
            assert mock_search.called
    
    @pytest.mark.asyncio
    async def test_retrieve_with_reranking(self):
        """Test retrieval with reranking"""
        query = "What are the safety requirements?"
        
        # Mock embedding and search results
        mock_embedding_result = {
            'success': True,
            'embeddings': [[0.1] * 1536]
        }
        
        mock_search_results = [
            SearchResult(
                chunk_id=f'chunk-{i}',
                score=0.9 - (i * 0.05),
                metadata={'document_id': 'doc-1'},
                content=f'Content {i}'
            )
            for i in range(10)
        ]
        
        with patch('rag_service.services.embedding.embedding_service.EmbeddingService') as MockEmbedding, \
             patch.object(self.retrieval_service.vector_store, 'initialize',
                         new_callable=AsyncMock) as mock_init, \
             patch.object(self.retrieval_service.vector_store, 'search',
                         new_callable=AsyncMock) as mock_search, \
             patch('rag_service.services.storage_retrieval.reranker.Reranker') as MockReranker, \
             patch.object(self.retrieval_service.document_store, 'update_chunk_statistics',
                         new_callable=AsyncMock):
            
            # Setup mocks
            mock_embedding_service = MockEmbedding.return_value
            mock_embedding_service.generate_embeddings = AsyncMock(
                return_value=mock_embedding_result
            )
            mock_init.return_value = True
            mock_search.return_value = mock_search_results
            
            # Mock reranker
            mock_reranker = MockReranker.return_value
            mock_reranker.rerank = AsyncMock(
                return_value=[
                    {
                        'chunk_id': r.chunk_id,
                        'content': r.content,
                        'score': r.score * 1.1,  # Boosted scores
                        'metadata': r.metadata,
                        'document_id': r.metadata.get('document_id')
                    }
                    for r in mock_search_results[:5]
                ]
            )
            
            # Perform retrieval with reranking
            results = await self.retrieval_service.retrieve(
                query=query,
                knowledge_base_id=self.knowledge_base_id,
                top_k=5,
                use_reranking=True,
                rerank_top_k=20
            )
            
            # Assertions
            assert len(results) == 5
            assert mock_reranker.rerank.called
    
    @pytest.mark.asyncio
    async def test_get_chunk_context(self):
        """Test getting chunk with context"""
        chunk_id = 'chunk-5'
        
        # Mock chunk data
        mock_chunk = {
            'id': chunk_id,
            'document_id': 'doc-1',
            'chunk_index': 5,
            'content': 'Target chunk content',
            'metadata': {}
        }
        
        mock_all_chunks = [
            {
                'id': f'chunk-{i}',
                'chunk_index': i,
                'content': f'Chunk {i} content',
                'metadata': {}
            }
            for i in range(10)
        ]
        
        with patch.object(self.retrieval_service.document_store, 'get_chunk_by_id',
                         new_callable=AsyncMock) as mock_get_chunk, \
             patch.object(self.retrieval_service.document_store, 'get_chunks',
                         new_callable=AsyncMock) as mock_get_chunks:
            
            mock_get_chunk.return_value = mock_chunk
            mock_get_chunks.return_value = mock_all_chunks
            
            result = await self.retrieval_service.get_chunk_context(
                chunk_id=chunk_id,
                context_window=2
            )
            
            # Assertions
            assert result['chunk']['id'] == chunk_id
            assert len(result['context_before']) == 2
            assert len(result['context_after']) == 2
            assert len(result['full_context']) == 5
