"""
Text Extractor Service

This module provides functionality to extract text from various document formats:
- PDF (digital, not scanned)
- DOCX (Word documents)
- TXT (plain text)
- MD (Markdown)
- CSV (structured data)
"""

import os
import io
import csv
import logging
import fitz  # PyMuPDF
import docx
import chardet
import markdown
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class TextExtractorConfig:
    """Configuration for text extraction process."""
    preserve_formatting: bool = True
    extract_tables: bool = True
    remove_headers_footers: bool = False
    min_text_density: float = 0.1  # Warn if below this threshold
    max_page_size_mb: int = 10
    strip_page_numbers: bool = False
    detect_sections: bool = True


class TextExtractor:
    """
    Main text extractor class that handles different document formats.
    """
    
    def __init__(self, config: Optional[TextExtractorConfig] = None):
        """
        Initialize the text extractor with optional configuration.
        
        Args:
            config: Configuration options for text extraction
        """
        self.config = config or TextExtractorConfig()
        
    def extract(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from a file based on its extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary containing extracted text and metadata
            
        Raises:
            ValueError: If file format is not supported
            FileNotFoundError: If file doesn't exist
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > self.config.max_page_size_mb:
            logger.warning(f"File size ({file_size_mb:.2f}MB) exceeds configured maximum ({self.config.max_page_size_mb}MB)")
        
        file_ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_ext == '.pdf':
                return self._extract_pdf(file_path)
            elif file_ext == '.docx':
                return self._extract_docx(file_path)
            elif file_ext == '.txt':
                return self._extract_txt(file_path)
            elif file_ext == '.md':
                return self._extract_markdown(file_path)
            elif file_ext == '.csv':
                return self._extract_csv(file_path)
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            raise
    
    def _extract_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        result = {
            'text': '',
            'pages': [],
            'metadata': {},
            'is_scanned': False,
            'text_confidence': 1.0,
            'problematic_pages': []
        }
        
        try:
            # Open the PDF
            doc = fitz.open(file_path)
            
            # Extract metadata
            metadata = doc.metadata
            result['metadata'] = {
                'title': metadata.get('title', ''),
                'author': metadata.get('author', ''),
                'subject': metadata.get('subject', ''),
                'creator': metadata.get('creator', ''),
                'producer': metadata.get('producer', ''),
                'creation_date': metadata.get('creationDate', ''),
                'modification_date': metadata.get('modDate', ''),
                'page_count': len(doc)
            }
            
            # Process each page
            full_text = []
            low_text_density_pages = []
            
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                page_dict = self._process_pdf_page(page, page_num, page_text)
                result['pages'].append(page_dict)
                full_text.append(page_text)
                
                # Check for low text density (possible scanned page)
                if page_dict['text_density'] < self.config.min_text_density:
                    low_text_density_pages.append(page_num + 1)
            
            # Combine all text
            result['text'] = '\n\n'.join(full_text)
            
            # Set scanned flag if many pages have low text density
            if len(low_text_density_pages) > len(doc) * 0.5:
                result['is_scanned'] = True
                result['text_confidence'] = 0.3
                result['problematic_pages'] = low_text_density_pages
                logger.warning(f"PDF appears to be scanned. OCR might be needed. Low text density on pages: {low_text_density_pages}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing PDF: {str(e)}")
            raise
    
    def _process_pdf_page(self, page, page_num: int, page_text: str) -> Dict[str, Any]:
        """
        Process a single PDF page and extract its properties.
        
        Args:
            page: PyMuPDF page object
            page_num: Page number (0-indexed)
            page_text: Already extracted text from the page
            
        Returns:
            Dictionary with page properties
        """
        # Get page dimensions
        page_size = [page.rect.width, page.rect.height]
        
        # Count words
        word_count = len(page_text.split())
        
        # Calculate text density (words per square point)
        area = page_size[0] * page_size[1]
        text_density = word_count / area if area > 0 else 0
        
        # Check for images
        image_list = page.get_images()
        has_images = len(image_list) > 0
        
        # Try to detect tables (simple heuristic)
        has_tables = False
        table_count = 0
        
        # Check for table markers in text
        if '|' in page_text and '-+-' in page_text:
            has_tables = True
            table_count = page_text.count('-+-')
        
        # Get fonts used on the page
        fonts_used = []
        for block in page.get_text("dict")["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        font = span["font"]
                        if font not in fonts_used:
                            fonts_used.append(font)
        
        return {
            'page_number': page_num + 1,  # 1-indexed for user-friendliness
            'text': page_text,
            'word_count': word_count,
            'has_images': has_images,
            'image_count': len(image_list),
            'has_tables': has_tables,
            'table_count': table_count,
            'text_density': text_density,
            'fonts_used': fonts_used,
            'page_size': page_size,
        }
    
    def _extract_docx(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text and structure from a DOCX file.
        
        Args:
            file_path: Path to the DOCX file
            
        Returns:
            Dictionary containing extracted text and structure
        """
        result = {
            'text': '',
            'structure': {
                'title': '',
                'headings': [],
                'paragraphs': [],
                'tables': [],
                'lists': []
            },
            'properties': {}
        }
        
        try:
            # Open the document
            doc = docx.Document(file_path)
            
            # Extract document properties
            core_props = doc.core_properties
            result['properties'] = {
                'author': core_props.author or '',
                'title': core_props.title or '',
                'created': str(core_props.created) if core_props.created else '',
                'modified': str(core_props.modified) if core_props.modified else '',
                'category': core_props.category or '',
                'comments': core_props.comments or '',
                'subject': core_props.subject or '',
            }
            
            # Set title from document properties
            result['structure']['title'] = core_props.title or ''
            
            # Process paragraphs and other elements
            full_text = []
            position = 0
            
            for element in doc.element.body:
                # Process paragraphs
                if element.tag.endswith('p'):
                    paragraph = docx.text.paragraph.Paragraph(element, doc)
                    text = paragraph.text
                    
                    # Skip empty paragraphs
                    if not text.strip():
                        continue
                    
                    full_text.append(text)
                    
                    # Check if it's a heading
                    if paragraph.style.name.startswith('Heading'):
                        try:
                            level = int(paragraph.style.name.replace('Heading ', ''))
                        except ValueError:
                            level = 1
                            
                        result['structure']['headings'].append({
                            'level': level,
                            'text': text,
                            'position': position
                        })
                    
                    # Add to paragraphs list
                    result['structure']['paragraphs'].append({
                        'text': text,
                        'position': position
                    })
                    
                    position += len(text) + 1  # +1 for newline
                
                # Process tables
                elif element.tag.endswith('tbl'):
                    table_data = []
                    table_text = []
                    
                    for row_idx, row in enumerate(element.findall('.//w:tr', {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'})):
                        row_data = []
                        for cell in row.findall('.//w:tc', {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}):
                            cell_text = ''.join(p.text for p in docx.text.paragraph.Paragraph(p, doc) 
                                              for p in cell.findall('.//w:p', {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}))
                            row_data.append(cell_text)
                        
                        table_data.append(row_data)
                        table_text.append(' | '.join(row_data))
                    
                    # Add table text to full text
                    table_str = '\n'.join(table_text)
                    full_text.append(table_str)
                    
                    # Add to tables list
                    result['structure']['tables'].append({
                        'data': table_data,
                        'position': position,
                        'rows': len(table_data),
                        'columns': len(table_data[0]) if table_data else 0
                    })
                    
                    position += len(table_str) + 2  # +2 for double newline
            
            # Combine all text
            result['text'] = '\n\n'.join(full_text)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing DOCX: {str(e)}")
            raise
    
    def _extract_txt(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text from a plain text file with encoding detection.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        result = {
            'text': '',
            'encoding': '',
            'line_count': 0,
            'word_count': 0,
            'char_count': 0
        }
        
        try:
            # Detect encoding
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                
            detection = chardet.detect(raw_data)
            encoding = detection['encoding'] or 'utf-8'
            result['encoding'] = encoding
            
            # Read text with detected encoding
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                text = f.read()
            
            result['text'] = text
            result['line_count'] = text.count('\n') + 1
            result['word_count'] = len(text.split())
            result['char_count'] = len(text)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing text file: {str(e)}")
            raise
    
    def _extract_markdown(self, file_path: str) -> Dict[str, Any]:
        """
        Extract text and structure from a Markdown file.
        
        Args:
            file_path: Path to the Markdown file
            
        Returns:
            Dictionary containing extracted text and structure
        """
        result = {
            'text': '',
            'html': '',
            'structure': {
                'headings': [],
                'code_blocks': [],
                'links': [],
                'lists': [],
                'tables': []
            }
        }
        
        try:
            # Read the markdown file
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                md_text = f.read()
            
            result['text'] = md_text
            
            # Convert to HTML for structured parsing
            html = markdown.markdown(md_text, extensions=['tables', 'fenced_code'])
            result['html'] = html
            
            # Extract headings (simple regex approach)
            import re
            heading_pattern = r'^(#{1,6})\s+(.+)$'
            for line in md_text.split('\n'):
                match = re.match(heading_pattern, line)
                if match:
                    level = len(match.group(1))
                    text = match.group(2).strip()
                    result['structure']['headings'].append({
                        'level': level,
                        'text': text,
                        'position': md_text.find(line)
                    })
            
            # Extract code blocks
            code_block_pattern = r'```(\w*)\n(.*?)\n```'
            for match in re.finditer(code_block_pattern, md_text, re.DOTALL):
                language = match.group(1) or 'text'
                code = match.group(2)
                result['structure']['code_blocks'].append({
                    'language': language,
                    'code': code,
                    'position': match.start()
                })
            
            # Extract links
            link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
            for match in re.finditer(link_pattern, md_text):
                text = match.group(1)
                url = match.group(2)
                result['structure']['links'].append({
                    'text': text,
                    'url': url,
                    'position': match.start()
                })
            
            # Extract tables (simple detection)
            if '|' in md_text and '---' in md_text:
                table_sections = []
                current_table = []
                in_table = False
                
                for line in md_text.split('\n'):
                    if '|' in line:
                        if not in_table:
                            in_table = True
                            current_table = [line]
                        else:
                            current_table.append(line)
                    elif in_table and line.strip() == '':
                        table_sections.append('\n'.join(current_table))
                        current_table = []
                        in_table = False
                
                if in_table and current_table:
                    table_sections.append('\n'.join(current_table))
                
                for table_text in table_sections:
                    result['structure']['tables'].append({
                        'text': table_text,
                        'position': md_text.find(table_text)
                    })
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing Markdown file: {str(e)}")
            raise
    
    def _extract_csv(self, file_path: str) -> Dict[str, Any]:
        """
        Extract data from a CSV file.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            Dictionary containing extracted data and metadata
        """
        result = {
            'text': '',
            'data': [],
            'headers': [],
            'delimiter': '',
            'row_count': 0,
            'column_count': 0
        }
        
        try:
            # Detect delimiter
            with open(file_path, 'r', newline='', encoding='utf-8', errors='replace') as f:
                sample = f.read(4096)  # Read a sample to detect delimiter
            
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample)
            result['delimiter'] = dialect.delimiter
            
            # Read CSV data
            with open(file_path, 'r', newline='', encoding='utf-8', errors='replace') as f:
                reader = csv.reader(f, dialect=dialect)
                data = list(reader)
            
            if not data:
                return result
            
            # Extract headers and data
            headers = data[0]
            rows = data[1:]
            
            result['headers'] = headers
            result['data'] = rows
            result['row_count'] = len(rows)
            result['column_count'] = len(headers)
            
            # Convert to text representation
            text_rows = []
            
            # Add header
            text_rows.append(' | '.join(headers))
            text_rows.append('-' * (sum(len(h) for h in headers) + 3 * len(headers)))
            
            # Add data rows
            for row in rows:
                text_rows.append(' | '.join(row))
            
            result['text'] = '\n'.join(text_rows)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing CSV file: {str(e)}")
            raise


# Utility functions
def detect_file_type(file_path: str) -> str:
    """
    Detect file type based on extension and content.
    
    Args:
        file_path: Path to the file
        
    Returns:
        String representing the file type
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    # Map extensions to file types
    extension_map = {
        '.pdf': 'pdf',
        '.docx': 'docx',
        '.doc': 'doc',
        '.txt': 'text',
        '.md': 'markdown',
        '.csv': 'csv',
        '.xlsx': 'excel',
        '.xls': 'excel'
    }
    
    return extension_map.get(ext, 'unknown')


def is_scanned_pdf(file_path: str) -> bool:
    """
    Check if a PDF appears to be scanned rather than digital.
    
    Args:
        file_path: Path to the PDF file
        
    Returns:
        True if the PDF appears to be scanned, False otherwise
    """
    try:
        doc = fitz.open(file_path)
        
        # Check a sample of pages
        pages_to_check = min(5, len(doc))
        low_text_density_pages = 0
        
        for i in range(pages_to_check):
            page = doc[i]
            text = page.get_text()
            word_count = len(text.split())
            
            # Calculate text density
            area = page.rect.width * page.rect.height
            text_density = word_count / area if area > 0 else 0
            
            if text_density < 0.001:  # Very low text density threshold
                low_text_density_pages += 1
        
        # If most checked pages have low text density, it's likely scanned
        return low_text_density_pages > pages_to_check / 2
        
    except Exception as e:
        logger.error(f"Error checking if PDF is scanned: {str(e)}")
        return False
