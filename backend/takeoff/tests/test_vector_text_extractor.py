"""
Test Script for Vector Text Extractor

This script demonstrates how to use the VectorTextExtractor service
and validates its functionality with various scenarios.

Usage:
    python test_vector_text_extractor.py --file path/to/drawing.pdf
    python test_vector_text_extractor.py --file path/to/drawing.pdf --elements C1,C2,B1
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Set up Django environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'takeoff_tool.settings')
import django
django.setup()

from takeoff.services.extractors.vector_text_extractor import (
    VectorTextExtractor,
    VectorTextExtractionConfig,
    extract_text_with_coordinates,
    find_element_ids_in_pdf
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section_header(title: str):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80 + "\n")


def test_basic_extraction(file_path: str, output_dir: str):
    """
    Test basic text extraction with default configuration.
    
    Args:
        file_path: Path to PDF file
        output_dir: Directory to save results
    """
    print_section_header("TEST 1: Basic Extraction")
    
    extractor = VectorTextExtractor()
    result = extractor.extract_from_file(file_path)
    
    if result['success']:
        print(f"✅ Extraction successful!")
        print(f"   File: {result['file_path']}")
        print(f"   Total pages: {result['total_pages']}")
        print(f"   Total text instances: {result['statistics']['total_text_instances']}")
        print(f"   Average font size: {result['statistics']['average_font_size']:.2f}pt")
        print(f"   Extraction method: {result['statistics']['extraction_method']}")
        
        # Save full results to JSON
        output_file = os.path.join(output_dir, 'basic_extraction_results.json')
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n   📄 Full results saved to: {output_file}")
        
        return result
    else:
        print(f"❌ Extraction failed!")
        print(f"   Errors: {result['errors']}")
        return None


def test_element_matching(result: Dict[str, Any], element_ids: List[str], output_dir: str):
    """
    Test matching specific element IDs in the extracted text.
    
    Args:
        result: Extraction result from basic extraction
        element_ids: List of element IDs to find
        output_dir: Directory to save results
    """
    print_section_header("TEST 2: Element ID Matching")
    
    extractor = VectorTextExtractor()
    
    matches = {}
    for element_id in element_ids:
        found = extractor.find_text_instances(
            result,
            element_id,
            case_sensitive=False,
            exact_match=True
        )
        matches[element_id] = found
        
        print(f"Element '{element_id}': Found {len(found)} occurrences")
        
        # Show first 3 occurrences with coordinates
        for i, instance in enumerate(found[:3], 1):
            print(f"   [{i}] Page {instance['page_number']}, "
                  f"Position: ({instance['center']['x']:.1f}, {instance['center']['y']:.1f}), "
                  f"Font: {instance['font_size']:.1f}pt")
        
        if len(found) > 3:
            print(f"   ... and {len(found) - 3} more occurrences")
    
    # Save matches to JSON
    output_file = os.path.join(output_dir, 'element_matches.json')
    with open(output_file, 'w') as f:
        json.dump(matches, f, indent=2)
    print(f"\n📄 Element matches saved to: {output_file}")
    
    return matches


def test_page_specific_extraction(result: Dict[str, Any], page_number: int):
    """
    Test extracting text from a specific page.
    
    Args:
        result: Extraction result from basic extraction
        page_number: Page number to extract (1-indexed)
    """
    print_section_header(f"TEST 3: Page-Specific Extraction (Page {page_number})")
    
    extractor = VectorTextExtractor()
    page_instances = extractor.get_text_instances_by_page(result, page_number)
    
    print(f"Page {page_number} contains {len(page_instances)} text instances")
    
    # Group by font size to identify different text types
    font_groups = {}
    for ti in page_instances:
        font_size = round(ti['font_size'], 1)
        if font_size not in font_groups:
            font_groups[font_size] = []
        font_groups[font_size].append(ti)
    
    print(f"\nText grouped by font size:")
    for font_size in sorted(font_groups.keys(), reverse=True):
        instances = font_groups[font_size]
        print(f"   {font_size}pt: {len(instances)} instances")
        # Show sample text
        sample = ', '.join([ti['text'] for ti in instances[:5]])
        if len(instances) > 5:
            sample += f", ... (+{len(instances) - 5} more)"
        print(f"      Sample: {sample}")


def test_region_extraction(result: Dict[str, Any], page_number: int, output_dir: str):
    """
    Test extracting text from specific regions of a page.
    
    Args:
        result: Extraction result from basic extraction
        page_number: Page number (1-indexed)
        output_dir: Directory to save results
    """
    print_section_header(f"TEST 4: Region-Based Extraction (Page {page_number})")
    
    # Get page metadata to determine page size
    page_data = None
    for page in result['pages']:
        if page['page_metadata']['page_number'] == page_number:
            page_data = page
            break
    
    if not page_data:
        print(f"❌ Page {page_number} not found in results")
        return
    
    page_width = page_data['page_metadata']['width']
    page_height = page_data['page_metadata']['height']
    
    print(f"Page size: {page_width:.1f} × {page_height:.1f} points")
    
    # Define regions to test (title block, center, etc.)
    regions = {
        'title_block': {
            'x0': page_width * 0.6,
            'y0': page_height * 0.0,
            'x1': page_width * 1.0,
            'y1': page_height * 0.3
        },
        'center': {
            'x0': page_width * 0.3,
            'y0': page_height * 0.3,
            'x1': page_width * 0.7,
            'y1': page_height * 0.7
        },
        'bottom_left': {
            'x0': page_width * 0.0,
            'y0': page_height * 0.7,
            'x1': page_width * 0.3,
            'y1': page_height * 1.0
        }
    }
    
    extractor = VectorTextExtractor()
    region_results = {}
    
    for region_name, region in regions.items():
        instances = extractor.get_text_in_region(result, page_number, region)
        region_results[region_name] = instances
        
        print(f"\nRegion '{region_name}': Found {len(instances)} text instances")
        
        # Show sample text
        if instances:
            sample_texts = [ti['text'] for ti in instances[:5]]
            print(f"   Sample: {', '.join(sample_texts)}")
            if len(instances) > 5:
                print(f"   ... and {len(instances) - 5} more")
    
    # Save region results
    output_file = os.path.join(output_dir, f'region_extraction_page{page_number}.json')
    with open(output_file, 'w') as f:
        json.dump(region_results, f, indent=2)
    print(f"\n📄 Region results saved to: {output_file}")


def test_coordinate_systems(file_path: str, output_dir: str):
    """
    Test extraction with different coordinate systems.
    
    Args:
        file_path: Path to PDF file
        output_dir: Directory to save results
    """
    print_section_header("TEST 5: Coordinate System Comparison")
    
    # Extract with PDF coordinates (origin: bottom-left)
    config_pdf = VectorTextExtractionConfig(coordinate_system="pdf")
    extractor_pdf = VectorTextExtractor(config_pdf)
    result_pdf = extractor_pdf.extract_from_file(file_path)
    
    # Extract with image coordinates (origin: top-left)
    config_image = VectorTextExtractionConfig(coordinate_system="image")
    extractor_image = VectorTextExtractor(config_image)
    result_image = extractor_image.extract_from_file(file_path)
    
    # Compare coordinates for first page
    if result_pdf['success'] and result_image['success']:
        pdf_instances = result_pdf['pages'][0]['text_instances'][:3]
        image_instances = result_image['pages'][0]['text_instances'][:3]
        
        print("First 3 text instances - Coordinate comparison:")
        for i, (pdf_ti, img_ti) in enumerate(zip(pdf_instances, image_instances), 1):
            print(f"\n[{i}] Text: '{pdf_ti['text']}'")
            print(f"    PDF coords:   center=({pdf_ti['center']['x']:.1f}, {pdf_ti['center']['y']:.1f})")
            print(f"    Image coords: center=({img_ti['center']['x']:.1f}, {img_ti['center']['y']:.1f})")


def test_custom_configuration(file_path: str, output_dir: str):
    """
    Test extraction with custom configuration.
    
    Args:
        file_path: Path to PDF file
        output_dir: Directory to save results
    """
    print_section_header("TEST 6: Custom Configuration")
    
    # Custom config: only large text, no deduplication
    config = VectorTextExtractionConfig(
        min_text_length=2,
        include_font_info=True,
        include_color_info=True,
        deduplicate=False,  # Keep all instances including duplicates
        coordinate_system="pdf",
        page_numbers=[0]  # Only first page
    )
    
    extractor = VectorTextExtractor(config)
    result = extractor.extract_from_file(file_path)
    
    if result['success']:
        print("✅ Extraction with custom config successful!")
        print(f"   Pages extracted: {len(result['pages'])}")
        print(f"   Total instances: {result['statistics']['total_text_instances']}")
        print(f"   Configuration:")
        print(f"      - Min text length: {config.min_text_length}")
        print(f"      - Deduplication: {'Enabled' if config.deduplicate else 'Disabled'}")
        print(f"      - Coordinate system: {config.coordinate_system}")
        print(f"      - Page numbers: {config.page_numbers}")


def generate_overlay_data(matches: Dict[str, List[Dict[str, Any]]], output_dir: str):
    """
    Generate JSON data for frontend overlay visualization.
    
    Args:
        matches: Element matches from test_element_matching
        output_dir: Directory to save results
    """
    print_section_header("TEST 7: Generate Overlay Data for Frontend")
    
    # Transform matches into frontend-friendly format
    overlay_data = {
        'elements': [],
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'coordinate_system': 'pdf',
            'total_elements': len(matches)
        }
    }
    
    for element_id, occurrences in matches.items():
        element_data = {
            'element_id': element_id,
            'count': len(occurrences),
            'occurrences': []
        }
        
        for occ in occurrences:
            element_data['occurrences'].append({
                'page': occ['page_number'],
                'x': occ['center']['x'],
                'y': occ['center']['y'],
                'bbox': occ['bbox'],
                'font_size': occ['font_size'],
                'confidence': occ['confidence']
            })
        
        overlay_data['elements'].append(element_data)
    
    # Save overlay data
    output_file = os.path.join(output_dir, 'overlay_data.json')
    with open(output_file, 'w') as f:
        json.dump(overlay_data, f, indent=2)
    
    print(f"✅ Overlay data generated!")
    print(f"   Elements: {len(overlay_data['elements'])}")
    print(f"   Total occurrences: {sum(e['count'] for e in overlay_data['elements'])}")
    print(f"\n📄 Overlay data saved to: {output_file}")
    
    # Print summary
    print(f"\nSummary by element:")
    for elem in overlay_data['elements']:
        print(f"   {elem['element_id']}: {elem['count']} occurrences")


def run_all_tests(file_path: str, element_ids: List[str] = None):
    """
    Run all test scenarios.
    
    Args:
        file_path: Path to PDF file
        element_ids: List of element IDs to search for
    """
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        return
    
    # Create output directory
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'output',
        f'vector_extraction_{timestamp}'
    )
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n" + "🚀" * 40)
    print("   VECTOR TEXT EXTRACTOR - COMPREHENSIVE TEST SUITE")
    print("🚀" * 40)
    print(f"\nTest file: {file_path}")
    print(f"Output directory: {output_dir}")
    
    # Test 1: Basic extraction
    result = test_basic_extraction(file_path, output_dir)
    if not result:
        print("\n❌ Basic extraction failed. Stopping tests.")
        return
    
    # Test 2: Element matching (if element IDs provided)
    matches = None
    if element_ids:
        matches = test_element_matching(result, element_ids, output_dir)
    
    # Test 3: Page-specific extraction
    if result['total_pages'] > 0:
        test_page_specific_extraction(result, page_number=1)
    
    # Test 4: Region-based extraction
    if result['total_pages'] > 0:
        test_region_extraction(result, page_number=1, output_dir=output_dir)
    
    # Test 5: Coordinate systems
    test_coordinate_systems(file_path, output_dir)
    
    # Test 6: Custom configuration
    test_custom_configuration(file_path, output_dir)
    
    # Test 7: Generate overlay data (if we have matches)
    if matches:
        generate_overlay_data(matches, output_dir)
    
    print("\n" + "✅" * 40)
    print("   ALL TESTS COMPLETED")
    print("✅" * 40)
    print(f"\nAll results saved to: {output_dir}")


def main():
    """Main entry point for the test script"""
    # Default test file
    default_file = '/app/backend/rag_service/tests/7_FLETT_RD.pdf'
    
    parser = argparse.ArgumentParser(
        description='Test Vector Text Extractor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic extraction (uses default file: 7_FLETT_RD.pdf)
  python test_vector_text_extractor.py
  
  # Custom file
  python test_vector_text_extractor.py --file drawing.pdf
  
  # With element matching
  python test_vector_text_extractor.py --elements BP1,BP2,BP3,PF1,PF2,PF3
  
  # Specific page only
  python test_vector_text_extractor.py --page 1
        """
    )
    
    parser.add_argument(
        '--file',
        type=str,
        default=default_file,
        help=f'Path to PDF file (default: {default_file})'
    )
    
    parser.add_argument(
        '--elements',
        type=str,
        help='Comma-separated list of element IDs to find (e.g., BP1,BP2,BP3,PF1,PF2)'
    )
    
    parser.add_argument(
        '--page',
        type=int,
        help='Extract specific page only (1-indexed)'
    )
    
    args = parser.parse_args()
    
    # Parse element IDs
    element_ids = None
    if args.elements:
        element_ids = [e.strip() for e in args.elements.split(',')]
    
    # Run tests
    run_all_tests(args.file, element_ids)


if __name__ == '__main__':
    main()