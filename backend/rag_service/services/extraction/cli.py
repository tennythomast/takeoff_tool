#!/usr/bin/env python
"""
Command-line interface for the document extraction service.

This script provides a command-line interface for extracting text from documents
using text-based, vision-based, and hybrid extraction methods.

Supported extraction methods:
- text: Traditional text extraction (PDFs, DOCX, TXT, etc.)
- vision: Vision-based extraction using LLMs (images, scanned documents)
- hybrid: Intelligent combination of text and vision methods
- auto: Automatically select the best method based on document type
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path to import the modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.extraction import (
    TextExtractor, TextExtractorConfig, 
    VisionExtractor, VisionConfig,
    HybridExtractor,
    DocumentProcessor, ExtractionMethod
)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Extract text from documents using text or vision methods")
    
    # Main arguments
    parser.add_argument("input", help="Input file or directory")
    parser.add_argument("-o", "--output", help="Output file or directory (default: stdout)")
    parser.add_argument("-f", "--format", choices=["text", "json", "summary"], default="text",
                        help="Output format (default: text)")
    
    # Extraction method
    parser.add_argument("-m", "--method", choices=["text", "vision", "hybrid", "auto"], default="auto",
                        help="Extraction method to use (default: auto)")
    
    # Processing options
    parser.add_argument("-r", "--recursive", action="store_true", help="Process directories recursively")
    parser.add_argument("-e", "--extensions", 
                        default=".pdf,.docx,.txt,.md,.csv,.jpg,.jpeg,.png,.tiff,.bmp,.webp",
                        help="Comma-separated list of file extensions to process")
    
    # Text extraction configuration
    text_group = parser.add_argument_group('Text extraction options')
    text_group.add_argument("--preserve-formatting", action="store_true", help="Preserve formatting")
    text_group.add_argument("--extract-tables", action="store_true", help="Extract tables")
    text_group.add_argument("--remove-headers-footers", action="store_true", help="Remove headers and footers")
    text_group.add_argument("--min-text-density", type=float, default=0.1,
                        help="Minimum text density threshold for scanned PDF detection (default: 0.1)")
    text_group.add_argument("--strip-page-numbers", action="store_true", help="Strip page numbers")
    
    # Vision extraction configuration
    vision_group = parser.add_argument_group('Vision extraction options')
    vision_group.add_argument("--vision-priority", choices=["cost", "quality", "balanced"], default="balanced",
                        help="Priority for vision model selection (default: balanced)")
    vision_group.add_argument("--max-cost", type=float, default=1.0,
                        help="Maximum cost per document in USD (default: 1.0)")
    vision_group.add_argument("--structured-output", action="store_true", default=True,
                        help="Request structured output from vision models")
    
    # Hybrid extraction configuration
    hybrid_group = parser.add_argument_group('Hybrid extraction options')
    hybrid_group.add_argument("--hybrid-strategy", choices=["auto", "fast", "parallel", "vision_only"], default="auto",
                        help="Strategy for hybrid extraction (default: auto)")
    
    # RAG options
    parser.add_argument("--rag", action="store_true", help="Process for RAG (Retrieval-Augmented Generation)")
    
    # Verbosity
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet output")
    
    return parser.parse_args()


async def process_file(file_path: str, args) -> Dict[str, Any]:
    """
    Process a single file.
    
    Args:
        file_path: Path to the file to process
        args: Command-line arguments
        
    Returns:
        Dictionary containing extraction result
    """
    logger.info(f"Processing file: {file_path}")
    
    # Map argument method to ExtractionMethod enum (for DocumentProcessor)
    method_map = {
        'text': ExtractionMethod.TEXT,
        'vision': ExtractionMethod.VISION,
        'auto': ExtractionMethod.AUTO,
        'hybrid': ExtractionMethod.AUTO  # For DocumentProcessor, hybrid is treated as auto
    }
    extraction_method = method_map[args.method]
    
    # Create text configuration
    text_config = TextExtractorConfig(
        preserve_formatting=args.preserve_formatting,
        extract_tables=args.extract_tables,
        remove_headers_footers=args.remove_headers_footers,
        min_text_density=args.min_text_density,
        strip_page_numbers=args.strip_page_numbers
    )
    
    # Create vision configuration
    vision_config = VisionConfig(
        priority=args.vision_priority,
        max_cost_per_document=args.max_cost,
        structured_output=args.structured_output
    )
    
    if args.rag:
        # Process for RAG
        processor = DocumentProcessor(
            text_config=text_config,
            vision_config=vision_config,
            default_method=extraction_method
        )
        result = processor.extract_text_for_rag(file_path)
    else:
        # Basic extraction based on method
        if args.method == 'vision':
            extractor = VisionExtractor(vision_config)
            extraction_result = extractor.extract(file_path)
            # Convert ExtractionResult to dict
            result = extraction_result.to_dict()
        elif args.method == 'text':
            extractor = TextExtractor(text_config)
            result = extractor.extract(file_path)
        elif args.method == 'hybrid':
            # Use the hybrid extractor
            extractor = HybridExtractor()
            result = await extractor.extract(
                file_path=file_path,
                strategy=args.hybrid_strategy
            )
        else:  # AUTO
            processor = DocumentProcessor(
                text_config=text_config,
                vision_config=vision_config,
                default_method=ExtractionMethod.AUTO
            )
            # Use the processor to determine the best method
            result = processor.process_file(file_path)
            # Extract the result from the processor output
            result = result["extraction_result"].to_dict() if hasattr(result["extraction_result"], "to_dict") else result["extraction_result"]
    
    return result


async def process_directory(dir_path: str, args) -> Dict[str, Dict[str, Any]]:
    """
    Process all files in a directory.
    
    Args:
        dir_path: Path to the directory to process
        args: Command-line arguments
        
    Returns:
        Dictionary mapping file paths to extraction results
    """
    logger.info(f"Processing directory: {dir_path}")
    
    # Parse extensions
    extensions = [ext.strip() for ext in args.extensions.split(",")]
    
    # Find files to process
    files_to_process = []
    if args.recursive:
        for root, _, files in os.walk(dir_path):
            for file in files:
                if any(file.lower().endswith(ext) for ext in extensions):
                    files_to_process.append(os.path.join(root, file))
    else:
        for file in os.listdir(dir_path):
            if any(file.lower().endswith(ext) for ext in extensions):
                files_to_process.append(os.path.join(dir_path, file))
    
    logger.info(f"Found {len(files_to_process)} files to process")
    
    # Process each file
    results = {}
    for file_path in files_to_process:
        try:
            result = await process_file(file_path, args)
            results[file_path] = result
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            results[file_path] = {"error": str(e)}
    
    return results


def format_output(result: Dict[str, Any], args) -> str:
    """
    Format extraction result based on output format.
    
    Args:
        result: Extraction result
        args: Command-line arguments
        
    Returns:
        Formatted output string
    """
    if args.format == "text":
        # Return just the extracted text
        return result.get("text", "")
    
    elif args.format == "summary":
        # Return a summary of the extraction
        output = []
        
        # Add basic info
        file_name = result.get("file_name", os.path.basename(args.input))
        output.append(f"File: {file_name}")
        
        # Add extraction method
        extraction_method = result.get("extraction_method", result.get("method", ""))
        if extraction_method:
            output.append(f"Extraction method: {extraction_method}")
            
        # Add primary method for hybrid extraction
        primary_method = result.get("primary_method", "")
        if primary_method:
            output.append(f"Primary method: {primary_method}")
        
        # Add model info if available
        if "model_used" in result:
            output.append(f"Model used: {result['model_used']}")
        if "provider_used" in result:
            output.append(f"Provider: {result['provider_used']}")
        
        # Add cost info if available
        if "cost_usd" in result:
            output.append(f"Cost: ${result['cost_usd']:.4f} USD")
        
        # Add metadata
        if "metadata" in result:
            metadata = result["metadata"]
            output.append("\nMetadata:")
            for key, value in metadata.items():
                if key not in ["extraction_method", "model_used", "provider_used", "cost_usd"]:
                    output.append(f"  {key}: {value}")
        
        # Add text stats
        text = result.get("text", "")
        word_count = len(text.split()) if text else 0
        char_count = len(text) if text else 0
        output.append(f"\nText Statistics:")
        output.append(f"  Characters: {char_count}")
        output.append(f"  Words: {word_count}")
        
        # Add warnings
        warnings = []
        if "warnings" in result:
            warnings.extend(result["warnings"])
        elif "processing_info" in result and "warnings" in result["processing_info"]:
            warnings.extend(result["processing_info"]["warnings"])
            
        if warnings:
            output.append("\nWarnings:")
            for warning in warnings:
                output.append(f"  - {warning}")
        
        # Add text sample
        if text:
            output.append("\nText Sample (first 500 chars):")
            output.append(text[:500] + "..." if len(text) > 500 else text)
        
        return "\n".join(output)
    
    else:  # json
        # Return the full result as JSON
        return json.dumps(result, indent=2, ensure_ascii=False)


def save_output(output: str, output_path: str) -> None:
    """
    Save output to a file.
    
    Args:
        output: Output string
        output_path: Path to save the output to
    """
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)
    
    logger.info(f"Saved output to {output_path}")


# This function is no longer needed since process_file is now async
# async def process_file_async(file_path: str, args) -> Dict[str, Any]:
#     """Process a file asynchronously (for hybrid extraction)."""
#     return await process_file(file_path, args)


async def main_async():
    """Async main function for hybrid extraction."""
    # Parse arguments
    args = parse_args()
    
    # Set logging level
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Process input
    input_path = args.input
    
    if os.path.isfile(input_path):
        # Process single file
        try:
            result = await process_file(input_path, args)
            output = format_output(result, args)
            
            if args.output:
                # Save to file
                save_output(output, args.output)
            else:
                # Print to stdout
                print(output)
        except Exception as e:
            logger.error(f"Error processing {input_path}: {str(e)}")
            print(f"Error: {str(e)}")
            sys.exit(1)
    else:
        print(f"Error: Async processing only supports single files")
        sys.exit(1)


def main():
    """Main function."""
    # Parse arguments
    args = parse_args()
    
    # If using hybrid extraction, use async main
    if args.method == 'hybrid':
        import asyncio
        asyncio.run(main_async())
        return
    
    # Set logging level
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Process input
    input_path = args.input
    
    if os.path.isfile(input_path):
        # Process single file
        try:
            # We need to run the async function in a synchronous context
            import asyncio
            result = asyncio.run(process_file(input_path, args))
            output = format_output(result, args)
            
            if args.output:
                # Save to file
                save_output(output, args.output)
            else:
                # Print to stdout
                print(output)
        except Exception as e:
            logger.error(f"Error processing {input_path}: {str(e)}")
            print(f"Error: {str(e)}")
            sys.exit(1)
            
    elif os.path.isdir(input_path):
        # Process directory
        # We need to run the async function in a synchronous context
        import asyncio
        results = asyncio.run(process_directory(input_path, args))
        
        if args.output:
            # Check if output is a directory
            if os.path.isdir(args.output) or args.output.endswith('/'):
                # Save each result to a separate file
                os.makedirs(args.output, exist_ok=True)
                
                for file_path, result in results.items():
                    file_name = os.path.basename(file_path)
                    output_file = os.path.join(args.output, f"{file_name}.{args.format}")
                    output = format_output(result, args)
                    save_output(output, output_file)
            else:
                # Save all results to a single file
                if args.format == "json":
                    # Save as JSON
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False)
                else:
                    # Save as text
                    with open(args.output, 'w', encoding='utf-8') as f:
                        for file_path, result in results.items():
                            file_name = os.path.basename(file_path)
                            output = format_output(result, args)
                            f.write(f"=== {file_name} ===\n\n")
                            f.write(output)
                            f.write("\n\n")
                
                logger.info(f"Saved all results to {args.output}")
        else:
            # Print summary to stdout
            print(f"Processed {len(results)} files:")
            for file_path, result in results.items():
                file_name = os.path.basename(file_path)
                if "error" in result:
                    print(f"- {file_name}: ERROR - {result['error']}")
                else:
                    # Get extraction method if available
                    method = result.get("extraction_method", "")
                    method_str = f" ({method})" if method else ""
                    
                    # Get text and word count
                    text = result.get("text", "")
                    word_count = len(text.split()) if text else 0
                    
                    # Get cost if available
                    cost_str = ""
                    if "cost_usd" in result and result["cost_usd"] > 0:
                        cost_str = f", cost: ${result['cost_usd']:.4f}"
                    
                    print(f"- {file_name}{method_str}: {word_count} words{cost_str}")
    
    else:
        print(f"Error: {input_path} is not a valid file or directory")
        sys.exit(1)


if __name__ == "__main__":
    main()
