#!/usr/bin/env python
"""
Test script for document layout analysis.

This script demonstrates how to use the LayoutAnalyzer class for analyzing document structure.
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
    LayoutAnalyzer,
    LayoutBlock,
    BlockType
)


async def test_layout_analysis(file_path: str, output_path: Optional[str] = None, method: str = 'rule_based') -> Dict[str, Any]:
    """
    Test document layout analysis on a given file.
    
    Args:
        file_path: Path to the file to analyze
        output_path: Optional path to save the analysis result
        method: Analysis method ('rule_based', 'vision', or 'auto')
        
    Returns:
        Analysis result
    """
    logger.info(f"Testing layout analysis on file: {file_path} using method: {method}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return {"error": "File not found"}
    
    # Create layout analyzer
    analyzer = LayoutAnalyzer()
    
    try:
        # Analyze layout
        blocks = await analyzer.analyze_layout(file_path, method=method)
        
        # Convert to serializable format
        result = {
            "file_name": os.path.basename(file_path),
            "method": method,
            "block_count": len(blocks),
            "blocks": []
        }
        
        # Print summary
        print("\n=== Layout Analysis Summary ===")
        print(f"File: {os.path.basename(file_path)}")
        print(f"Method: {method}")
        print(f"Block count: {len(blocks)}")
        
        # Count block types
        type_counts = {}
        for block in blocks:
            block_type = block.type.value
            type_counts[block_type] = type_counts.get(block_type, 0) + 1
            
            # Add to result
            result["blocks"].append({
                "type": block.type.value,
                "text": block.text[:100] + "..." if len(block.text) > 100 else block.text,
                "page": block.page,
                "reading_order": block.reading_order,
                "confidence": block.confidence,
                "bbox": block.bbox,
                "metadata": block.metadata
            })
        
        # Print block type counts
        print("\nBlock Types:")
        for block_type, count in type_counts.items():
            print(f"- {block_type}: {count}")
        
        # Print sample blocks
        print("\nSample Blocks:")
        for i, block in enumerate(blocks[:5]):  # Show first 5 blocks
            print(f"\nBlock {i+1} ({block.type.value}):")
            print(f"  Page: {block.page}, Reading Order: {block.reading_order}")
            print(f"  Text: {block.text[:100]}..." if len(block.text) > 100 else f"  Text: {block.text}")
        
        # Save result if output path is provided
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\nSaved analysis result to {output_path}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing layout: {str(e)}")
        return {"error": str(e)}


async def main():
    """Main function to run the test."""
    parser = argparse.ArgumentParser(description="Test document layout analysis")
    parser.add_argument("file_path", help="Path to the file to analyze")
    parser.add_argument("-o", "--output", help="Path to save the analysis result")
    parser.add_argument("-m", "--method", choices=["rule_based", "vision", "auto"], default="rule_based",
                        help="Analysis method to use (rule_based, vision, or auto)")
    
    args = parser.parse_args()
    
    await test_layout_analysis(args.file_path, args.output, args.method)


if __name__ == "__main__":
    asyncio.run(main())
