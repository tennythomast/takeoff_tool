"""
Test script for chunked LLM extraction service

This script tests the new chunked extraction approach that:
1. Provides full document context to the LLM
2. Requests output in chunks to avoid token limits
3. Automatically continues until all elements are extracted
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Set up Django environment
# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'takeoff_tool.settings')
import django
django.setup()

from asgiref.sync import sync_to_async
from rag_service.models import Document
from takeoff.models import Drawing, TakeoffExtraction, TakeoffElement
from takeoff.services.extractors.llm_extraction_chunked import ChunkedLLMExtractionService
from core.models import Organization, User


async def run_test():
    """Test the chunked extraction service"""
    
    print("\n" + "="*80)
    print("CHUNKED EXTRACTION TEST")
    print("="*80 + "\n")
    
    # Initialize the chunked extraction service
    service = ChunkedLLMExtractionService()
    
    try:
        # Look for the most recent document with title '7_FLETT_RD.pdf'
        documents = await sync_to_async(lambda: list(Document.objects.filter(title='7_FLETT_RD.pdf').order_by('-created_at')))()
        if not documents:
            raise Document.DoesNotExist("No documents found with title '7_FLETT_RD.pdf'")
        
        document = documents[0]  # Get the most recent document
        print(f"Found existing document: {document.title} (ID: {document.id})")
        
        # Get page count
        page_count = await sync_to_async(lambda: document.chunks.count())()
        print(f"Document has {page_count} pages")
        
        # Check if a drawing already exists for this document
        drawing = await sync_to_async(lambda: Drawing.objects.filter(rag_document=document).first())()
        if drawing:
            # Update the drawing title to match the actual file name
            if drawing.drawing_title != "7_FLETT_RD.pdf":
                drawing.drawing_title = "7_FLETT_RD.pdf"
                await sync_to_async(drawing.save)()
                print(f"Updated existing drawing title to '7_FLETT_RD.pdf' (ID: {drawing.id})")
            else:
                print(f"Using existing drawing: {drawing.drawing_title} (ID: {drawing.id})")
        else:
            # Create a new drawing
            print("Creating new drawing...")
            
            # Get or create organization
            org = await sync_to_async(lambda: Organization.objects.first())()
            if not org:
                org = await sync_to_async(lambda: Organization.objects.create(
                    name="Test Organization",
                    slug="test-org"
                ))()
            
            # Get or create user
            user = await sync_to_async(lambda: User.objects.first())()
            
            # Generate unique drawing number
            import random
            unique_drawing_number = f"TEST-{random.randint(100000, 999999)}"
            
            drawing = await sync_to_async(lambda: Drawing.objects.create(
                organization=org,
                created_by=user,
                client="Test Client",
                project="Test Project",
                location="Test Location",
                drawing_number=unique_drawing_number,
                drawing_title="7_FLETT_RD.pdf",  # Updated to match the actual file name
                date=datetime.now().date(),
                page_count=page_count,
                rag_document=document
            ))()
            print(f"Created new drawing: {drawing.drawing_title} (ID: {drawing.id})")
        
        # Check for existing extractions
        latest_extraction = await sync_to_async(
            lambda: TakeoffExtraction.objects.filter(drawing=drawing).order_by('-extraction_date').first()
        )()
        
        if latest_extraction:
            # Get elements from the existing extraction
            elements = await sync_to_async(
                lambda: list(TakeoffElement.objects.filter(extraction=latest_extraction))
            )()
            
            # Print information about the existing extraction
            print("\nUsing existing extraction as reference for comparison")
            print(f"Existing extraction ID: {latest_extraction.id}")
            print(f"Existing extraction has {len(elements)} elements")
        else:
            print("No existing extractions found for this document.")
        
        # Run chunked extraction with real document data and actual LLM
        print("\n" + "="*80)
        print("STARTING CHUNKED EXTRACTION")
        print("="*80)
        print("This will use the actual LLM to extract data in chunks.")
        print("Full document context is provided, but output is requested in batches.")
        print("Note: This may incur costs for API usage.")
        print("="*80 + "\n")
        
        # Call the chunked extraction service
        result = await service.extract_elements(
            drawing_id=str(drawing.id),
            trade="concrete"
            # Let the router select the model automatically
        )
        
        # Check the result
        print("\n" + "="*80)
        print("EXTRACTION RESULT")
        print("="*80)
        print(f"Result: {json.dumps(result, indent=2)}")
        
        if result['success']:
            print(f"\n✅ Successfully extracted {result['element_count']} elements")
            print(f"   Pages processed: {result.get('pages_processed', result.get('chunks_processed', 'N/A'))}")
            print(f"   Total cost: ${result['total_cost_usd']:.4f}")
            print(f"   Processing time: {result['processing_time_ms']}ms")
            
            # Get the new extraction
            new_extraction = await sync_to_async(
                lambda: TakeoffExtraction.objects.get(id=result['extraction_id'])
            )()
            print(f"\nNew extraction ID: {new_extraction.id}, status: {new_extraction.status}")
            
            # Get elements from the new extraction
            new_elements = await sync_to_async(
                lambda: list(TakeoffElement.objects.filter(extraction=new_extraction))
            )()
            print(f"New extraction has {len(new_elements)} elements")
            
            # Print first few elements
            for i, element in enumerate(new_elements[:5], 1):
                print(f"\nElement {i}: {element.element_type} {element.element_id}")
                specs_preview = json.dumps(element.specifications, indent=2)[:200]
                print(f"  Specifications: {specs_preview}...")
            
            if len(new_elements) > 5:
                print(f"\n... and {len(new_elements) - 5} more elements")
            
            # Compare with existing extraction if available
            if latest_extraction and elements:
                print("\n" + "="*80)
                print("COMPARISON WITH EXISTING EXTRACTION")
                print("="*80)
                print(f"Original extraction: {len(elements)} elements")
                print(f"New extraction: {len(new_elements)} elements")
                
                if len(new_elements) == len(elements):
                    print("✅ Element count matches original extraction")
                elif len(new_elements) > len(elements):
                    print(f"✅ New extraction found {len(new_elements) - len(elements)} MORE elements")
                else:
                    print(f"⚠️  New extraction found {len(elements) - len(new_elements)} FEWER elements")
            
            # Save results to file
            output_dir = '/app/backend/takeoff/tests/output'
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(output_dir, f'chunked_extraction_results_{timestamp}.json')
            
            output_data = {
                'metadata': {
                    'extraction_id': str(new_extraction.id),
                    'drawing_id': str(drawing.id),
                    'document_id': str(document.id),
                    'drawing_title': drawing.drawing_title,
                    'drawing_number': drawing.drawing_number,
                    'page_count': page_count,
                    'timestamp': datetime.now().isoformat(),
                    'extraction_status': new_extraction.status,
                    'processing_time_ms': result['processing_time_ms'],
                    'pages_processed': result.get('pages_processed', result.get('chunks_processed', 0)),
                    'total_cost_usd': result['total_cost_usd'],
                    'element_count': len(new_elements)
                },
                'elements': [
                    {
                        'element_id': elem.element_id,
                        'element_type': elem.element_type,
                        'specifications': elem.specifications,
                        'page_number': elem.page_number,
                        'confidence_score': elem.confidence_score
                    }
                    for elem in new_elements
                ]
            }
            
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            
            print(f"\nExtraction results saved to: {output_file}")
            
        else:
            print(f"\n❌ Extraction failed: {result['error']}")
            
    except Document.DoesNotExist:
        print("❌ Document '7_FLETT_RD.pdf' not found in the database.")
        print("Please run the process_document command first to create the document.")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_test())
