#!/usr/bin/env python
"""
Test script for hybrid extraction.

This script demonstrates how to use the HybridExtractor class for intelligent document extraction.
"""

import os
import sys
import json
import logging
import asyncio
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path to import the modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from rag_service.services.extraction import (
    HybridExtractor,
    ExtractionQualityScore
)


async def test_hybrid_extraction(file_path: str, output_path: Optional[str] = None, strategy: str = 'auto') -> Dict[str, Any]:
    """
    Test hybrid extraction on a given file.
    
    Args:
        file_path: Path to the file to extract text from
        output_path: Optional path to save the extraction result
        strategy: Extraction strategy ('auto', 'fast', 'parallel', 'vision_only')
        
    Returns:
        Extraction result
    """
    logger.info(f"Testing hybrid extraction on file: {file_path} using strategy: {strategy}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return {"error": "File not found"}
    
    # Create hybrid extractor
    extractor = HybridExtractor()
    
    try:
        # Extract text
        result = await extractor.extract(file_path, strategy=strategy)
        
        # Print summary
        print("\n=== Hybrid Extraction Summary ===")
        print(f"File: {os.path.basename(file_path)}")
        print(f"Strategy: {strategy} → {result.get('method', 'unknown')}")
        
        if result.get('primary_method'):
            print(f"Primary method: {result['primary_method']}")
        
        # Print quality scores
        quality = result.get('quality', {})
        if isinstance(quality, dict):
            print("\nQuality Scores:")
            for key, value in quality.items():
                if isinstance(value, float):
                    print(f"  {key}: {value:.2f}")
                else:
                    print(f"  {key}: {value}")
        elif isinstance(quality, ExtractionQualityScore):
            print("\nQuality Scores:")
            print(f"  Overall: {quality.overall_score:.2f}")
            print(f"  Text density: {quality.text_density:.2f}")
            print(f"  Structure preserved: {quality.structure_preserved}")
            print(f"  Tables extracted: {quality.tables_extracted}")
            print(f"  Reading order correct: {quality.reading_order_correct}")
            print(f"  Confidence: {quality.confidence:.2f}")
            if quality.issues:
                print("  Issues:")
                for issue in quality.issues:
                    print(f"    - {issue}")
        
        # Print cost and processing time
        print(f"\nCost: ${result.get('cost_usd', 0):.4f}")
        print(f"Processing time: {result.get('processing_time', 0):.2f} seconds")
        
        # Print text sample
        text = result.get('text', '')
        print("\nText Sample (first 500 chars):")
        print(text[:500] + "..." if len(text) > 500 else text)
        
        # Print table info if available
        tables = result.get('tables', [])
        if tables:
            print(f"\nTables found: {len(tables)}")
            for i, table in enumerate(tables[:2]):  # Show first 2 tables
                print(f"\nTable {i+1}:")
                if isinstance(table, dict):
                    for key, value in table.items():
                        if key not in ['data', 'markdown', 'text']:  # Skip large fields
                            print(f"  {key}: {value}")
        
        # Save result if output path is provided
        if output_path:
            # Create a serializable version of the result
            serializable_result = {
                "method": result.get('method', ''),
                "primary_method": result.get('primary_method', ''),
                "text_sample": text[:1000] + "..." if len(text) > 1000 else text,
                "metadata": result.get('metadata', {}),
                "quality": {
                    k: v for k, v in quality.items()
                } if isinstance(quality, dict) else {
                    "overall_score": quality.overall_score,
                    "text_density": quality.text_density,
                    "structure_preserved": quality.structure_preserved,
                    "tables_extracted": quality.tables_extracted,
                    "confidence": quality.confidence,
                    "issues": quality.issues
                },
                "cost_usd": result.get('cost_usd', 0),
                "processing_time": result.get('processing_time', 0),
                "table_count": len(tables)
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_result, f, indent=2, ensure_ascii=False)
            print(f"\nSaved extraction result to {output_path}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        return {"error": str(e)}


async def main():
    """Main function to run the test."""
    parser = argparse.ArgumentParser(description="Test hybrid extraction")
    parser.add_argument("file_path", help="Path to the file to extract text from")
    parser.add_argument("-o", "--output", help="Path to save the extraction result")
    parser.add_argument("-s", "--strategy", choices=["auto", "fast", "parallel", "vision_only"], 
                        default="auto", help="Extraction strategy to use")
    
    args = parser.parse_args()
    
    await test_hybrid_extraction(args.file_path, args.output, args.strategy)


if __name__ == "__main__":
    asyncio.run(main())
