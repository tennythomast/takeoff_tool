import os
import sys
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'takeoff_tool.settings')
django.setup()

# Import the TextExtractor
from rag_service.services.extraction.text import TextExtractor, TextExtractorConfig

def print_full_text(file_path):
    """
    Extract and print the full text from a file.
    
    Args:
        file_path: Path to the file to extract text from
    """
    print(f"Extracting full text from: {file_path}")
    
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
        
        # Print full text
        print("\n=== FULL EXTRACTED TEXT ===\n")
        print(result.get('text', ''))
        
        # Print page-by-page text
        print("\n=== TEXT BY PAGE ===\n")
        for i, page in enumerate(result.get('pages', [])):
            print(f"\n--- PAGE {page['page_number']} ---\n")
            print(page.get('text', ''))
            
    except Exception as e:
        print(f"Error extracting text: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python print_full_text.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    print_full_text(file_path)
