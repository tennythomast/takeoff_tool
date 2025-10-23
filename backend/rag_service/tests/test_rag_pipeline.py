import os
import json
from pathlib import Path
from django.test import TestCase
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from model_bakery import baker
from asgiref.sync import sync_to_async

from rag_service.models import KnowledgeBase, Document, Chunk
from rag_service.services.storage_retrieval import StorageService
from rag_service.services.storage_retrieval.document_store import DocumentStore
from rag_service.services.extraction.text import TextExtractor
from rag_service.services.extraction.table_extractor import TableExtractor
from rag_service.services.extraction.layout_analyzer import LayoutAnalyzer


class TestRAGPipeline(TestCase):
    """Test the complete RAG pipeline from document upload to retrieval"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data for all test methods"""
        # Create a test organization
        cls.organization = baker.make('core.Organization')
        
        # Create a user with email (required field)
        cls.user = baker.make('core.User', email='test@example.com')
        
        # Get the membership that was automatically created
        from core.models import Membership
        cls.membership = Membership.objects.get(user=cls.user)
        
        # Update the membership to link to our organization
        cls.membership.organization = cls.organization
        cls.membership.role = 'OWNER'
        cls.membership.save()
        
        cls.knowledge_base = KnowledgeBase.objects.create(
            name="Test Knowledge Base",
            organization=cls.organization,
            created_by=cls.user,
            embedding_strategy='semantic',
            retrieval_strategy='similarity',
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # Initialize services
        cls.storage_service = StorageService()
        cls.text_extractor = TextExtractor()
        cls.table_extractor = TableExtractor()
        cls.layout_analyzer = LayoutAnalyzer()
        
        # Path to test file
        cls.test_file_path = os.path.join(
            os.path.dirname(__file__), 
            'test_file1.pdf'
        )
    
    async def test_document_extraction_and_chunking(self):
        """Test document extraction and chunking with all components"""
        # 1. Create document in database
        document = await sync_to_async(Document.objects.create)(
            knowledge_base=self.knowledge_base,
            title="Test Document",
            document_type='pdf',
            file_upload=None,  # In a real test, you'd create a FileUpload instance
            status='pending',
            created_by=self.user
        )
        
        # 2. Process the document (extract and chunk)
        try:
            # Mark document as processing
            document.status = 'processing'
            await sync_to_async(document.save)()
            
            # Step 1: Use the text extractor to extract text
            print("\n1. Extracting text from PDF...")
            text_result = self.text_extractor.extract(self.test_file_path)
            print(f"Text extraction result: {len(text_result['text'])} characters")
            
            # Step 2: Use the table extractor to extract tables
            print("\n2. Extracting tables from PDF...")
            tables = []
            try:
                tables = await self.table_extractor.extract_tables(self.test_file_path)
                print(f"Found {len(tables)} tables")
                for i, table in enumerate(tables):
                    if hasattr(table, 'shape'):
                        print(f"Table {i+1}: {table.shape[0]} rows x {table.shape[1]} columns")
                    else:
                        print(f"Table {i+1}: format unknown")
            except Exception as e:
                print(f"Table extraction error: {e}")
            
            # Step 3: Use the layout analyzer to analyze layout
            print("\n3. Analyzing document layout...")
            layout_blocks = []
            try:
                layout_blocks = await self.layout_analyzer.analyze_layout(self.test_file_path)
                print(f"Found {len(layout_blocks)} layout blocks")
                for i, block in enumerate(layout_blocks[:3]):
                    print(f"Block {i+1}: {block.block_type} - {block.text[:50]}...")
            except Exception as e:
                print(f"Layout analysis error: {e}")
            
            # Step 4: Use the document processor if available
            # (Removed ImageProcessor usage)
            
            # Step 6: Use the chunking service to create chunks
            print("\n6. Chunking document content...")
            from rag_service.services.chunking.chunking_service import ChunkingService
            chunking_service = ChunkingService()
            
            # Create extraction response format expected by chunking service
            extraction_response = {
                'text': text_result['text'],
                'tables': [{
                    'headers': table.columns.tolist(),
                    'rows': table.values.tolist()
                } for table in tables],
                'layout_blocks': [{
                    'type': block.block_type.value if hasattr(block, 'block_type') else 'text',
                    'text': block.text if hasattr(block, 'text') else '',
                    'position': block.position if hasattr(block, 'position') else {}
                } for block in layout_blocks],
                'metadata': {}
            }
            
            # Use the chunking service to create chunks
            chunks = chunking_service.chunk_document(extraction_response, document)
            
            # Verify chunks were created
            self.assertGreater(len(chunks), 0, "No chunks were created")
            
            # Print chunk information for debugging
            print(f"\nCreated {len(chunks)} chunks from document")
            for i, chunk in enumerate(chunks[:3]):  # Show first 3 chunks
                print(f"\nChunk {i+1}:")
                print(f"Content: {chunk.content[:100]}...")
                print(f"Type: {chunk.chunk_type}")
                print(f"Index: {chunk.chunk_index}")
            
            # Mark document as completed
            document.status = 'completed'
            await sync_to_async(document.save)()
            
            # Verify document status
            self.assertEqual(document.status, 'completed')
            
        except Exception as e:
            document.status = 'failed'
            document.error_message = str(e)
            await sync_to_async(document.save)()
            raise
