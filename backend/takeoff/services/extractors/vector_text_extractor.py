"""
Vector Text Extractor Service

This module provides functionality to extract text with precise coordinates from PDF files
using vector data. It leverages PyMuPDF (fitz) and pdfplumber for comprehensive text extraction
with positioning information.

Key Features:
- Extract text with exact PDF coordinates (x, y, width, height)
- Preserve bounding boxes for each text instance
- Support for page-by-page extraction
- Font and styling information
- Scale and coordinate system metadata
- Optimized for engineering drawings and technical documents

Usage:
    from takeoff.services.extractors.vector_text_extractor import VectorTextExtractor
    
    extractor = VectorTextExtractor()
    result = extractor.extract_from_file('path/to/drawing.pdf')
    
    # Access text instances with coordinates
    for page in result['pages']:
        for text_instance in page['text_instances']:
            print(f"Text: {text_instance['text']}")
            print(f"Position: {text_instance['bbox']}")
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import fitz  # PyMuPDF
import pdfplumber
from decimal import Decimal

logger = logging.getLogger(__name__)


@dataclass
class TextInstance:
    """Represents a single text instance with its position and metadata"""
    text: str
    bbox: Dict[str, float]  # {'x0': float, 'y0': float, 'x1': float, 'y1': float}
    center: Dict[str, float]  # {'x': float, 'y': float}
    page_number: int
    font_name: str = ""
    font_size: float = 0.0
    color: Optional[Tuple[float, ...]] = None
    flags: int = 0  # Font flags (bold, italic, etc.)
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'text': self.text,
            'bbox': self.bbox,
            'center': self.center,
            'page_number': self.page_number,
            'font_name': self.font_name,
            'font_size': self.font_size,
            'color': self.color,
            'flags': self.flags,
            'confidence': self.confidence,
            'width': self.bbox['x1'] - self.bbox['x0'],
            'height': self.bbox['y1'] - self.bbox['y0']
        }
    
    def is_bold(self) -> bool:
        """Check if text is bold"""
        return bool(self.flags & 2**4)
    
    def is_italic(self) -> bool:
        """Check if text is italic"""
        return bool(self.flags & 2**1)


@dataclass
class PageMetadata:
    """Metadata for a PDF page"""
    page_number: int
    width: float
    height: float
    rotation: int
    dpi: float = 72.0
    coordinate_system: str = "pdf"  # 'pdf' (bottom-left origin) or 'image' (top-left origin)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'page_number': self.page_number,
            'width': self.width,
            'height': self.height,
            'rotation': self.rotation,
            'dpi': self.dpi,
            'coordinate_system': self.coordinate_system,
            'aspect_ratio': self.width / self.height if self.height > 0 else 1.0
        }


@dataclass
class VectorTextExtractionConfig:
    """Configuration for vector text extraction"""
    min_text_length: int = 1  # Minimum text length to extract
    include_font_info: bool = True  # Include font metadata
    include_color_info: bool = True  # Include color information
    normalize_whitespace: bool = True  # Normalize whitespace in text
    deduplicate: bool = True  # Remove duplicate text instances
    deduplication_tolerance: float = 2.0  # Pixel tolerance for deduplication
    extract_rotated_text: bool = True  # Extract text at any rotation
    coordinate_system: str = "pdf"  # 'pdf' or 'image'
    page_numbers: Optional[List[int]] = None  # Specific pages to extract (None = all)
    
    # Performance settings
    use_pdfplumber_fallback: bool = True  # Use pdfplumber if PyMuPDF fails
    parallel_processing: bool = False  # Future: parallel page processing


class VectorTextExtractor:
    """
    Main vector text extractor class using PyMuPDF (fitz) as primary engine
    with pdfplumber as fallback for enhanced accuracy.
    
    This extractor is optimized for engineering drawings and technical documents
    where precise positioning is critical.
    """
    
    def __init__(self, config: Optional[VectorTextExtractionConfig] = None):
        """
        Initialize the vector text extractor.
        
        Args:
            config: Configuration options for extraction
        """
        self.config = config or VectorTextExtractionConfig()
        self._validate_dependencies()
    
    def _validate_dependencies(self):
        """Validate that required dependencies are available"""
        try:
            import fitz
        except ImportError:
            raise ImportError(
                "PyMuPDF (fitz) is required for vector text extraction. "
                "Install with: pip install PyMuPDF"
            )
        
        if self.config.use_pdfplumber_fallback:
            try:
                import pdfplumber
            except ImportError:
                logger.warning(
                    "pdfplumber is not installed. Fallback extraction will not be available. "
                    "Install with: pip install pdfplumber"
                )
                self.config.use_pdfplumber_fallback = False
    
    def extract_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text with coordinates from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary containing:
            {
                'success': bool,
                'file_path': str,
                'total_pages': int,
                'pages': List[Dict],  # Page-by-page extraction results
                'metadata': Dict,  # Document metadata
                'statistics': Dict,  # Extraction statistics
                'errors': List[str]  # Any errors encountered
            }
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        logger.info(f"Starting vector text extraction from: {file_path}")
        
        result = {
            'success': False,
            'file_path': file_path,
            'total_pages': 0,
            'pages': [],
            'metadata': {},
            'statistics': {
                'total_text_instances': 0,
                'unique_text_instances': 0,
                'average_font_size': 0.0,
                'extraction_method': 'pymupdf'
            },
            'errors': []
        }
        
        try:
            # Try PyMuPDF first (primary method)
            result = self._extract_with_pymupdf(file_path)
            result['success'] = True
            
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {str(e)}")
            result['errors'].append(f"PyMuPDF error: {str(e)}")
            
            # Fallback to pdfplumber if enabled
            if self.config.use_pdfplumber_fallback:
                try:
                    logger.info("Attempting extraction with pdfplumber fallback...")
                    result = self._extract_with_pdfplumber(file_path)
                    result['success'] = True
                    result['statistics']['extraction_method'] = 'pdfplumber'
                except Exception as e2:
                    logger.error(f"Pdfplumber extraction also failed: {str(e2)}")
                    result['errors'].append(f"pdfplumber error: {str(e2)}")
        
        # Calculate statistics
        if result['success']:
            self._calculate_statistics(result)
        
        return result
    
    def _extract_with_pymupdf(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text using PyMuPDF (fitz) - Primary method.
        
        PyMuPDF provides:
        - Fast extraction
        - Precise coordinate data
        - Font and style information
        - Good handling of complex PDFs
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extraction result dictionary
        """
        doc = fitz.open(file_path)
        
        result = {
            'file_path': file_path,
            'total_pages': len(doc),
            'pages': [],
            'metadata': self._extract_document_metadata(doc),
            'statistics': {
                'extraction_method': 'pymupdf'
            },
            'errors': []
        }
        
        # Determine which pages to process
        pages_to_process = (
            self.config.page_numbers 
            if self.config.page_numbers 
            else range(len(doc))
        )
        
        # Process each page
        for page_num in pages_to_process:
            try:
                page = doc[page_num]
                page_data = self._extract_page_pymupdf(page, page_num)
                result['pages'].append(page_data)
            except Exception as e:
                error_msg = f"Error processing page {page_num + 1}: {str(e)}"
                logger.error(error_msg)
                result['errors'].append(error_msg)
        
        doc.close()
        return result
    
    def _extract_page_pymupdf(self, page: fitz.Page, page_num: int) -> Dict[str, Any]:
        """
        Extract text instances from a single page using PyMuPDF.
        
        Args:
            page: fitz.Page object
            page_num: Page number (0-indexed)
            
        Returns:
            Dictionary containing page data and text instances
        """
        # Get page metadata
        page_rect = page.rect
        page_metadata = PageMetadata(
            page_number=page_num + 1,  # 1-indexed for user display
            width=page_rect.width,
            height=page_rect.height,
            rotation=page.rotation,
            dpi=72.0,
            coordinate_system=self.config.coordinate_system
        )
        
        # Extract text with detailed information
        # Using "dict" mode gives us word-level granularity with full metadata
        text_dict = page.get_text("dict")
        
        text_instances = []
        
        # Process each block
        for block in text_dict.get("blocks", []):
            # Only process text blocks (type 0), skip image blocks (type 1)
            if block.get("type") != 0:
                continue
            
            # Process each line in the block
            for line in block.get("lines", []):
                # Process each span (text with same formatting) in the line
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    
                    # Skip if text is too short
                    if len(text) < self.config.min_text_length:
                        continue
                    
                    # Get bounding box
                    bbox = span.get("bbox")  # (x0, y0, x1, y1)
                    
                    # Create text instance
                    text_instance = TextInstance(
                        text=text,
                        bbox={
                            'x0': bbox[0],
                            'y0': bbox[1],
                            'x1': bbox[2],
                            'y1': bbox[3]
                        },
                        center={
                            'x': (bbox[0] + bbox[2]) / 2,
                            'y': (bbox[1] + bbox[3]) / 2
                        },
                        page_number=page_num + 1,
                        font_name=span.get("font", "") if self.config.include_font_info else "",
                        font_size=span.get("size", 0.0) if self.config.include_font_info else 0.0,
                        color=span.get("color") if self.config.include_color_info else None,
                        flags=span.get("flags", 0),
                        confidence=1.0
                    )
                    
                    text_instances.append(text_instance)
        
        # Convert coordinates if needed
        if self.config.coordinate_system == "image":
            text_instances = self._convert_to_image_coordinates(
                text_instances, 
                page_rect.height
            )
        
        # Deduplicate if configured
        if self.config.deduplicate:
            text_instances = self._deduplicate_text_instances(text_instances)
        
        return {
            'page_metadata': page_metadata.to_dict(),
            'text_instances': [ti.to_dict() for ti in text_instances],
            'text_count': len(text_instances)
        }
    
    def _extract_with_pdfplumber(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text using pdfplumber - Fallback method.
        
        pdfplumber provides:
        - More accurate text extraction for some PDFs
        - Better table detection
        - Character-level precision
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Extraction result dictionary
        """
        result = {
            'file_path': file_path,
            'total_pages': 0,
            'pages': [],
            'metadata': {},
            'statistics': {},
            'errors': []
        }
        
        with pdfplumber.open(file_path) as pdf:
            result['total_pages'] = len(pdf.pages)
            result['metadata'] = {
                'title': pdf.metadata.get('Title', ''),
                'author': pdf.metadata.get('Author', ''),
                'creator': pdf.metadata.get('Creator', ''),
                'producer': pdf.metadata.get('Producer', ''),
                'page_count': len(pdf.pages)
            }
            
            # Determine which pages to process
            pages_to_process = (
                self.config.page_numbers 
                if self.config.page_numbers 
                else range(len(pdf.pages))
            )
            
            for page_num in pages_to_process:
                try:
                    page = pdf.pages[page_num]
                    page_data = self._extract_page_pdfplumber(page, page_num)
                    result['pages'].append(page_data)
                except Exception as e:
                    error_msg = f"Error processing page {page_num + 1}: {str(e)}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
        
        return result
    
    def _extract_page_pdfplumber(self, page, page_num: int) -> Dict[str, Any]:
        """
        Extract text instances from a single page using pdfplumber.
        
        Args:
            page: pdfplumber.Page object
            page_num: Page number (0-indexed)
            
        Returns:
            Dictionary containing page data and text instances
        """
        # Get page metadata
        page_metadata = PageMetadata(
            page_number=page_num + 1,
            width=float(page.width),
            height=float(page.height),
            rotation=page.rotation or 0,
            dpi=72.0,
            coordinate_system=self.config.coordinate_system
        )
        
        # Extract text with coordinates
        # chars gives us character-level data with precise positioning
        chars = page.chars
        
        # Group characters into words (pdfplumber doesn't do this automatically)
        words = self._group_chars_into_words(chars)
        
        text_instances = []
        
        for word_data in words:
            text = word_data['text'].strip()
            
            # Skip if text is too short
            if len(text) < self.config.min_text_length:
                continue
            
            # Create text instance
            text_instance = TextInstance(
                text=text,
                bbox={
                    'x0': word_data['x0'],
                    'y0': word_data['y0'],
                    'x1': word_data['x1'],
                    'y1': word_data['y1']
                },
                center={
                    'x': (word_data['x0'] + word_data['x1']) / 2,
                    'y': (word_data['y0'] + word_data['y1']) / 2
                },
                page_number=page_num + 1,
                font_name=word_data.get('fontname', '') if self.config.include_font_info else "",
                font_size=word_data.get('size', 0.0) if self.config.include_font_info else 0.0,
                confidence=0.95  # Slightly lower confidence for pdfplumber
            )
            
            text_instances.append(text_instance)
        
        # Convert coordinates if needed (pdfplumber uses image coordinates by default)
        if self.config.coordinate_system == "pdf":
            text_instances = self._convert_to_pdf_coordinates(
                text_instances,
                page_metadata.height
            )
        
        # Deduplicate if configured
        if self.config.deduplicate:
            text_instances = self._deduplicate_text_instances(text_instances)
        
        return {
            'page_metadata': page_metadata.to_dict(),
            'text_instances': [ti.to_dict() for ti in text_instances],
            'text_count': len(text_instances)
        }
    
    def _group_chars_into_words(self, chars: List[Dict]) -> List[Dict]:
        """
        Group individual characters into words.
        
        Args:
            chars: List of character dictionaries from pdfplumber
            
        Returns:
            List of word dictionaries with combined bounding boxes
        """
        if not chars:
            return []
        
        words = []
        current_word = None
        
        # Sort chars by position (top to bottom, left to right)
        sorted_chars = sorted(chars, key=lambda c: (c['top'], c['x0']))
        
        for char in sorted_chars:
            text = char.get('text', '')
            
            # Skip if whitespace
            if text.isspace():
                if current_word:
                    words.append(current_word)
                    current_word = None
                continue
            
            # Start new word or continue current word
            if current_word is None:
                current_word = {
                    'text': text,
                    'x0': char['x0'],
                    'y0': char['top'],
                    'x1': char['x1'],
                    'y1': char['bottom'],
                    'fontname': char.get('fontname', ''),
                    'size': char.get('size', 0.0)
                }
            else:
                # Check if this character continues the current word
                # (same line and close horizontal proximity)
                horizontal_gap = char['x0'] - current_word['x1']
                vertical_gap = abs(char['top'] - current_word['y0'])
                
                if horizontal_gap < 3 and vertical_gap < 2:  # Thresholds in PDF points
                    # Continue current word
                    current_word['text'] += text
                    current_word['x1'] = char['x1']
                    current_word['y1'] = max(current_word['y1'], char['bottom'])
                else:
                    # Start new word
                    words.append(current_word)
                    current_word = {
                        'text': text,
                        'x0': char['x0'],
                        'y0': char['top'],
                        'x1': char['x1'],
                        'y1': char['bottom'],
                        'fontname': char.get('fontname', ''),
                        'size': char.get('size', 0.0)
                    }
        
        # Add the last word
        if current_word:
            words.append(current_word)
        
        return words
    
    def _convert_to_image_coordinates(
        self, 
        text_instances: List[TextInstance], 
        page_height: float
    ) -> List[TextInstance]:
        """
        Convert from PDF coordinates (origin: bottom-left) to image coordinates (origin: top-left).
        
        Args:
            text_instances: List of text instances
            page_height: Height of the page
            
        Returns:
            Text instances with converted coordinates
        """
        for ti in text_instances:
            # Flip Y-axis
            ti.bbox['y0'] = page_height - ti.bbox['y1']
            ti.bbox['y1'] = page_height - ti.bbox['y0']
            ti.center['y'] = page_height - ti.center['y']
        
        return text_instances
    
    def _convert_to_pdf_coordinates(
        self,
        text_instances: List[TextInstance],
        page_height: float
    ) -> List[TextInstance]:
        """
        Convert from image coordinates (origin: top-left) to PDF coordinates (origin: bottom-left).
        
        Args:
            text_instances: List of text instances
            page_height: Height of the page
            
        Returns:
            Text instances with converted coordinates
        """
        for ti in text_instances:
            # Flip Y-axis
            y0_old = ti.bbox['y0']
            y1_old = ti.bbox['y1']
            ti.bbox['y0'] = page_height - y1_old
            ti.bbox['y1'] = page_height - y0_old
            ti.center['y'] = page_height - ti.center['y']
        
        return text_instances
    
    def _deduplicate_text_instances(
        self, 
        text_instances: List[TextInstance]
    ) -> List[TextInstance]:
        """
        Remove duplicate text instances that are at the same position.
        
        Some PDFs have overlapping text (e.g., bold text rendered multiple times).
        This function keeps only one instance per position.
        
        Args:
            text_instances: List of text instances
            
        Returns:
            Deduplicated list of text instances
        """
        if not text_instances:
            return text_instances
        
        unique_instances = []
        seen_positions = set()
        
        tolerance = self.config.deduplication_tolerance
        
        for ti in text_instances:
            # Create a position key (rounded to tolerance)
            pos_key = (
                round(ti.center['x'] / tolerance) * tolerance,
                round(ti.center['y'] / tolerance) * tolerance,
                ti.text
            )
            
            if pos_key not in seen_positions:
                seen_positions.add(pos_key)
                unique_instances.append(ti)
        
        return unique_instances
    
    def _extract_document_metadata(self, doc: fitz.Document) -> Dict[str, Any]:
        """
        Extract metadata from PDF document.
        
        Args:
            doc: fitz.Document object
            
        Returns:
            Dictionary of metadata
        """
        metadata = doc.metadata
        
        return {
            'title': metadata.get('title', ''),
            'author': metadata.get('author', ''),
            'subject': metadata.get('subject', ''),
            'creator': metadata.get('creator', ''),
            'producer': metadata.get('producer', ''),
            'creation_date': metadata.get('creationDate', ''),
            'modification_date': metadata.get('modDate', ''),
            'page_count': len(doc),
            'is_encrypted': doc.is_encrypted,
            'is_pdf': doc.is_pdf
        }
    
    def _calculate_statistics(self, result: Dict[str, Any]):
        """
        Calculate extraction statistics.
        
        Args:
            result: Extraction result dictionary (modified in place)
        """
        total_instances = 0
        font_sizes = []
        
        for page in result['pages']:
            total_instances += page['text_count']
            for ti in page['text_instances']:
                if ti['font_size'] > 0:
                    font_sizes.append(ti['font_size'])
        
        result['statistics']['total_text_instances'] = total_instances
        result['statistics']['unique_text_instances'] = total_instances  # After deduplication
        result['statistics']['average_font_size'] = (
            sum(font_sizes) / len(font_sizes) if font_sizes else 0.0
        )
    
    # Public utility methods
    
    def get_text_instances_by_page(
        self, 
        extraction_result: Dict[str, Any], 
        page_number: int
    ) -> List[Dict[str, Any]]:
        """
        Get all text instances for a specific page.
        
        Args:
            extraction_result: Result from extract_from_file()
            page_number: Page number (1-indexed)
            
        Returns:
            List of text instance dictionaries
        """
        for page in extraction_result['pages']:
            if page['page_metadata']['page_number'] == page_number:
                return page['text_instances']
        return []
    
    def find_text_instances(
        self,
        extraction_result: Dict[str, Any],
        search_text: str,
        case_sensitive: bool = False,
        exact_match: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Find all text instances matching search criteria.
        
        Args:
            extraction_result: Result from extract_from_file()
            search_text: Text to search for
            case_sensitive: Whether to match case
            exact_match: If True, requires exact match; if False, contains match
            
        Returns:
            List of matching text instances with page_number included
        """
        matches = []
        
        search_text_processed = search_text if case_sensitive else search_text.lower()
        
        for page in extraction_result['pages']:
            for ti in page['text_instances']:
                ti_text = ti['text'] if case_sensitive else ti['text'].lower()
                
                is_match = (
                    ti_text == search_text_processed if exact_match
                    else search_text_processed in ti_text
                )
                
                if is_match:
                    matches.append(ti)
        
        return matches
    
    def get_text_in_region(
        self,
        extraction_result: Dict[str, Any],
        page_number: int,
        region: Dict[str, float]  # {'x0': float, 'y0': float, 'x1': float, 'y1': float}
    ) -> List[Dict[str, Any]]:
        """
        Get all text instances within a specific region on a page.
        
        Args:
            extraction_result: Result from extract_from_file()
            page_number: Page number (1-indexed)
            region: Bounding box defining the region
            
        Returns:
            List of text instances within the region
        """
        page_instances = self.get_text_instances_by_page(extraction_result, page_number)
        
        instances_in_region = []
        
        for ti in page_instances:
            # Check if text instance center is within region
            if (region['x0'] <= ti['center']['x'] <= region['x1'] and
                region['y0'] <= ti['center']['y'] <= region['y1']):
                instances_in_region.append(ti)
        
        return instances_in_region


# Utility functions for external use

def extract_text_with_coordinates(
    file_path: str,
    config: Optional[VectorTextExtractionConfig] = None
) -> Dict[str, Any]:
    """
    Convenience function to extract text with coordinates from a PDF.
    
    Args:
        file_path: Path to PDF file
        config: Optional extraction configuration
        
    Returns:
        Extraction result dictionary
    """
    extractor = VectorTextExtractor(config)
    return extractor.extract_from_file(file_path)


def find_element_ids_in_pdf(
    file_path: str,
    element_ids: List[str],
    case_sensitive: bool = False
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Find all occurrences of element IDs in a PDF.
    
    Args:
        file_path: Path to PDF file
        element_ids: List of element IDs to find (e.g., ['C1', 'C2', 'B1'])
        case_sensitive: Whether to match case
        
    Returns:
        Dictionary mapping element_id to list of occurrences with coordinates
    """
    extractor = VectorTextExtractor()
    result = extractor.extract_from_file(file_path)
    
    if not result['success']:
        raise Exception(f"Extraction failed: {result['errors']}")
    
    matches = {}
    
    for element_id in element_ids:
        matches[element_id] = extractor.find_text_instances(
            result,
            element_id,
            case_sensitive=case_sensitive,
            exact_match=True
        )
    
    return matches