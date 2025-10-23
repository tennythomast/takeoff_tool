"""
Test script for the TextExtractor class.

This script demonstrates how to use the TextExtractor class to extract text from various document formats.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path to import the text module
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from rag_service.services.extraction.text import TextExtractor, TextExtractorConfig, detect_file_type, is_scanned_pdf


def test_extractor(file_path):
    """
    Test the TextExtractor on a given file.
    
    Args:
        file_path: Path to the file to extract text from
    """
    logger.info(f"Testing TextExtractor on file: {file_path}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return
    
    # Detect file type
    file_type = detect_file_type(file_path)
    logger.info(f"Detected file type: {file_type}")
    
    # Check if PDF is scanned (if applicable)
    if file_type == 'pdf':
        is_scanned = is_scanned_pdf(file_path)
        logger.info(f"Is scanned PDF: {is_scanned}")
    
    # Create extractor with default config
    config = TextExtractorConfig(
        preserve_formatting=True,
        extract_tables=True,
        remove_headers_footers=False,
        min_text_density=0.1
    )
    extractor = TextExtractor(config)
    
    try:
        # Extract text
        result = extractor.extract(file_path)
        
        # Print summary
        print("\n=== Extraction Summary ===")
        print(f"File: {os.path.basename(file_path)}")
        print(f"Type: {file_type}")
        
        if file_type == 'pdf':
            print(f"Pages: {result['metadata'].get('page_count', 0)}")
            print(f"Author: {result['metadata'].get('author', 'Unknown')}")
            print(f"Title: {result['metadata'].get('title', 'Unknown')}")
            print(f"Is scanned: {result.get('is_scanned', False)}")
            print(f"Text confidence: {result.get('text_confidence', 1.0)}")
            print(f"Problematic pages: {result.get('problematic_pages', [])}")
            
            # Print page info
            print("\nPage Information:")
            for i, page in enumerate(result.get('pages', [])[:3]):  # Show first 3 pages only
                print(f"  Page {page['page_number']}:")
                print(f"    Words: {page['word_count']}")
                print(f"    Images: {page['image_count']}")
                print(f"    Tables: {page['table_count']}")
                print(f"    Text density: {page['text_density']:.4f}")
                print(f"    Fonts: {', '.join(page['fonts_used'][:3])}")  # Show first 3 fonts only
            
            if len(result.get('pages', [])) > 3:
                print(f"  ... and {len(result.get('pages', [])) - 3} more pages")
                
        elif file_type == 'docx':
            print(f"Author: {result['properties'].get('author', 'Unknown')}")
            print(f"Title: {result['properties'].get('title', 'Unknown')}")
            print(f"Created: {result['properties'].get('created', 'Unknown')}")
            print(f"Modified: {result['properties'].get('modified', 'Unknown')}")
            
            # Print structure info
            print("\nDocument Structure:")
            print(f"  Headings: {len(result['structure'].get('headings', []))}")
            print(f"  Paragraphs: {len(result['structure'].get('paragraphs', []))}")
            print(f"  Tables: {len(result['structure'].get('tables', []))}")
            
            # Print headings
            if result['structure'].get('headings'):
                print("\nHeadings:")
                for heading in result['structure']['headings'][:5]:  # Show first 5 headings only
                    print(f"  Level {heading['level']}: {heading['text']}")
                
                if len(result['structure']['headings']) > 5:
                    print(f"  ... and {len(result['structure']['headings']) - 5} more headings")
                    
        elif file_type == 'text':
            print(f"Encoding: {result.get('encoding', 'Unknown')}")
            print(f"Lines: {result.get('line_count', 0)}")
            print(f"Words: {result.get('word_count', 0)}")
            print(f"Characters: {result.get('char_count', 0)}")
            
        elif file_type == 'markdown':
            print(f"Headings: {len(result['structure'].get('headings', []))}")
            print(f"Code blocks: {len(result['structure'].get('code_blocks', []))}")
            print(f"Links: {len(result['structure'].get('links', []))}")
            print(f"Tables: {len(result['structure'].get('tables', []))}")
            
        elif file_type == 'csv':
            print(f"Delimiter: '{result.get('delimiter', ',')}'")
            print(f"Headers: {len(result.get('headers', []))}")
            print(f"Rows: {result.get('row_count', 0)}")
            print(f"Columns: {result.get('column_count', 0)}")
            
            # Print headers
            if result.get('headers'):
                print("\nHeaders:")
                print(f"  {', '.join(result['headers'])}")
                
            # Print sample rows
            if result.get('data'):
                print("\nSample Rows:")
                for row in result['data'][:3]:  # Show first 3 rows only
                    print(f"  {row}")
                
                if len(result['data']) > 3:
                    print(f"  ... and {len(result['data']) - 3} more rows")
        
        # Print text sample
        print("\nText Sample (first 500 chars):")
        print(result.get('text', '')[:500] + "..." if len(result.get('text', '')) > 500 else result.get('text', ''))
        
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")


if __name__ == "__main__":
    # Check if file path is provided
    if len(sys.argv) < 2:
        print("Usage: python test_text_extractor.py <file_path>")
        sys.exit(1)
    
    # Get file path from command line
    file_path = sys.argv[1]
    
    # Test extractor
    test_extractor(file_path)
