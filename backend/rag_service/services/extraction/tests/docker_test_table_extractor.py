#!/usr/bin/env python
"""
Docker-compatible test script for TableExtractor.
"""

import os
import sys
import json
import logging
import asyncio
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path to import the modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from rag_service.services.extraction import TableExtractor, TableExtractionMethod
except ImportError:
    logger.error("Failed to import TableExtractor. Make sure the path is correct.")
    sys.exit(1)

async def test_table_extraction(file_path: str):
    """Test table extraction on a given file."""
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
        
        # Print table details
        for i, table in enumerate(tables[:5]):  # Show first 5 tables only
            print(f"\nTable {i+1}:")
            print(f"  Page: {table.get('page', 'Unknown')}")
            print(f"  Method: {table.get('method', 'Unknown')}")
            print(f"  Confidence: {table.get('confidence', 0):.2f}")
            
            df = table.get('data')
            if df is not None:
                print(f"  Rows: {len(df)}")
                print(f"  Columns: {len(df.columns)}")
                print(f"  Column names: {', '.join(df.columns)}")
                
                # Print markdown representation
                print("\n  Sample (first 3 rows):")
                print(table.get('markdown', ''))
        
        # Save result to a file
        output_path = "/app/table_extractor_result.json"
        result = {
            "file_name": os.path.basename(file_path),
            "table_count": len(tables),
            "tables": [
                {
                    "page": table.get('page', 'Unknown'),
                    "method": table.get('method', 'Unknown'),
                    "confidence": table.get('confidence', 0),
                    "rows": len(table.get('data')) if table.get('data') is not None else 0,
                    "columns": len(table.get('data').columns) if table.get('data') is not None else 0
                }
                for table in tables
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nSaved extraction result to {output_path}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error extracting tables: {str(e)}")
        return {"error": str(e)}

async def main():
    """Main function."""
    file_path = "/app/backend/rag_service/services/extraction/tests/STAR OF THE SEA COLLEGE - PRESTON LANE.pdf"
    await test_table_extraction(file_path)

if __name__ == "__main__":
    asyncio.run(main())
