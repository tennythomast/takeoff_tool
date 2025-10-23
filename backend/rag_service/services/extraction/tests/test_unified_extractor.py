#!/usr/bin/env python
"""
Test script for unified extraction.

This script demonstrates how to use the UnifiedExtractor class for extracting
multiple types of information from documents in a single LLM call.
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
    UnifiedExtractor,
    ExtractionRequest,
    ExtractionTask,
    MultiTaskPrompts,
    SpecializedPrompts
)


async def test_unified_extraction(
    file_path: str, 
    output_path: Optional[str] = None,
    tasks: Optional[str] = None
) -> Dict[str, Any]:
    """
    Test unified extraction on a given file.
    
    Args:
        file_path: Path to the file to extract from
        output_path: Optional path to save the extraction result
        tasks: Comma-separated list of tasks to perform (text,layout,tables,entities,summary,all)
        
    Returns:
        Extraction result
    """
    logger.info(f"Testing unified extraction on file: {file_path}")
    
    # Check if file exists
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return {"error": "File not found"}
    
    # Parse tasks
    task_map = {
        "text": ExtractionTask.TEXT,
        "layout": ExtractionTask.LAYOUT,
        "tables": ExtractionTask.TABLES,
        "entities": ExtractionTask.ENTITIES,
        "summary": ExtractionTask.SUMMARY,
        "all": ExtractionTask.ALL
    }
    
    extraction_tasks = []
    if tasks:
        for task in tasks.split(','):
            task = task.strip().lower()
            if task in task_map:
                extraction_tasks.append(task_map[task])
    
    if not extraction_tasks:
        extraction_tasks = [ExtractionTask.ALL]
    
    # Create unified extractor
    extractor = UnifiedExtractor()
    
    try:
        # Create extraction request
        request = ExtractionRequest(
            file_path=file_path,
            tasks=extraction_tasks,
            quality_priority='balanced',
            max_pages=5  # Limit to 5 pages for testing
        )
        
        # Extract content
        response = await extractor.extract(request)
        
        # Print summary
        print("\n=== Unified Extraction Summary ===")
        print(f"File: {os.path.basename(file_path)}")
        print(f"Tasks: {', '.join([t.value for t in extraction_tasks])}")
        print(f"Success: {response.success}")
        
        if not response.success:
            print(f"Error: {response.error}")
            return {"error": response.error}
        
        # Print cost and model info
        print(f"\nModel: {response.model_used} ({response.provider_used})")
        print(f"Cost: ${response.cost_usd:.4f}")
        print(f"Processing time: {response.processing_time_ms / 1000:.2f} seconds")
        
        # Print text sample
        if response.text:
            print("\nText Sample (first 300 chars):")
            print(response.text[:300] + "..." if len(response.text) > 300 else response.text)
        
        # Print layout blocks
        if response.layout_blocks:
            print(f"\nLayout Blocks: {len(response.layout_blocks)}")
            for i, block in enumerate(response.layout_blocks[:3]):  # Show first 3
                print(f"  Block {i+1}: {block['type']} - {block.get('text', '')[:50]}...")
        
        # Print tables
        if response.tables:
            print(f"\nTables: {len(response.tables)}")
            for i, table in enumerate(response.tables[:2]):  # Show first 2
                print(f"\nTable {i+1} (Page {table['page']}):")
                print(table['markdown'])
        
        # Print entities
        if response.entities:
            print(f"\nEntities: {len(response.entities)}")
            for i, entity in enumerate(response.entities[:5]):  # Show first 5
                print(f"  {entity['type']}: {entity['value']}")
        
        # Print summary
        if response.summary:
            print("\nSummary:")
            print(response.summary)
        
        # Save result if output path is provided
        if output_path:
            # Create a serializable version of the response
            result = {
                "file_name": os.path.basename(file_path),
                "success": response.success,
                "model_used": response.model_used,
                "provider_used": response.provider_used,
                "cost_usd": response.cost_usd,
                "processing_time_ms": response.processing_time_ms,
                "text_sample": response.text[:1000] + "..." if response.text and len(response.text) > 1000 else response.text,
                "layout_blocks_count": len(response.layout_blocks),
                "tables_count": len(response.tables),
                "entities_count": len(response.entities),
                "summary": response.summary,
                "warnings": response.warnings
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"\nSaved extraction result to {output_path}")
        
        return {
            "success": response.success,
            "text": response.text,
            "layout_blocks": response.layout_blocks,
            "tables": response.tables,
            "entities": response.entities,
            "summary": response.summary,
            "cost_usd": response.cost_usd
        }
        
    except Exception as e:
        logger.error(f"Error in unified extraction: {str(e)}")
        return {"error": str(e)}


async def main():
    """Main function to run the test."""
    parser = argparse.ArgumentParser(description="Test unified extraction")
    parser.add_argument("file_path", help="Path to the file to extract from")
    parser.add_argument("-o", "--output", help="Path to save the extraction result")
    parser.add_argument("-t", "--tasks", help="Comma-separated list of tasks (text,layout,tables,entities,summary,all)")
    
    args = parser.parse_args()
    
    await test_unified_extraction(args.file_path, args.output, args.tasks)


if __name__ == "__main__":
    asyncio.run(main())
