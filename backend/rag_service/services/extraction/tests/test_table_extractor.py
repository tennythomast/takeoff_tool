#!/usr/bin/env python
"""
Test script for table extraction.

This script demonstrates how to use the TableExtractor class for extracting tables from documents.
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
    TableExtractor,
    TableExtractionMethod
)


async def test_table_extraction(file_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Test table extraction on a given file.
    
    Args:
        file_path: Path to the file to extract tables from
        output_path: Optional path to save the extraction result
        
    Returns:
        Extraction result
    """
    logger.info(f"Testing table extraction on file: {file_path}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return {"error": "File not found"}
    
    # Create table extractor
    extractor = TableExtractor()
    
    try:
        # Extract tables
        tables = await extractor.extract_tables(file_path)
        
        # Print summary
        print("\n=== Table Extraction Summary ===")
        print(f"File: {os.path.basename(file_path)}")
        print(f"Tables found: {len(tables)}")
        
        result = {
            "file_name": os.path.basename(file_path),
            "table_count": len(tables),
            "tables": []
        }
        
        # Print table details
        for i, table in enumerate(tables):
            print(f"\nTable {i+1}:")
            print(f"  Page: {table.get('page', 'Unknown')}")
            print(f"  Method: {table.get('method', 'Unknown')}")
            print(f"  Confidence: {table.get('confidence', 0):.2f}")
            
            df = table.get('data')
            if df is not None:
                print(f"  Rows: {len(df)}")
                print(f"  Columns: {len(df.columns)}")
                print(f"  Column names: {', '.join(df.columns)}")
                
                # Print sample
                print("\n  Sample (first 3 rows):")
                print(df.head(3).to_markdown(index=False))
            
            # Add to result
            result["tables"].append({
                "page": table.get('page', 'Unknown'),
                "method": table.get('method', 'Unknown'),
                "confidence": table.get('confidence', 0),
                "rows": len(df) if df is not None else 0,
                "columns": len(df.columns) if df is not None else 0,
                "column_names": list(df.columns) if df is not None else [],
                "markdown": table.get('markdown', '')
            })
        
        # Save result if output path is provided
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\nSaved extraction result to {output_path}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error extracting tables: {str(e)}")
        return {"error": str(e)}


async def main():
    """Main function to run the test."""
    parser = argparse.ArgumentParser(description="Test table extraction")
    parser.add_argument("file_path", help="Path to the file to extract tables from")
    parser.add_argument("-o", "--output", help="Path to save the extraction result")
    
    args = parser.parse_args()
    
    await test_table_extraction(args.file_path, args.output)


if __name__ == "__main__":
    asyncio.run(main())
