"""
Document Processor Service

This module provides a document processor service that uses various extractors
to extract text from documents and prepare them for RAG (Retrieval-Augmented Generation).

Supported extraction methods:
- Text-based extraction (PDFs, DOCX, TXT, etc.)
- Vision-based extraction (images, scanned documents)
- Unified extraction (combines multiple extraction tasks in a single LLM call)

This module now uses the UnifiedExtractor to avoid duplicate LLM calls.
"""

import os
import logging
import tempfile
from typing import Dict, List, Any, Optional, BinaryIO, Union, Literal
from pathlib import Path
from enum import Enum

from .text import TextExtractor, TextExtractorConfig, detect_file_type, is_scanned_pdf
from .vision import VisionExtractor, VisionConfig
from .base import BaseExtractor, ExtractionResult
from .unified_extractor import UnifiedExtractor, ExtractionRequest, ExtractionTask, ExtractionResponse

logger = logging.getLogger(__name__)


class ExtractionMethod(str, Enum):
    """Extraction method options"""
    TEXT = 'text'
    VISION = 'vision'
    UNIFIED = 'unified'  # Use the UnifiedExtractor
    AUTO = 'auto'  # Automatically select based on document type


class DocumentProcessor:
    """
    Document processor service that extracts text from documents and prepares them for RAG.
    
    Features:
    - Supports multiple extraction methods (text, vision)
    - Automatically selects the best extraction method based on document type
    - Handles various file formats (PDF, DOCX, images, etc.)
    - Prepares text for RAG pipelines
    """
    
    def __init__(
        self, 
        text_config: Optional[TextExtractorConfig] = None,
        vision_config: Optional[VisionConfig] = None,
        default_method: ExtractionMethod = ExtractionMethod.AUTO
    ):
        """
        Initialize the document processor.
        
        Args:
            text_config: Configuration for the text extractor
            vision_config: Configuration for the vision extractor
            default_method: Default extraction method to use
        """
        self.text_extractor = TextExtractor(text_config or TextExtractorConfig())
        self.vision_extractor = VisionExtractor(vision_config or VisionConfig())
        self.unified_extractor = UnifiedExtractor()
        self.default_method = default_method
    
    def get_extractor(self, file_path: str, method: Optional[ExtractionMethod] = None) -> Union[BaseExtractor, UnifiedExtractor]:
        """
        Get the appropriate extractor for the file.
        
        Args:
            file_path: Path to the file
            method: Extraction method to use (if None, uses default_method)
            
        Returns:
            BaseExtractor or UnifiedExtractor: The appropriate extractor
        """
        method = method or self.default_method
        file_type = detect_file_type(file_path)
        
        # If method is UNIFIED, use the unified extractor
        if method == ExtractionMethod.UNIFIED:
            return self.unified_extractor
        
        # If method is AUTO, determine based on file type and content
        if method == ExtractionMethod.AUTO:
            # For complex documents, use unified extractor
            if file_type == 'pdf' and is_scanned_pdf(file_path):
                # Scanned PDFs benefit from unified extraction
                return self.unified_extractor
                
            # Images benefit from unified extraction
            if file_type in ['jpg', 'jpeg', 'png', 'tiff', 'bmp', 'webp']:
                return self.unified_extractor
                
            # Default to text extractor for simple documents
            return self.text_extractor
            
        # Use specified method
        if method == ExtractionMethod.VISION:
            return self.vision_extractor
        else:
            return self.text_extractor
    
    async def process_file(self, file_path: str, method: Optional[ExtractionMethod] = None, organization=None) -> Dict[str, Any]:
        """
        Process a file and extract its text and metadata.
        
        Args:
            file_path: Path to the file to process
            method: Extraction method to use
            organization: Organization for ModelHub routing (needed for vision/unified)
            
        Returns:
            Dictionary containing extracted text, metadata, and processing info
        """
        logger.info(f"Processing file: {file_path}")
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Get appropriate extractor
        extractor = self.get_extractor(file_path, method)
        logger.info(f"Using extractor: {extractor.__class__.__name__}")
        
        # Extract text
        if isinstance(extractor, UnifiedExtractor):
            # Use the unified extractor (async)
            request = ExtractionRequest(
                file_path=file_path,
                tasks=[ExtractionTask.ALL],
                organization=organization,
                quality_priority='balanced'
            )
            extraction_response = await extractor.extract(request)
            
            # Convert to standard format
            result = {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "file_type": detect_file_type(file_path),
                "file_size": os.path.getsize(file_path),
                "extraction_method": "UnifiedExtractor",
                "text": extraction_response.text,
                "tables": extraction_response.tables,
                "layout_blocks": extraction_response.layout_blocks,
                "entities": extraction_response.entities,
                "summary": extraction_response.summary,
                "metadata": extraction_response.metadata,
                "cost_usd": extraction_response.cost_usd,
                "model_used": extraction_response.model_used,
                "provider_used": extraction_response.provider_used,
                "processing_info": {
                    "success": extraction_response.success,
                    "error": extraction_response.error,
                    "warnings": extraction_response.warnings
                }
            }
        else:
            # Use standard extractors (sync)
            extraction_result = extractor.extract(file_path)
            
            # Add processing metadata
            result = {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "file_type": detect_file_type(file_path),
                "file_size": os.path.getsize(file_path),
                "extraction_method": extractor.__class__.__name__,
                "extraction_result": extraction_result,
                "processing_info": {
                    "success": extraction_result.success,
                    "error": None if extraction_result.success else "Extraction failed",
                    "warnings": extraction_result.warnings or []
                }
            }
        
        return result
    
    async def process_file_object(self, file_obj: BinaryIO, file_name: str, method: Optional[ExtractionMethod] = None, organization=None) -> Dict[str, Any]:
        """
        Process a file object (e.g., from a file upload) and extract its text and metadata.
        
        Args:
            file_obj: File object to process
            file_name: Name of the file
            method: Extraction method to use
            
        Returns:
            Dictionary containing extracted text, metadata, and processing info
        """
        logger.info(f"Processing file object: {file_name}")
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            # Write the file object to the temporary file
            file_obj.seek(0)
            temp_file.write(file_obj.read())
            temp_file_path = temp_file.name
        
        try:
            # Process the temporary file
            result = await self.process_file(temp_file_path, method, organization)
            
            # Update file name in result
            result["file_name"] = file_name
            
            return result
            
        finally:
            # Clean up the temporary file
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Error removing temporary file {temp_file_path}: {str(e)}")
    
    async def process_directory(
        self, 
        directory_path: str, 
        extensions: Optional[List[str]] = None,
        method: Optional[ExtractionMethod] = None,
        organization=None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Process all files in a directory and extract their text and metadata.
        
        Args:
            directory_path: Path to the directory to process
            extensions: List of file extensions to process (e.g., ['.pdf', '.docx'])
            method: Extraction method to use
            
        Returns:
            Dictionary mapping file paths to processing results
        """
        logger.info(f"Processing directory: {directory_path}")
        
        if extensions is None:
            extensions = ['.pdf', '.docx', '.txt', '.md', '.csv', '.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.webp']
        
        # Find files with specified extensions
        files_to_process = []
        for root, _, files in os.walk(directory_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in extensions):
                    files_to_process.append(os.path.join(root, file))
        
        logger.info(f"Found {len(files_to_process)} files to process")
        
        # Process each file
        results = {}
        for file_path in files_to_process:
            try:
                result = await self.process_file(file_path, method, organization)
                results[file_path] = result
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
                results[file_path] = {
                    "file_path": file_path,
                    "file_name": os.path.basename(file_path),
                    "file_size": os.path.getsize(file_path),
                    "error": str(e),
                    "success": False
                }
        
        return results
    
    def extract_text_for_rag(
        self, 
        file_path: str, 
        method: Optional[ExtractionMethod] = None
    ) -> Dict[str, Any]:
        """
        Extract text from a document specifically for RAG purposes.
        This method focuses on getting clean text suitable for embedding.
        
        Args:
            file_path: Path to the file to process
            method: Extraction method to use
            
        Returns:
            Dictionary containing extracted text and metadata for RAG
        """
        # Process the file
        result = self.process_file(file_path, method)
        extraction_result = result["extraction_result"]
        
        # Extract the text content
        text_content = extraction_result.extracted_text
        
        # For PDF with text extraction, include page information
        pages_content = []
        if result["file_type"] == "pdf" and result["extraction_method"] == "TextExtractor":
            if "pages" in extraction_result.metadata:
                for page in extraction_result.metadata["pages"]:
                    pages_content.append({
                        "page_number": page["page_number"],
                        "text": page["text"],
                        "word_count": page.get("word_count", 0)
                    })
        
        # For vision extraction, include page information if available
        elif result["extraction_method"] == "VisionExtractor":
            if "pages" in extraction_result.structured_data:
                for page in extraction_result.structured_data["pages"]:
                    pages_content.append({
                        "page_number": page["page_number"],
                        "text": page["content"],
                        "structured": page.get("structured", {})
                    })
        
        # For DOCX, include structure information
        structure = None
        if result["file_type"] == "docx" and "structure" in extraction_result.metadata:
            structure = {
                "title": extraction_result.metadata["structure"].get("title", ""),
                "headings": extraction_result.metadata["structure"].get("headings", []),
                "paragraphs": extraction_result.metadata["structure"].get("paragraphs", [])
            }
        
        # Create metadata for RAG
        metadata = {
            "file_name": result["file_name"],
            "file_type": result["file_type"],
            "file_size": result["file_size"],
            "extraction_method": result["extraction_method"],
            "word_count": len(text_content.split()) if text_content else 0,
            "warnings": result["processing_info"]["warnings"]
        }
        
        # Add document-specific metadata
        metadata.update(extraction_result.metadata)
        
        # Add model information if available
        if extraction_result.model_used:
            metadata["model_used"] = extraction_result.model_used
        if extraction_result.provider_used:
            metadata["provider_used"] = extraction_result.provider_used
        if extraction_result.cost_usd:
            metadata["cost_usd"] = float(extraction_result.cost_usd)
        if extraction_result.confidence_score:
            metadata["confidence_score"] = extraction_result.confidence_score
        
        # Return RAG-specific result
        rag_result = {
            "text": text_content,
            "metadata": metadata,
            "pages": pages_content if pages_content else None,
            "structure": structure,
            "structured_data": extraction_result.structured_data
        }
        
        return rag_result


# Utility function to create a document processor with default configuration
def create_document_processor(
    method: ExtractionMethod = ExtractionMethod.AUTO
) -> DocumentProcessor:
    """
    Create a document processor with default configuration.
    
    Args:
        method: Default extraction method to use
        
    Returns:
        DocumentProcessor instance
    """
    text_config = TextExtractorConfig(
        preserve_formatting=True,
        extract_tables=True,
        remove_headers_footers=False,
        min_text_density=0.1,
        strip_page_numbers=False,
        detect_sections=True
    )
    
    vision_config = VisionConfig(
        priority='balanced',
        max_cost_per_document=1.0,
        structured_output=True
    )
    
    return DocumentProcessor(
        text_config=text_config,
        vision_config=vision_config,
        default_method=method
    )
