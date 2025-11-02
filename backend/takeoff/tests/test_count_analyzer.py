"""
Test script for Count Analyzer

This script tests the count analyzer service that extracts element counts
from engineering drawings using vector data and pattern matching.
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Set up Django environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'takeoff_tool.settings')
import django
django.setup()

from asgiref.sync import sync_to_async
from takeoff.models import Drawing, TakeoffExtraction, TakeoffElement
from takeoff.services.measurement.count_analyzer import CountAnalyzer
from rag_service.models import Document


async def run_test():
    """Test the count analyzer service"""
    
    print("\n" + "="*80)
    print("COUNT ANALYZER TEST")
    print("="*80 + "\n")
    
    # Initialize the count analyzer
    analyzer = CountAnalyzer()
    
    try:
        # Look for the most recent document with title 'test_file3.pdf'
        documents = await sync_to_async(lambda: list(Document.objects.filter(title='test_file3.pdf').order_by('-created_at')))()
        if not documents:
            print("❌ Document 'test_file3.pdf' not found in the database.")
            return
        
        document = documents[0]
        print(f"Found document: {document.title} (ID: {document.id})")
        
        # Get the drawing linked to this document
        drawing = await sync_to_async(lambda: Drawing.objects.filter(rag_document=document).first())()
        if not drawing:
            print("❌ No drawing found linked to this document.")
            return
        
        print(f"Found drawing: {drawing.drawing_title} (ID: {drawing.id})")
        
        # Get the latest extraction
        extraction = await sync_to_async(
            lambda: TakeoffExtraction.objects.filter(drawing=drawing).order_by('-extraction_date').first()
        )()
        
        if not extraction:
            print("❌ No extractions found for this drawing.")
            return
        
        print(f"Found extraction: {extraction.id} (Status: {extraction.status})")
        
        # Get element count
        element_count = await sync_to_async(
            lambda: TakeoffElement.objects.filter(extraction=extraction).count()
        )()
        print(f"Extraction has {element_count} elements")
        
        # Show first few elements
        elements = await sync_to_async(
            lambda: list(TakeoffElement.objects.filter(extraction=extraction)[:5])
        )()
        
        print("\nSample elements:")
        for elem in elements:
            print(f"  - {elem.element_type} {elem.element_id} (Page {elem.page_number})")
        
        # Run count analysis
        print("\n" + "="*80)
        print("STARTING COUNT ANALYSIS")
        print("="*80)
        print("Analyzing elements to extract counts from document content...")
        print("="*80 + "\n")
        
        # Analyze the extraction
        results = await analyzer.analyze_extraction(
            str(extraction.id),
            update_elements=True  # Update elements with found counts
        )
        
        # Display results
        print("\n" + "="*80)
        print("ANALYSIS RESULTS")
        print("="*80)
        print(f"Total elements analyzed: {results['total_elements']}")
        print(f"Elements with count found: {results['elements_with_count']}")
        print(f"Elements without count: {results['elements_without_count']}")
        print(f"Elements flagged: {results['elements_flagged']}")
        
        # Show detailed results for first few elements
        print("\n" + "-"*80)
        print("DETAILED ELEMENT RESULTS (First 10)")
        print("-"*80)
        
        for i, elem_result in enumerate(results['element_results'][:10], 1):
            print(f"\n{i}. {elem_result['element_type']} {elem_result['element_id']} (Page {elem_result['page_number']})")
            
            if elem_result['count_found']:
                print(f"   ✅ Count: {elem_result['count']}")
                print(f"   Confidence: {elem_result['count_confidence']:.2f}")
                print(f"   Method: {elem_result['count_method']}")
                if elem_result.get('position'):
                    print(f"   Position: {elem_result['position']}")
                if elem_result.get('context_text'):
                    context = elem_result['context_text'][:100]
                    print(f"   Context: {context}...")
            else:
                print(f"   ❌ Count not found")
                if elem_result['flagged']:
                    print(f"   Flag reason: {elem_result['flag_reason']}")
                if elem_result.get('context_text'):
                    context = elem_result['context_text'][:100]
                    print(f"   Context: {context}...")
        
        # Show summary by element type
        print("\n" + "-"*80)
        print("SUMMARY BY ELEMENT TYPE")
        print("-"*80)
        
        type_summary = {}
        for elem_result in results['element_results']:
            elem_type = elem_result['element_type']
            if elem_type not in type_summary:
                type_summary[elem_type] = {
                    'total': 0,
                    'with_count': 0,
                    'flagged': 0
                }
            
            type_summary[elem_type]['total'] += 1
            if elem_result['count_found']:
                type_summary[elem_type]['with_count'] += 1
            if elem_result['flagged']:
                type_summary[elem_type]['flagged'] += 1
        
        for elem_type, summary in sorted(type_summary.items()):
            success_rate = (summary['with_count'] / summary['total'] * 100) if summary['total'] > 0 else 0
            print(f"\n{elem_type}:")
            print(f"  Total: {summary['total']}")
            print(f"  With count: {summary['with_count']} ({success_rate:.1f}%)")
            print(f"  Flagged: {summary['flagged']}")
        
        # Save results to file
        output_dir = '/app/backend/takeoff/tests/output'
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(output_dir, f'count_analysis_results_{timestamp}.json')
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n\nResults saved to: {output_file}")
        
        # Check updated elements
        print("\n" + "="*80)
        print("CHECKING UPDATED ELEMENTS")
        print("="*80)
        
        updated_elements = await sync_to_async(
            lambda: list(TakeoffElement.objects.filter(
                extraction=extraction,
                specifications__has_key='quantity'
            )[:5])
        )()
        
        print(f"\nFound {len(updated_elements)} elements with quantity field (showing first 5):")
        for elem in updated_elements:
            qty = elem.specifications.get('quantity')
            confidence = elem.specifications.get('quantity_confidence', 0)
            method = elem.specifications.get('quantity_method', 'unknown')
            print(f"  - {elem.element_type} {elem.element_id}: Qty={qty}, Confidence={confidence:.2f}, Method={method}")
        
        print("\n✅ Count analysis complete!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_test())
