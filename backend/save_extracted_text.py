import os
import sys
import json
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'takeoff_tool.settings')
django.setup()

# Import the TextExtractor
from rag_service.services.extraction.text import TextExtractor, TextExtractorConfig

def save_extracted_text(file_path, output_path):
    """
    Extract text and save it to a file.
    
    Args:
        file_path: Path to the file to extract text from
        output_path: Path to save the extracted text to
    """
    print(f"Extracting text from: {file_path}")
    
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
        
        # Save full text
        with open(output_path, 'w') as f:
            f.write("=== FULL EXTRACTED TEXT ===\n\n")
            f.write(result.get('text', ''))
            
            f.write("\n\n=== TEXT BY PAGE ===\n\n")
            for i, page in enumerate(result.get('pages', [])):
                f.write(f"\n--- PAGE {page['page_number']} ---\n\n")
                f.write(page.get('text', ''))
                
            f.write("\n\n=== PAGE METADATA ===\n\n")
            f.write(json.dumps(result.get('pages', []), indent=2))
            
        print(f"Extracted text saved to: {output_path}")
        
    except Exception as e:
        print(f"Error extracting text: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python save_extracted_text.py <input_file_path> <output_file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    output_path = sys.argv[2]
    save_extracted_text(file_path, output_path)
