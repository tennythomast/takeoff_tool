"""
Tests for the LLM extraction service using real document data

These tests verify that the LLM extraction service correctly:
1. Processes existing document data from the RAG service
2. Generates appropriate extraction prompts
3. Creates accurate extraction records
"""

import json
import os
import uuid
import unittest
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from django.test import TestCase
from django.utils import timezone
from django.conf import settings

from rag_service.models import Document, DocumentPage, KnowledgeBase
from takeoff.models import Drawing, TakeoffExtraction, TakeoffElement
from takeoff.services.extractors.llm_extraction import LLMExtractionService
from takeoff.services.validation.schema_validator import SchemaValidator
from core.models import Organization


class TestLLMExtractionWithRealData(TestCase):
    """Test the LLM extraction service using real document data"""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data once for all tests"""
        # Try to find existing document with title 'test_file2.pdf'
        try:
            # Look for the document in the database
            cls.document = Document.objects.get(title='test_file2.pdf')
            print(f"Found existing document: {cls.document.title} (ID: {cls.document.id})")
            
            # Get the document pages
            cls.document_pages = DocumentPage.objects.filter(document=cls.document)
            cls.page_count = cls.document_pages.count()
            print(f"Document has {cls.page_count} pages")
            
            # Get the knowledge base
            cls.knowledge_base = cls.document.knowledge_base
            print(f"Using knowledge base: {cls.knowledge_base.name} (ID: {cls.knowledge_base.id})")
            
            # Get the organization
            cls.organization = cls.knowledge_base.organization
            print(f"Using organization: {cls.organization.name} (ID: {cls.organization.id})")
            
            # Check if there's already a drawing linked to this document
            existing_drawing = Drawing.objects.filter(rag_document=cls.document).first()
            if existing_drawing:
                cls.drawing = existing_drawing
                print(f"Using existing drawing: {cls.drawing.drawing_title} (ID: {cls.drawing.id})")
            else:
                # Create a new drawing linked to the document
                cls.drawing = Drawing.objects.create(
                    organization_id=cls.organization.id,
                    client="Test Client",
                    project="Test Project",
                    location="Test Location",
                    drawing_number="TEST-001",
                    drawing_title="test_file2.pdf",
                    date=timezone.now().date(),
                    page_count=cls.page_count,
                    rag_document=cls.document
                )
                print(f"Created new drawing with ID: {cls.drawing.id}")
            
            # Print some information about the document content
            if cls.document_pages.exists():
                first_page = cls.document_pages.first()
                print(f"First page content preview: {first_page.page_text[:100]}...")
                
        except Document.DoesNotExist:
            print("Document 'test_file2.pdf' not found. Creating test data instead.")
            
            # Create an organization for testing
            cls.organization = Organization.objects.create(
                name="Test Organization",
                slug="test-org"
            )
            print(f"Created test organization: {cls.organization.name} (ID: {cls.organization.id})")
            
            # Create a knowledge base for testing
            cls.knowledge_base = KnowledgeBase.objects.create(
                name="Test Knowledge Base",
                description="Test knowledge base for unit tests",
                is_public=True,
                organization=cls.organization
            )
            print(f"Created knowledge base: {cls.knowledge_base.name} (ID: {cls.knowledge_base.id})")
            
            # Create a test document
            cls.document = Document.objects.create(
                title="test_file2.pdf",
                content="Test document content",
                status="completed",
                document_type="pdf",
                storage_approach="file_system",
                knowledge_base=cls.knowledge_base
            )
            print(f"Created test document: {cls.document.title} (ID: {cls.document.id})")
            
            # Create document pages
            cls.page_texts = [
                "Page 1: Test content with some structural information",
                "Page 2: FOOTING SCHEDULE\nF-01: 1200x1500x600, N16@200 B.W, N32",
                "Page 3: COLUMN SCHEDULE\nC-01: 300x300x3000, 8N24, N40"
            ]
            
            for i, text in enumerate(cls.page_texts):
                DocumentPage.objects.create(
                    document=cls.document,
                    page_number=i + 1,
                    page_text=text
                )
            
            cls.document_pages = DocumentPage.objects.filter(document=cls.document)
            cls.page_count = cls.document_pages.count()
            print(f"Created {cls.page_count} document pages")
            
            # Create a drawing linked to the document
            cls.drawing = Drawing.objects.create(
                organization_id=cls.organization.id,
                client="Test Client",
                project="Test Project",
                location="Test Location",
                drawing_number="TEST-001",
                drawing_title="test_file2.pdf",
                date=timezone.now().date(),
                page_count=cls.page_count,
                rag_document=cls.document
            )
            print(f"Created drawing with ID: {cls.drawing.id}")
    
    def setUp(self):
        """Set up for each test"""
        self.service = LLMExtractionService()
    
    @patch('takeoff.services.extractors.llm_extraction.LLMExtractionService._call_llm')
    async def test_extraction_with_real_document(self, mock_call_llm):
        """Test extraction using real document data from the database"""
        # Check if we have existing extractions for this document
        existing_extractions = await self._get_existing_extractions(self.drawing)
        
        if existing_extractions:
            # Use data from an existing extraction
            latest_extraction = existing_extractions[0]  # Most recent extraction
            print(f"Using data from existing extraction ID: {latest_extraction.id}")
            
            # Get the elements from the existing extraction
            elements = await self._get_elements(latest_extraction)
            if elements:
                # Use the actual elements from the database for our mock response
                mock_elements = []
                for element in elements:
                    # Convert each element to a dictionary for the mock response
                    mock_element = {
                        "element_id": element.element_id,
                        "element_type": element.element_type,
                        "page_number": 1,  # Default page number
                        "confidence_score": element.confidence_score or 0.9,
                        "specifications": element.specifications,
                        "extraction_notes": {
                            "source_references": [f"From existing extraction {latest_extraction.id}"]
                        }
                    }
                    mock_elements.append(mock_element)
                
                print(f"Using {len(mock_elements)} elements from existing extraction")
                mock_llm_response = {
                    'text': json.dumps(mock_elements),
                    'model_used': 'gpt-4',
                    'provider_used': 'openai',
                    'cost_usd': 0.15,
                    'processing_time_ms': 2500
                }
            else:
                # No elements found, use default mock response
                print("No elements found in existing extraction, using default mock")
                mock_llm_response = self._get_default_mock_response()
        else:
            # No existing extractions, use default mock response
            print("No existing extractions found, using default mock")
            mock_llm_response = self._get_default_mock_response()
            
        mock_call_llm.return_value = mock_llm_response
        
        # Call the extract_elements method
        result = await self.service.extract_elements(
            drawing_id=str(self.drawing.id),
            trade="concrete"
        )
        
        # Verify the result
        self.assertTrue(result["success"])
        self.assertEqual(result["element_count"], 1)
        
        # Verify that the extraction record was created
        extraction = await self._get_extraction(result["extraction_id"])
        self.assertEqual(extraction.status, "completed")
        self.assertEqual(extraction.element_count, 1)
        self.assertEqual(extraction.drawing_id, self.drawing.id)
        
        # Verify that element objects were created
        elements = await self._get_elements(extraction)
        self.assertEqual(len(elements), 1)
        
        # Verify element details
        element = elements[0]
        self.assertEqual(element.element_type, "IsolatedFooting")
        self.assertEqual(element.element_id, "F-01")
        self.assertEqual(element.specifications["dimensions"]["width_mm"], 1200)
    
    @patch('takeoff.services.extractors.llm_extraction.LLMExtractionService._call_llm')
    async def test_extraction_prompt_generation(self, mock_call_llm):
        """Test that the prompt is correctly generated from document pages"""
        # Mock the LLM response
        mock_call_llm.return_value = {
            'text': '[]',  # Empty result for this test
            'model_used': 'gpt-4',
            'provider_used': 'openai',
            'cost_usd': 0.05,
            'processing_time_ms': 1000
        }
        
        # Spy on the _generate_extraction_prompt method
        original_generate_prompt = self.service._generate_extraction_prompt
        prompt_spy = MagicMock(wraps=original_generate_prompt)
        self.service._generate_extraction_prompt = prompt_spy
        
        try:
            # Call the extract_elements method with specific page
            await self.service.extract_elements(
                drawing_id=str(self.drawing.id),
                trade="concrete",
                pages=[2]  # Only extract from page 2 (footing schedule)
            )
            
            # Verify that the prompt was generated correctly
            prompt_spy.assert_called_once()
            
            # Get the arguments passed to the prompt generation method
            args, kwargs = prompt_spy.call_args
            trade, input_text, context = args
            
            # Verify the trade
            self.assertEqual(trade, "concrete")
            
            # Verify that the input text contains the footing schedule
            self.assertIn("FOOTING SCHEDULE", input_text)
            self.assertIn("F-01", input_text)
            
            # Verify that the context contains the correct page numbers
            self.assertEqual(context["pages"], [2])
            
        finally:
            # Restore the original method
            self.service._generate_extraction_prompt = original_generate_prompt
    
    # Helper methods to handle async DB operations
    async def _get_extraction(self, extraction_id):
        """Get extraction by ID"""
        from asgiref.sync import sync_to_async
        get_extraction = sync_to_async(lambda: TakeoffExtraction.objects.get(id=extraction_id))
        return await get_extraction()
    
    async def _get_elements(self, extraction):
        """Get elements for an extraction"""
        from asgiref.sync import sync_to_async
        get_elements = sync_to_async(lambda: list(TakeoffElement.objects.filter(extraction=extraction)))
        return await get_elements()
    
    async def _get_existing_extractions(self, drawing):
        """Get existing extractions for a drawing"""
        from asgiref.sync import sync_to_async
        get_extractions = sync_to_async(lambda: list(TakeoffExtraction.objects.filter(drawing=drawing).order_by('-created_at')))
        return await get_extractions()
    
    def _get_default_mock_response(self):
        """Get a default mock LLM response"""
        return {
            'text': json.dumps([
                {
                    "element_id": "F-01",
                    "element_type": "IsolatedFooting",
                    "page_number": 2,
                    "confidence_score": 0.95,
                    "specifications": {
                        "dimensions": {
                            "width_mm": 1200,
                            "length_mm": 1500,
                            "depth_mm": 600
                        },
                        "reinforcement": {
                            "bottom": {
                                "bar_size": "N16",
                                "spacing_mm": 200,
                                "direction": "both_ways"
                            }
                        },
                        "concrete": {
                            "grade": "N32"
                        }
                    },
                    "extraction_notes": {
                        "source_references": ["Page 2, Footing Schedule"]
                    }
                }
            ]),
            'model_used': 'gpt-4',
            'provider_used': 'openai',
            'cost_usd': 0.15,
            'processing_time_ms': 2500
        }


if __name__ == "__main__":
    # This allows running the tests directly
    import unittest
    unittest.main()
