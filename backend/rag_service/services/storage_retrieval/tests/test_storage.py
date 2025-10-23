# storage_retrieval/tests/test_storage.py
"""
Tests for Storage Service
"""

import pytest
from django.test import TestCase
from unittest.mock import Mock, patch, AsyncMock
import uuid

from rag_service.services.storage_retrieval import StorageService, DocumentStore


class TestDocumentStore(TestCase):
    """Test DocumentStore functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.document_store = DocumentStore()
        self.document_id = str(uuid.uuid4())
    
    @pytest.mark.asyncio
    async def test_store_extraction(self):
        """Test storing extraction response"""
        extraction_response = {
            'text': 'Sample document text',
            'tables': [],
            'layout_blocks': [],
            'entities': [],
            'summary': 'Document summary',
            'metadata': {},
            'cost_usd': 0.01,
            'processing_time_ms': 1000,
            'model_used': 'gpt-4-vision',
            'provider_used': 'openai',
            'success': True,
            'warnings': []
        }
        
        file_metadata = {
            'name': 'test.pdf',
            'size': 1024000,
            'type': 'pdf'
        }
        
        # Mock the document model
        with patch('rag_service.models.Document') as MockDocument:
            MockDocument.objects.update_or_create = AsyncMock(
                return_value=(Mock(), True)
            )
            
            result = await self.document_store.store_extraction(
                document_id=self.document_id,
                extraction_response=extraction_response,
                file_metadata=file_metadata
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_store_chunks(self):
        """Test storing document chunks"""
        chunks = [
            {
                'chunk_index': 0,
                'content': 'First chunk content',
                'chunk_type': 'text',
                'metadata': {'page': 1},
                'token_count': 50
            },
            {
                'chunk_index': 1,
                'content': 'Second chunk content',
                'chunk_type': 'text',
                'metadata': {'page': 1},
                'token_count': 45
            }
        ]
        
        with patch('rag_service.models.Document') as MockDocument, \
             patch('rag_service.models.Chunk') as MockChunk:
            
            MockDocument.objects.get = AsyncMock(return_value=Mock())
            MockChunk.objects.filter = Mock(return_value=Mock(delete=Mock()))
            MockChunk.objects.bulk_create = Mock(return_value=[Mock(), Mock()])
            
            result = await self.document_store.store_chunks(
                document_id=self.document_id,
                chunks=chunks
            )
            
            assert result is True


class TestStorageService(TestCase):
    """Test StorageService functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.storage_service = StorageService(vector_store_type='pinecone')
        self.document_id = str(uuid.uuid4())
    
    @pytest.mark.asyncio
    async def test_store_document(self):
        """Test complete document storage"""
        extraction_response = {
            'text': 'Sample document text',
            'tables': [],
            'layout_blocks': [],
            'entities': [],
            'summary': 'Document summary',
            'metadata': {},
            'cost_usd': 0.01,
            'processing_time_ms': 1000,
            'model_used': 'gpt-4-vision',
            'provider_used': 'openai',
            'success': True,
            'warnings': []
        }
        
        file_metadata = {
            'name': 'test.pdf',
            'size': 1024000,
            'type': 'pdf'
        }
        
        chunks = [
            {
                'chunk_index': 0,
                'content': 'First chunk',
                'chunk_type': 'text',
                'metadata': {},
                'token_count': 50
            }
        ]
        
        # Mock dependencies
        with patch.object(self.storage_service.document_store, 'store_extraction', 
                         new_callable=AsyncMock) as mock_store_extraction, \
             patch.object(self.storage_service.document_store, 'store_chunks',
                         new_callable=AsyncMock) as mock_store_chunks:
            
            mock_store_extraction.return_value = True
            mock_store_chunks.return_value = True
            
            result = await self.storage_service.store_document(
                document_id=self.document_id,
                extraction_response=extraction_response,
                file_metadata=file_metadata,
                chunks=chunks,
                store_vectors=False  # Skip vector storage for test
            )
            
            assert result['success'] is True
            assert result['chunks_stored'] == 1
            assert mock_store_extraction.called
            assert mock_store_chunks.called
    
    @pytest.mark.asyncio
    async def test_delete_document(self):
        """Test document deletion"""
        with patch.object(self.storage_service.document_store, 'delete_document',
                         new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True
            
            result = await self.storage_service.delete_document(
                document_id=self.document_id
            )
            
            assert result['success'] is True
            assert mock_delete.called
