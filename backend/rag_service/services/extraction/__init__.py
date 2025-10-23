"""
Text extraction services for RAG pipeline.

This package provides functionality to extract text from various document formats
for use in retrieval-augmented generation (RAG) pipelines.

Supported extraction methods:
- Text extraction (PDF, DOCX, TXT, MD, CSV)
- Vision-based extraction (images, scanned documents)
- Layout analysis (document structure recognition)
- Table extraction (structured tables from PDFs)
- Unified extraction (combines multiple tasks in a single LLM call)
- Hybrid extraction (intelligent combination of methods)
"""

from .text import TextExtractor, TextExtractorConfig, detect_file_type, is_scanned_pdf
from .document_processor import DocumentProcessor, create_document_processor
from .base import BaseExtractor, ExtractionResult
from .image_processor import ImageProcessor
from .vision import VisionExtractor, VisionConfig
from .layout_analyzer import LayoutAnalyzer, LayoutBlock, BlockType
from .table_extractor import TableExtractor, TableExtractionMethod
from .multi_task_prompts import ExtractionTask, MultiTaskPrompts, SpecializedPrompts
from .unified_extractor import UnifiedExtractor, ExtractionRequest, ExtractionResponse

__all__ = [
    # Text extraction
    'TextExtractor', 
    'TextExtractorConfig', 
    'detect_file_type', 
    'is_scanned_pdf',
    'DocumentProcessor',
    'create_document_processor',
    
    # Base classes
    'BaseExtractor',
    'ExtractionResult',
    
    # Vision extraction
    'ImageProcessor',
    'VisionExtractor',
    'VisionConfig',
    
    # Layout analysis
    'LayoutAnalyzer',
    'LayoutBlock',
    'BlockType',
    
    # Table extraction
    'TableExtractor',
    'TableExtractionMethod',
    
    # Prompts
    'MultiTaskPrompts',
    'SpecializedPrompts',
    'ExtractionTask',
    
    # Unified extraction
    'UnifiedExtractor',
    'ExtractionRequest',
    'ExtractionResponse'
]
