"""
Example usage of the TextExtractor class.

This script demonstrates how to use the TextExtractor class in various scenarios:
1. Basic extraction from different file types
2. Batch processing multiple files
3. Handling errors and edge cases
4. Customizing extraction with different configurations
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


def basic_extraction_example(file_path: str) -> dict:
    """
    Basic example of extracting text from a file.
    
    Args:
        file_path: Path to the file to extract text from
        
    Returns:
        Dictionary containing extracted text and metadata
    """
    logger.info(f"Basic extraction example for file: {file_path}")
    
    # Create extractor with default config
    extractor = TextExtractor()
    
    # Extract text
    result = extractor.extract(file_path)
    
    # Print basic info
    print(f"\nExtracted {len(result.get('text', ''))} characters from {os.path.basename(file_path)}")
    
    return result


def custom_extraction_example(file_path: str) -> dict:
    """
    Example of extracting text with custom configuration.
    
    Args:
        file_path: Path to the file to extract text from
        
    Returns:
        Dictionary containing extracted text and metadata
    """
    logger.info(f"Custom extraction example for file: {file_path}")
    
    # Create custom config
    config = TextExtractorConfig(
        preserve_formatting=True,
        extract_tables=True,
        remove_headers_footers=True,  # Remove headers and footers
        min_text_density=0.05,  # Lower threshold for scanned detection
        strip_page_numbers=True,  # Strip page numbers
        detect_sections=True
    )
    
    # Create extractor with custom config
    extractor = TextExtractor(config)
    
    # Extract text
    result = extractor.extract(file_path)
    
    # Print basic info
    print(f"\nCustom extraction: {len(result.get('text', ''))} characters from {os.path.basename(file_path)}")
    
    return result


def batch_processing_example(directory_path: str, extensions: list = None) -> dict:
    """
    Example of batch processing multiple files.
    
    Args:
        directory_path: Path to directory containing files to process
        extensions: List of file extensions to process (e.g., ['.pdf', '.docx'])
        
    Returns:
        Dictionary mapping file paths to extraction results
    """
    logger.info(f"Batch processing example for directory: {directory_path}")
    
    if extensions is None:
        extensions = ['.pdf', '.docx', '.txt', '.md', '.csv']
    
    # Create extractor
    extractor = TextExtractor()
    
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
            logger.info(f"Processing {file_path}")
            result = extractor.extract(file_path)
            results[file_path] = result
            print(f"Processed {os.path.basename(file_path)}: {len(result.get('text', ''))} characters")
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            results[file_path] = {"error": str(e)}
    
    return results


def error_handling_example(file_path: str) -> dict:
    """
    Example of handling errors during extraction.
    
    Args:
        file_path: Path to the file to extract text from
        
    Returns:
        Dictionary containing extraction result or error information
    """
    logger.info(f"Error handling example for file: {file_path}")
    
    # Create extractor
    extractor = TextExtractor()
    
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Check if file is too large
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 50:  # 50 MB limit
            raise ValueError(f"File too large: {file_size_mb:.2f} MB (limit: 50 MB)")
        
        # Check if PDF is scanned
        if file_path.lower().endswith('.pdf') and is_scanned_pdf(file_path):
            print(f"Warning: {os.path.basename(file_path)} appears to be a scanned PDF. OCR might be needed.")
        
        # Extract text
        result = extractor.extract(file_path)
        return result
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        return {"error": "file_not_found", "message": str(e)}
        
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        return {"error": "value_error", "message": str(e)}
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"error": "unexpected_error", "message": str(e)}


def save_extraction_result(result: dict, output_path: str) -> None:
    """
    Save extraction result to a JSON file.
    
    Args:
        result: Extraction result dictionary
        output_path: Path to save the result to
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Prepare result for JSON serialization (handle non-serializable objects)
    def prepare_for_json(obj):
        if isinstance(obj, dict):
            return {k: prepare_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [prepare_for_json(item) for item in obj]
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        else:
            return str(obj)
    
    serializable_result = prepare_for_json(result)
    
    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(serializable_result, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved extraction result to {output_path}")


def main():
    """Main function to demonstrate the examples."""
    if len(sys.argv) < 2:
        print("Usage: python example_usage.py <file_or_directory_path> [output_directory]")
        sys.exit(1)
    
    path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "extraction_results"
    
    if os.path.isfile(path):
        # Single file examples
        print("\n=== Basic Extraction Example ===")
        basic_result = basic_extraction_example(path)
        
        print("\n=== Custom Extraction Example ===")
        custom_result = custom_extraction_example(path)
        
        print("\n=== Error Handling Example ===")
        error_result = error_handling_example(path)
        
        # Save results
        file_name = os.path.basename(path)
        save_extraction_result(basic_result, os.path.join(output_dir, f"{file_name}_basic.json"))
        save_extraction_result(custom_result, os.path.join(output_dir, f"{file_name}_custom.json"))
        
    elif os.path.isdir(path):
        # Directory batch processing example
        print("\n=== Batch Processing Example ===")
        batch_results = batch_processing_example(path)
        
        # Save results
        for file_path, result in batch_results.items():
            file_name = os.path.basename(file_path)
            save_extraction_result(result, os.path.join(output_dir, f"{file_name}.json"))
    
    else:
        print(f"Error: {path} is not a valid file or directory")
        sys.exit(1)


if __name__ == "__main__":
    main()
