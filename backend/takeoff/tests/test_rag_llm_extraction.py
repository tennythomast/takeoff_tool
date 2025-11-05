"""
RAG and LLM Chunked Extraction Pipeline

This script handles:
1. RAG document processing (text extraction, tables, layout)
2. LLM chunked extraction (structured element extraction)

Separate from vector detection pipeline for modularity.
"""

import os
import sys
import asyncio
import json
import argparse
from datetime import datetime
from typing import Dict, Any
import warnings

# Set up Django environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'takeoff_tool.settings')
import django
django.setup()

from rag_service.services.document_pipeline import DocumentPipeline
from takeoff.services.extractors.llm_extraction_chunked import ChunkedLLMExtractionService
from takeoff.models import Drawing
from rag_service.models import Document
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

# Default configuration
DEFAULT_PDF = "/app/backend/rag_service/tests/7_FLETT_RD.pdf"
DEFAULT_KB_ID = "b59efd65-25c0-40fb-8ebe-fbc2ccb0767b"  # Test Knowledge Base

# Suppress warnings
warnings.filterwarnings('ignore', message='.*PDF appears to be scanned.*')
warnings.filterwarnings('ignore', message='.*pdfplumber extraction failed.*')
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*received a naive datetime.*')


async def process_document(
    pdf_path: str,
    kb_id: str,
    output_dir: str,
    run_llm: bool = True,
    trade: str = 'concrete'
) -> Dict[str, Any]:
    """
    Process document through RAG and optionally LLM extraction
    
    Args:
        pdf_path: Path to PDF file
        kb_id: Knowledge base ID
        output_dir: Directory to save results
        run_llm: Whether to run LLM chunked extraction
        trade: Trade type for LLM extraction (concrete, steel, etc.)
        
    Returns:
        Dictionary with processing results
    """
    User = get_user_model()
    results = {
        'success': False,
        'document_id': None,
        'drawing_id': None,
        'extraction_id': None,
        'rag_time_ms': 0,
        'llm_time_ms': 0,
        'total_cost': 0.0
    }
    
    print("="*80)
    print("RAG & LLM EXTRACTION PIPELINE")
    print("="*80)
    print(f"\nPDF: {pdf_path}")
    print(f"KB ID: {kb_id}")
    print(f"Trade: {trade}")
    print(f"Output directory: {output_dir}")
    
    try:
        # Get admin user
        get_user = sync_to_async(lambda: User.objects.filter(is_staff=True).first())
        user = await get_user()
        
        if not user:
            print(f"\n❌ No admin user found")
            return results
        
        # ====================================================================
        # STEP 1: RAG Document Processing
        # ====================================================================
        print(f"\n{'='*80}")
        print("[STEP 1/2] RAG DOCUMENT PROCESSING")
        print(f"{'='*80}")
        
        pipeline = DocumentPipeline()
        title = os.path.basename(pdf_path)
        
        print(f"\nProcessing document...")
        rag_result = await pipeline.process_document(
            file_path=pdf_path,
            knowledge_base_id=kb_id,
            title=title,
            created_by_id=user.id
        )
        
        if rag_result.get('status') != 'completed':
            print(f"\n❌ RAG processing failed: {rag_result.get('error', 'Unknown error')}")
            return results
        
        document_id = rag_result.get('document_id')
        results['document_id'] = document_id
        results['rag_time_ms'] = rag_result.get('processing_time_ms', 0)
        
        print(f"\n✅ RAG Processing Complete!")
        print(f"   Document ID: {document_id}")
        print(f"   Text length: {rag_result.get('text_length', 0):,} characters")
        print(f"   Tables: {rag_result.get('tables_count', 0)}")
        print(f"   Layout blocks: {rag_result.get('layout_blocks_count', 0)}")
        print(f"   Processing time: {results['rag_time_ms']:.2f}ms")
        
        # Save RAG results
        pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
        rag_output = os.path.join(output_dir, f"{pdf_name}_rag_results.json")
        
        with open(rag_output, 'w') as f:
            json.dump({
                'document_id': document_id,
                'text_length': rag_result.get('text_length', 0),
                'tables_count': rag_result.get('tables_count', 0),
                'layout_blocks_count': rag_result.get('layout_blocks_count', 0),
                'processing_time_ms': results['rag_time_ms'],
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"   Saved to: {rag_output}")
        
        # ====================================================================
        # STEP 2: LLM Chunked Extraction (Optional)
        # ====================================================================
        if run_llm and document_id:
            print(f"\n{'='*80}")
            print("[STEP 2/2] LLM CHUNKED EXTRACTION")
            print(f"{'='*80}")
            
            # Get or create Drawing from Document
            get_drawing = sync_to_async(lambda: Drawing.objects.filter(
                rag_document_id=document_id
            ).first())
            drawing = await get_drawing()
            
            if not drawing:
                # Create Drawing from Document
                get_doc = sync_to_async(lambda: Document.objects.get(id=document_id))
                doc = await get_doc()
                
                create_drawing = sync_to_async(Drawing.objects.create)
                drawing = await create_drawing(
                    title=doc.title,
                    file_path=pdf_path,
                    rag_document_id=document_id,
                    created_by_id=user.id,
                    status='processed'
                )
                print(f"\nCreated Drawing: {drawing.id}")
            
            results['drawing_id'] = str(drawing.id)
            
            # Run chunked extraction
            extraction_service = ChunkedLLMExtractionService()
            
            print(f"\nExtracting {trade} elements with LLM (chunked)...")
            extraction_result = await extraction_service.extract_elements(
                drawing_id=str(drawing.id),
                trade=trade,
                user_id=str(user.id) if user else None
            )
            
            if extraction_result.get('status') == 'completed':
                extraction_id = extraction_result.get('extraction_id')
                results['extraction_id'] = extraction_id
                results['llm_time_ms'] = extraction_result.get('total_time_ms', 0)
                results['total_cost'] = extraction_result.get('total_cost', 0)
                
                print(f"\n✅ LLM Extraction Complete!")
                print(f"   Extraction ID: {extraction_id}")
                print(f"   Elements extracted: {extraction_result.get('total_elements', 0)}")
                print(f"   Total cost: ${results['total_cost']:.4f}")
                print(f"   Processing time: {results['llm_time_ms']:.2f}ms")
                
                # Save LLM results
                llm_output = os.path.join(output_dir, f"{pdf_name}_llm_extraction.json")
                
                with open(llm_output, 'w') as f:
                    json.dump({
                        'extraction_id': extraction_id,
                        'drawing_id': str(drawing.id),
                        'total_elements': extraction_result.get('total_elements', 0),
                        'total_cost': results['total_cost'],
                        'processing_time_ms': results['llm_time_ms'],
                        'timestamp': datetime.now().isoformat()
                    }, f, indent=2)
                
                print(f"   Saved to: {llm_output}")
            else:
                print(f"\n❌ LLM extraction failed: {extraction_result.get('error', 'Unknown error')}")
        
        results['success'] = True
        
        # ====================================================================
        # SUMMARY
        # ====================================================================
        print(f"\n{'='*80}")
        print("PROCESSING COMPLETE")
        print(f"{'='*80}")
        
        print(f"\n📊 Summary:")
        print(f"   Document ID: {results['document_id']}")
        if results['drawing_id']:
            print(f"   Drawing ID: {results['drawing_id']}")
        if results['extraction_id']:
            print(f"   Extraction ID: {results['extraction_id']}")
        print(f"   RAG time: {results['rag_time_ms']:.2f}ms")
        if run_llm:
            print(f"   LLM time: {results['llm_time_ms']:.2f}ms")
            print(f"   Total cost: ${results['total_cost']:.4f}")
        print(f"   Total time: {results['rag_time_ms'] + results['llm_time_ms']:.2f}ms")
        
        return results
        
    except Exception as e:
        print(f"\n❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='RAG & LLM Extraction Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline (RAG + LLM)
  python test_rag_llm_extraction.py --pdf gwynne1.pdf
  
  # RAG only (no LLM)
  python test_rag_llm_extraction.py --pdf gwynne1.pdf --no-llm
  
  # Custom trade type
  python test_rag_llm_extraction.py --pdf gwynne1.pdf --trade steel
  
  # Custom KB ID
  python test_rag_llm_extraction.py --pdf gwynne1.pdf --kb-id <your-kb-id>
        """
    )
    
    parser.add_argument(
        '--pdf',
        type=str,
        default=DEFAULT_PDF,
        help=f'Path to PDF file (default: {DEFAULT_PDF})'
    )
    
    parser.add_argument(
        '--kb-id',
        type=str,
        default=DEFAULT_KB_ID,
        help=f'Knowledge base ID (default: {DEFAULT_KB_ID})'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='/app/backend/takeoff/tests/output',
        help='Output directory for results (default: /app/backend/takeoff/tests/output)'
    )
    
    parser.add_argument(
        '--trade',
        type=str,
        default='concrete',
        choices=['concrete', 'steel', 'timber', 'masonry'],
        help='Trade type for LLM extraction (default: concrete)'
    )
    
    parser.add_argument(
        '--no-llm',
        action='store_true',
        help='Skip LLM extraction (RAG only)'
    )
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    # Run pipeline
    asyncio.run(process_document(
        pdf_path=args.pdf,
        kb_id=args.kb_id,
        output_dir=args.output,
        run_llm=not args.no_llm,
        trade=args.trade
    ))


if __name__ == "__main__":
    main()
