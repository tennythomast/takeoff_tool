"""
Document Processing Pipeline

This module provides an end-to-end document processing pipeline that:
1. Extracts text using rule-based extraction (no LLM)
2. Analyzes document layout
3. Extracts tables
4. Stores results directly in PostgreSQL

This pipeline skips chunking and embedding to provide a simpler,
direct storage approach for engineering drawings and documents.
"""

import os
import uuid
import logging
import asyncio
from typing import Dict, Any, Optional, BinaryIO, List, Union
from pathlib import Path
from datetime import datetime

from django.utils import timezone
from django.db import transaction
from asgiref.sync import sync_to_async

from .extraction.text import TextExtractor, TextExtractorConfig, detect_file_type
from .extraction.layout_analyzer import LayoutAnalyzer
from .extraction.table_extractor import TableExtractor, TableExtractionMethod
from .storage_retrieval.document_store import DocumentStore

logger = logging.getLogger(__name__)


class DocumentPipeline:
    """
    End-to-end document processing pipeline using rule-based extraction.
    
    Features:
    - Rule-based text extraction (no LLM)
    - Layout analysis for document structure
    - Table extraction using non-LLM methods
    - Direct PostgreSQL storage
    - No chunking or embedding
    """
    
    def __init__(self):
        """Initialize the document pipeline with required services"""
        self.text_extractor = TextExtractor(
            config=TextExtractorConfig(
                preserve_formatting=True,
                extract_tables=True,
                detect_sections=True
            )
        )
        self.layout_analyzer = LayoutAnalyzer()
        self.table_extractor = TableExtractor()
        self.document_store = DocumentStore()
    
    async def process_document(
        self,
        file_path: str,
        knowledge_base_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        document_id: Optional[str] = None,
        created_by_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a document end-to-end using rule-based extraction.
        
        Args:
            file_path: Path to the document file
            knowledge_base_id: ID of the knowledge base to store the document in
            title: Document title (optional, will use filename if not provided)
            description: Document description (optional)
            document_id: Document ID (optional, will generate if not provided)
            created_by_id: ID of the user who created the document (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            Dictionary with processing results
        """
        start_time = datetime.now()
        document_id = document_id or str(uuid.uuid4())
        
        # Prepare file metadata
        file_info = Path(file_path)
        file_name = file_info.name
        file_size = file_info.stat().st_size
        file_type = detect_file_type(file_path)
        
        if not title:
            title = file_name
            
        # Prepare document metadata
        file_metadata = {
            'file_name': file_name,
            'file_size': file_size,
            'file_type': file_type,
            'original_path': str(file_path)
        }
        
        # Add additional metadata if provided
        if metadata:
            file_metadata.update(metadata)
        
        try:
            # 1. Extract text using rule-based extraction
            logger.info(f"Extracting text from {file_path}")
            extraction_result = await self._extract_text(file_path)
            
            # 2. Analyze document layout
            logger.info(f"Analyzing document layout")
            layout_blocks = await self._analyze_layout(file_path)
            
            # 3. Extract tables
            logger.info(f"Extracting tables")
            tables = await self._extract_tables(file_path)
            
            # 4. Prepare extraction response
            extraction_response = {
                'text': extraction_result.get('text', ''),
                'pages': extraction_result.get('pages', []),  # Include page-by-page text
                'extraction_method': 'rule_based',
                'model_used': 'rule_based',
                'provider_used': 'local',
                'cost_usd': 0.0,  # No cost for rule-based extraction
                'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                'success': True,
                'error': None,
                'warnings': extraction_result.get('warnings', [])
            }
            
            # 5. Store in PostgreSQL
            logger.info(f"Storing document {document_id} in database")
            try:
                # Enhance file metadata with document information
                enhanced_metadata = {
                    **file_metadata,
                    'title': title,
                    'description': description or '',
                    'knowledge_base_id': knowledge_base_id,
                    'created_by_id': created_by_id
                }
                
                # Store directly using document_store for error cases
                await self.document_store.store_extraction(
                    document_id=document_id,
                    extraction_response=extraction_response,
                    file_metadata=enhanced_metadata,
                    knowledge_base_id=knowledge_base_id
                )
            except Exception as store_error:
                logger.error(f"Failed to store error information: {store_error}", exc_info=True)
            
            logger.info(f"Document processing completed for {file_path}")
            return {
                'document_id': document_id,
                'knowledge_base_id': knowledge_base_id,
                'title': title,
                'status': 'completed',
                'processing_time_ms': extraction_response['processing_time_ms'],
                'text_length': len(extraction_response['text']),
                'tables_count': len(tables),
                'layout_blocks_count': len(layout_blocks)
            }
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}", exc_info=True)
            
            # Store error information
            error_response = {
                'text': '',
                'pages': [],  # Empty pages list
                'extraction_method': 'rule_based',
                'model_used': 'rule_based',
                'provider_used': 'local',
                'cost_usd': 0.0,
                'processing_time_ms': (datetime.now() - start_time).total_seconds() * 1000,
                'success': False,
                'error': str(e),
                'warnings': []
            }
            
            try:
                # Enhance file metadata with document information
                enhanced_metadata = {
                    **file_metadata,
                    'title': title,
                    'description': description or '',
                    'knowledge_base_id': knowledge_base_id,
                    'created_by_id': created_by_id
                }
                
                # Store directly using document_store for error cases
                await self.document_store.store_extraction(
                    document_id=document_id,
                    extraction_response=error_response,
                    file_metadata=enhanced_metadata,
                    knowledge_base_id=knowledge_base_id
                )
            except Exception as store_error:
                logger.error(f"Failed to store error information: {store_error}", exc_info=True)
                
            return {
                'document_id': document_id,
                'knowledge_base_id': knowledge_base_id,
                'title': title,
                'status': 'failed',
                'error': str(e),
                'processing_time_ms': error_response['processing_time_ms']
            }
    
    async def _extract_text(self, file_path: str) -> Dict[str, Any]:
        """Extract text using the TextExtractor service"""
        try:
            # Use the existing TextExtractor service
            extraction_result = self.text_extractor.extract(file_path)
            
            # Log the extraction result
            logger.info(f"Text extraction result keys: {extraction_result.keys()}")
            logger.info(f"Pages in extraction result: {len(extraction_result.get('pages', []))}")
            if 'pages' in extraction_result:
                logger.info(f"First page keys: {extraction_result['pages'][0].keys() if extraction_result['pages'] else 'No pages'}")
            
            # Return the extraction result with a consistent structure
            return {
                'text': extraction_result.get('text', ''),
                'metadata': extraction_result.get('metadata', {}),
                'pages': extraction_result.get('pages', []),  # This contains per-page data
                'warnings': extraction_result.get('problematic_pages', [])
            }
        except Exception as e:
            logger.error(f"Text extraction failed: {e}", exc_info=True)
            return {
                'text': '',
                'metadata': {},
                'pages': [],
                'warnings': [f"Text extraction failed: {str(e)}"]
            }
    
    async def _analyze_layout(self, file_path: str) -> Dict[str, Any]:
        """Analyze document layout using the LayoutAnalyzer service"""
        try:
            # Use the existing LayoutAnalyzer service which now returns organized data
            layout_result = await self.layout_analyzer.analyze_layout(
                file_path=file_path,
                method='rule_based'
            )
            
            # Return the result directly since it's already organized
            return layout_result
        except Exception as e:
            logger.error(f"Layout analysis failed: {e}", exc_info=True)
            return {
                'layout_blocks': [],
                'layout_by_page': {}
            }
    
    async def _extract_tables(self, file_path: str) -> Dict[str, Any]:
        """Extract tables using the TableExtractor service"""
        try:
            # Use the existing TableExtractor service which now returns organized data
            tables_result = await self.table_extractor.extract_tables(
                file_path=file_path
            )
            
            # Return the result directly since it's already organized
            return tables_result
        except Exception as e:
            logger.error(f"Table extraction failed: {e}", exc_info=True)
            return {
                'tables': [],
                'tables_by_page': {}
            }
    
    async def process_document_with_pages(
        self,
        file_path: str,
        knowledge_base_id: str,
        title: str = None,
        description: str = None,
        created_by_id: str = None,
        use_rule_based: bool = False
    ) -> Dict[str, Any]:
        """Process a document using existing extraction services with page-level data"""
        start_time = time.time()
        document_id = str(uuid.uuid4())
        
        try:
            # Extract file metadata
            file_info = Path(file_path)
            file_metadata = {
                'file_name': file_info.name,
                'file_size': file_info.stat().st_size if file_info.exists() else 0,
                'file_type': file_info.suffix.lower().lstrip('.'),
                'original_path': str(file_path)
            }
            
            # Set default title if not provided
            if not title:
                title = os.path.basename(file_path)
                
            # Extract text using TextExtractor
            text_response = await self._extract_text(file_path)
            
            # Analyze layout using LayoutAnalyzer
            layout_blocks = await self._analyze_layout(file_path)
            
            # Extract tables using TableExtractor
            tables = await self._extract_tables(file_path)
            
            # Store document directly using document_store
            # Enhance file metadata with document information
            enhanced_metadata = {
                **file_metadata,
                'title': title,
                'description': description or '',
                'knowledge_base_id': knowledge_base_id,
                'created_by_id': created_by_id
            }
            
            # Prepare the extraction response
            complete_extraction = {
                'text': text_response.get('text', ''),
                'pages': text_response.get('pages', []),
                'layout_blocks': layout_blocks,
                'tables': tables,
                'warnings': text_response.get('warnings', []),
                'success': True,
                'extraction_method': 'rule_based',
                'model_used': 'rule_based',
                'provider_used': 'local',
                'cost_usd': 0.0,  # No cost for rule-based extraction
                'processing_time_ms': (time.time() - start_time) * 1000
            }
            
            # Store using document_store
            await self.document_store.store_extraction(
                document_id=document_id,
                extraction_response=complete_extraction,
                file_metadata=enhanced_metadata,
                knowledge_base_id=knowledge_base_id
            )
            
            # Calculate processing time
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Return success response
            return {
                'status': 'success',
                'document_id': document_id,
                'text': text_response.get('text', ''),
                'pages': text_response.get('pages', []),
                'layout_blocks': layout_blocks,
                'tables': tables,
                'processing_time_ms': processing_time_ms
            }
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {e}", exc_info=True)
            return {
                'status': 'failed',
                'document_id': document_id,
                'error': str(e),
                'processing_time_ms': (time.time() - start_time) * 1000
            }

    # Storage is now handled directly by calling document_store.store_extraction


# Command-line interface for testing
if __name__ == "__main__":
    import django
    import sys
    
    # Set up Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'takeoff_tool.settings')
    django.setup()
    
    # Parse arguments
    if len(sys.argv) < 3:
        print("Usage: python document_pipeline.py <file_path> <knowledge_base_id>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    knowledge_base_id = sys.argv[2]
    
    # Process document
    async def main():
        pipeline = DocumentPipeline()
        result = await pipeline.process_document(
            file_path=file_path,
            knowledge_base_id=knowledge_base_id
        )
        print(f"Document processing result: {result}")
    
    asyncio.run(main())
