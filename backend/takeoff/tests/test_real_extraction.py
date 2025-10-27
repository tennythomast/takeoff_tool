"""
Script to test LLM extraction using real document data from the production database

This script connects to the actual database and uses real document data
for testing the extraction process with the actual LLM (no mocking).

IMPORTANT: This test specifically uses test_file3.pdf which should be processed
using the process_document command before running this test:

python manage.py process_document --kb_id=<knowledge_base_id> --file=<path_to_test_file3.pdf> --rule-based
"""

import os
import sys
import json
import django
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock
from django.utils import timezone

# Set up Django environment
# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'takeoff_tool.settings')
django.setup()

from asgiref.sync import sync_to_async
from rag_service.models import Document, DocumentPage, KnowledgeBase
from takeoff.models import Drawing, TakeoffExtraction, TakeoffElement
from takeoff.services.llm_extraction import LLMExtractionService


async def run_test():
    """Main test function"""
    # Create the service
    service = LLMExtractionService()
    
    try:
        # Look for the most recent document with title 'test_file3.pdf'
        documents = await sync_to_async(lambda: list(Document.objects.filter(title='test_file3.pdf').order_by('-created_at')))()
        if not documents:
            raise Document.DoesNotExist("No documents found with title 'test_file3.pdf'")
        
        document = documents[0]  # Get the most recent document
        print(f"Found existing document: {document.title} (ID: {document.id})")
        
        # Get the document pages
        document_pages = await sync_to_async(lambda: list(DocumentPage.objects.filter(document=document)))()
        page_count = len(document_pages)
        print(f"Document has {page_count} pages")
        
        # Check if there's already a drawing linked to this document
        drawing = await sync_to_async(lambda: Drawing.objects.filter(rag_document=document).first())()
        if drawing:
            # Update the drawing title to match the actual file name
            if drawing.drawing_title != "test_file3.pdf":
                drawing.drawing_title = "test_file3.pdf"
                await sync_to_async(drawing.save)()
                print(f"Updated existing drawing title to 'test_file3.pdf' (ID: {drawing.id})")
            else:
                print(f"Using existing drawing: {drawing.drawing_title} (ID: {drawing.id})")
        else:
            # No drawing found, we need to create one
            print("No drawing found for this document. Creating one...")
            
            # Get the knowledge base ID and fetch it separately
            kb_id = await sync_to_async(lambda: document.knowledge_base_id)()
            knowledge_base = await sync_to_async(KnowledgeBase.objects.get)(id=kb_id)
            print(f"Using knowledge base: {knowledge_base.name} (ID: {knowledge_base.id})")
            
            # Get the organization ID and fetch it separately
            org_id = await sync_to_async(lambda: knowledge_base.organization_id)()
            from core.models import Organization
            organization = await sync_to_async(Organization.objects.get)(id=org_id)
            print(f"Using organization: {organization.name} (ID: {organization.id})")
            
            # Create a drawing linked to the document
            from django.utils import timezone
            import uuid
            from datetime import datetime
            
            # Generate a unique drawing number
            unique_drawing_number = f"TEST-{uuid.uuid4().hex[:6]}"
            
            drawing = await sync_to_async(Drawing.objects.create)(
                organization_id=organization.id,
                client="Test Client",
                project="Test Project",
                location="Test Location",
                drawing_number=unique_drawing_number,
                drawing_title="test_file3.pdf",  # Updated to match the actual file name
                date=datetime.now().date(),
                page_count=page_count,
                rag_document=document
            )
            print(f"Created new drawing with ID: {drawing.id}")
        
        # Check if we have existing extractions for this document
        existing_extractions = await sync_to_async(lambda: list(TakeoffExtraction.objects.filter(drawing=drawing).order_by('-created_at')))()
        
        if existing_extractions:
            # Use data from an existing extraction
            latest_extraction = existing_extractions[0]
            print(f"Found existing extraction: {latest_extraction.id}, status: {latest_extraction.status}")
            
            # Get the elements from the existing extraction
            elements = await sync_to_async(lambda: list(TakeoffElement.objects.filter(extraction=latest_extraction)))()
            print(f"Found {len(elements)} elements in the extraction")
            
            for element in elements:
                print(f"Element: {element.element_type} {element.element_id}")
                specs_json = json.dumps(element.specifications, indent=2)
                print(f"  Specifications: {specs_json[:200]}..." if len(specs_json) > 200 else specs_json)
            
            # Print information about the existing extraction
            print("\nUsing existing extraction as reference for comparison")
            print(f"Existing extraction ID: {latest_extraction.id}")
            print(f"Existing extraction has {len(elements)} elements")
        else:
            print("No existing extractions found for this document.")
        
        # Run extraction with real document data and actual LLM
        print("\nRunning extraction with real document data and actual LLM...")
        print("This will use the actual LLM to extract data from the document.")
        print("Note: This may incur costs for API usage.")
        
        # Call the extraction service
        result = await service.extract_elements(
            drawing_id=str(drawing.id),
            trade="concrete"
            # Let the router select the model automatically
        )
        
        # Add a longer delay to allow RunPod more time to fully process the request
        print("Waiting for extraction to complete (60 seconds)...")
        await asyncio.sleep(60)  # Wait 60 seconds to ensure we get the full response
        
        # Check the result
        print(f"Extraction result: {result}")
        if result['success']:
            print(f"Successfully extracted {result['element_count']} elements")
            
            # Get the new extraction
            new_extraction = await sync_to_async(TakeoffExtraction.objects.get)(id=result['extraction_id'])
            print(f"New extraction ID: {new_extraction.id}, status: {new_extraction.status}")
            
            # Get the new elements
            new_elements = await sync_to_async(lambda: list(TakeoffElement.objects.filter(extraction=new_extraction)))() 
            print(f"New extraction has {len(new_elements)} elements")
            
            # Show element details
            for element in new_elements:
                print(f"Element: {element.element_type} {element.element_id}")
                specs_json = json.dumps(element.specifications, indent=2)
                print(f"  Specifications: {specs_json[:200]}..." if len(specs_json) > 200 else specs_json)
                
            # Save extraction results to JSON file
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
            os.makedirs(output_dir, exist_ok=True)
            
            # Create a timestamp for the filename
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(output_dir, f'extraction_results_{timestamp}.json')
            
            # Check if we have raw extraction results in the response
            raw_elements = result.get('elements', [])
            if raw_elements:
                print(f"\nRaw extraction results: {len(raw_elements)} elements")
                for i, elem in enumerate(raw_elements[:5]):  # Show first 5 elements
                    print(f"Raw element {i+1}: {elem.get('element_type')} {elem.get('element_id')}")
                if len(raw_elements) > 5:
                    print(f"...and {len(raw_elements) - 5} more elements")
            
            # Prepare data for JSON export
            export_data = {
                'metadata': {
                    'extraction_id': str(new_extraction.id),
                    'drawing_id': str(drawing.id),
                    'document_id': str(document.id),
                    'drawing_title': drawing.drawing_title,
                    'drawing_number': drawing.drawing_number,
                    'page_count': drawing.page_count,
                    'timestamp': datetime.now().isoformat(),
                    'extraction_status': new_extraction.status,
                    'processing_time_ms': result.get('processing_time_ms', 0),
                    'element_count': len(new_elements),
                    'raw_element_count': len(raw_elements)
                },
                'elements': []
            }
            
            # Add elements to export data
            for element in new_elements:
                element_data = {
                    'element_id': element.element_id,
                    'element_type': element.element_type,
                    'specifications': element.specifications,
                    'confidence_score': float(element.confidence_score) if element.confidence_score else None
                }
                export_data['elements'].append(element_data)
                
            # Also include raw elements in the export
            export_data['raw_elements'] = raw_elements
            
            # Write to JSON file
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            print(f"\nExtraction results saved to: {output_file}")
            
            # Compare with original elements if they exist
            if existing_extractions:
                if len(new_elements) == len(elements):
                    print("✅ Element count matches original extraction")
                else:
                    print("❌ Element count does not match original extraction")
        else:
            print(f"❌ Extraction failed: {result['error']}")
            
    except Document.DoesNotExist:
        print("❌ Document 'test_file3.pdf' not found in the database.")
        print("Please run the process_document command first to create the document.")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the test
    asyncio.run(run_test())
