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
                'layout_blocks': layout_blocks,
                'tables': tables,
                'entities': [],  # No entity extraction in rule-based approach
                'summary': '',   # No summary in rule-based approach
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
            await self._store_document(
                document_id=document_id,
                knowledge_base_id=knowledge_base_id,
                title=title,
                description=description,
                created_by_id=created_by_id,
                extraction_response=extraction_response,
                file_metadata=file_metadata
            )
            
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
                'layout_blocks': [],
                'tables': [],
                'entities': [],
                'summary': '',
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
                await self._store_document(
                    document_id=document_id,
                    knowledge_base_id=knowledge_base_id,
                    title=title,
                    description=description,
                    created_by_id=created_by_id,
                    extraction_response=error_response,
                    file_metadata=file_metadata
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
        """Extract text using rule-based extraction"""
        try:
            # Use PyMuPDF directly for rule-based extraction
            import fitz  # PyMuPDF
            text = ""
            metadata = {}
            
            try:
                doc = fitz.open(file_path)
                for page_num, page in enumerate(doc):
                    page_text = page.get_text()
                    text += page_text + "\n\n"
                
                metadata = {
                    "page_count": len(doc),
                    "file_info": doc.metadata,
                    "extraction_method": "rule_based_pymupdf"
                }
                doc.close()
            except Exception as inner_e:
                logger.warning(f"PyMuPDF extraction failed: {inner_e}, trying fallback methods")
                # Try to use other libraries as fallback
                if file_path.lower().endswith('.pdf'):
                    try:
                        from pypdf import PdfReader
                        reader = PdfReader(file_path)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() + "\n\n"
                        metadata = {
                            "page_count": len(reader.pages),
                            "extraction_method": "rule_based_pypdf"
                        }
                    except Exception as pdf_e:
                        logger.warning(f"PyPDF extraction failed: {pdf_e}")
                        raise
            
            return {
                'text': text,
                'metadata': metadata,
                'warnings': []
            }
        except Exception as e:
            logger.error(f"Text extraction failed: {e}", exc_info=True)
            return {
                'text': '',
                'metadata': {},
                'warnings': [f"Text extraction failed: {str(e)}"]
            }
    
    async def _analyze_layout(self, file_path: str) -> List[Dict[str, Any]]:
        """Analyze document layout"""
        try:
            # Use layout analyzer with non-LLM approach
            # This is a simplified version that doesn't use LLM
            layout_blocks = []
            
            # For PDF files, use PyMuPDF to analyze layout
            if file_path.lower().endswith('.pdf'):
                import fitz  # PyMuPDF
                doc = fitz.open(file_path)
                
                for page_num, page in enumerate(doc):
                    # Extract blocks using PyMuPDF's built-in layout analysis
                    blocks = page.get_text("dict")["blocks"]
                    
                    for i, block in enumerate(blocks):
                        if "lines" in block:  # Text block
                            text = ""
                            for line in block["lines"]:
                                for span in line["spans"]:
                                    text += span["text"] + " "
                            
                            # Create a layout block
                            layout_blocks.append({
                                "type": "paragraph",  # Simple classification
                                "text": text.strip(),
                                "bbox": block["bbox"],
                                "page": page_num,
                                "reading_order": i,
                                "confidence": 1.0,  # High confidence for rule-based
                                "metadata": {}
                            })
            
            return layout_blocks
        except Exception as e:
            logger.error(f"Layout analysis failed: {e}", exc_info=True)
            return []
    
    async def _extract_tables(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract tables using rule-based methods"""
        try:
            # Use TableExtractor with non-LLM methods
            # Only use CAMELOT and PDFPLUMBER methods
            tables = []
            
            if file_path.lower().endswith('.pdf'):
                # Extract tables using camelot (rule-based)
                try:
                    import camelot
                    table_list = camelot.read_pdf(file_path, pages='all', flavor='lattice')
                    
                    for i, table in enumerate(table_list):
                        df = table.df
                        tables.append({
                            "page": table.page,
                            "table_number": i + 1,
                            "bbox": table._bbox,
                            "data": df.to_dict('records'),
                            "headers": df.columns.tolist() if not df.empty else [],
                            "extraction_method": "camelot"
                        })
                except Exception as camelot_error:
                    logger.warning(f"Camelot table extraction failed: {camelot_error}")
                    
                    # Fallback to pdfplumber
                    try:
                        import pdfplumber
                        with pdfplumber.open(file_path) as pdf:
                            for page_num, page in enumerate(pdf.pages):
                                for i, table in enumerate(page.extract_tables()):
                                    if table:
                                        # Convert to pandas DataFrame
                                        import pandas as pd
                                        df = pd.DataFrame(table[1:], columns=table[0] if table else [])
                                        
                                        tables.append({
                                            "page": page_num + 1,
                                            "table_number": i + 1,
                                            "bbox": page.bbox,
                                            "data": df.to_dict('records'),
                                            "headers": df.columns.tolist() if not df.empty else [],
                                            "extraction_method": "pdfplumber"
                                        })
                    except Exception as plumber_error:
                        logger.warning(f"PDFPlumber table extraction failed: {plumber_error}")
            
            return tables
        except Exception as e:
            logger.error(f"Table extraction failed: {e}", exc_info=True)
            return []
    
    async def _store_document(
        self,
        document_id: str,
        knowledge_base_id: str,
        title: str,
        description: str,
        created_by_id: Optional[str],
        extraction_response: Dict[str, Any],
        file_metadata: Dict[str, Any]
    ) -> bool:
        """Store document in PostgreSQL"""
        from rag_service.models import Document, KnowledgeBase
        
        @sync_to_async
        def create_document():
            with transaction.atomic():
                # Get knowledge base
                try:
                    knowledge_base = KnowledgeBase.objects.get(id=knowledge_base_id)
                except KnowledgeBase.DoesNotExist:
                    raise ValueError(f"Knowledge base {knowledge_base_id} does not exist")
                
                # Create document
                document, created = Document.objects.update_or_create(
                    id=document_id,
                    defaults={
                        'knowledge_base': knowledge_base,
                        'title': title,
                        'description': description or '',  # Use empty string if description is None
                        'created_by_id': created_by_id,
                        'document_type': file_metadata.get('file_type', 'pdf'),
                        'content': extraction_response.get('text', ''),
                        'metadata': file_metadata,
                        'extraction_metadata': {
                            'layout_blocks': extraction_response.get('layout_blocks', []),
                            'tables': extraction_response.get('tables', []),
                            'warnings': extraction_response.get('warnings', [])
                        },
                        'extraction_method': 'rule_based',
                        'status': 'completed' if extraction_response.get('success', True) else 'failed',
                        'processing_error': extraction_response.get('error', '') or '',  # Use empty string if None
                        'processed_at': timezone.now(),
                        'storage_approach': 'complete'  # Direct storage without chunking
                    }
                )
                
                # Update knowledge base statistics
                knowledge_base.update_statistics()
                
                return document, created
        
        try:
            document, created = await create_document()
            action = "Created" if created else "Updated"
            logger.info(f"{action} document {document_id} in knowledge base {knowledge_base_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to store document: {e}", exc_info=True)
            return False


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
