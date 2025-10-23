#!/usr/bin/env python
"""
Test script for vision-based extraction.

This script demonstrates how to use the VisionExtractor class for extracting text from images and scanned documents.
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path to import the modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from backend.rag_service.services.extraction import (
    VisionExtractor, 
    VisionConfig, 
    DocumentProcessor,
    ExtractionMethod
)


def test_vision_extraction(file_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Test vision-based extraction on a given file.
    
    Args:
        file_path: Path to the file to extract text from
        output_path: Optional path to save the extraction result
        
    Returns:
        Extraction result
    """
    logger.info(f"Testing vision extraction on file: {file_path}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return {"error": "File not found"}
    
    # Create vision extractor with default config
    config = VisionConfig(
        priority='balanced',
        max_cost_per_document=1.0,
        structured_output=True
    )
    extractor = VisionExtractor(config)
    
    try:
        # Extract text
        result = extractor.extract(file_path)
        
        # Print summary
        print("\n=== Vision Extraction Summary ===")
        print(f"File: {os.path.basename(file_path)}")
        print(f"Success: {result.success}")
        print(f"Model used: {result.model_used}")
        print(f"Provider: {result.provider_used}")
        print(f"Extraction method: {result.extraction_method}")
        print(f"Cost: ${result.cost_usd:.4f}")
        print(f"Processing time: {result.processing_time:.2f} seconds")
        print(f"Confidence score: {result.confidence_score:.2f}")
        print(f"Tokens used: {result.tokens_used_input} input, {result.tokens_used_output} output")
        print(f"Image count: {result.image_count}")
        
        if result.warnings:
            print("\nWarnings:")
            for warning in result.warnings:
                print(f"- {warning}")
        
        # Print text sample
        print("\nText Sample (first 500 chars):")
        print(result.extracted_text[:500] + "..." if len(result.extracted_text) > 500 else result.extracted_text)
        
        # Save result if output path is provided
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            print(f"\nSaved extraction result to {output_path}")
        
        return result.to_dict()
        
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        return {"error": str(e)}


def test_document_processor(file_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Test document processor with vision extraction on a given file.
    
    Args:
        file_path: Path to the file to extract text from
        output_path: Optional path to save the extraction result
        
    Returns:
        Extraction result
    """
    logger.info(f"Testing document processor with vision extraction on file: {file_path}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return {"error": "File not found"}
    
    # Create document processor
    processor = DocumentProcessor(default_method=ExtractionMethod.AUTO)
    
    try:
        # Extract text for RAG
        result = processor.extract_text_for_rag(file_path)
        
        # Print summary
        print("\n=== Document Processor Summary ===")
        print(f"File: {os.path.basename(file_path)}")
        print(f"Extraction method: {result['metadata']['extraction_method']}")
        
        if 'model_used' in result['metadata']:
            print(f"Model used: {result['metadata']['model_used']}")
        if 'provider_used' in result['metadata']:
            print(f"Provider: {result['metadata']['provider_used']}")
        if 'cost_usd' in result['metadata']:
            print(f"Cost: ${result['metadata']['cost_usd']:.4f}")
        if 'confidence_score' in result['metadata']:
            print(f"Confidence score: {result['metadata']['confidence_score']:.2f}")
        
        print(f"Word count: {result['metadata']['word_count']}")
        
        if result['metadata'].get('warnings'):
            print("\nWarnings:")
            for warning in result['metadata']['warnings']:
                print(f"- {warning}")
        
        # Print text sample
        print("\nText Sample (first 500 chars):")
        print(result['text'][:500] + "..." if len(result['text']) > 500 else result['text'])
        
        # Save result if output path is provided
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\nSaved extraction result to {output_path}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        return {"error": str(e)}


def main():
    """Main function to run the test."""
    parser = argparse.ArgumentParser(description="Test vision-based extraction")
    parser.add_argument("file_path", help="Path to the file to extract text from")
    parser.add_argument("-o", "--output", help="Path to save the extraction result")
    parser.add_argument("-m", "--method", choices=["vision", "auto", "processor"], default="vision",
                        help="Extraction method to use (vision, auto, or processor)")
    
    args = parser.parse_args()
    
    if args.method == "processor":
        test_document_processor(args.file_path, args.output)
    else:
        if args.method == "auto":
            # Use document processor with AUTO method
            processor = DocumentProcessor(default_method=ExtractionMethod.AUTO)
            result = processor.extract_text_for_rag(args.file_path)
            
            # Print summary
            print("\n=== Auto Extraction Summary ===")
            print(f"File: {os.path.basename(args.file_path)}")
            print(f"Selected method: {result['metadata']['extraction_method']}")
            print(f"Text length: {len(result['text'])} characters")
            
            # Save result if output path is provided
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False)
                print(f"\nSaved extraction result to {args.output}")
        else:
            # Use vision extractor directly
            test_vision_extraction(args.file_path, args.output)


if __name__ == "__main__":
    main()
