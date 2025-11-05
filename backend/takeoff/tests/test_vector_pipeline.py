"""
Vector Element Detection Pipeline

Focused on vector-based detection:
1. Text extraction from PDF vectors
2. Shape detection (rectangles, circles, polygons)
3. Symbol detection (tiny connected strokes)
4. Symbol-label association
5. Element occurrence generation

For RAG and LLM extraction, use test_rag_llm_extraction.py
"""

import os
import sys
import asyncio
import json
from datetime import datetime
from typing import Dict, Any

# Set up Django environment
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'takeoff_tool.settings')
import django
django.setup()

from takeoff.services.orchestration.vector import VectorElementPipeline, process_pdf_page
import fitz
import argparse

# Default configuration
DEFAULT_PDF = "/app/backend/rag_service/tests/7_FLETT_RD.pdf"


async def create_visualization(pdf_path: str, results) -> str:
    """
    Create visualization overlay on PDF showing detected elements
    
    Args:
        pdf_path: Path to original PDF
        results: PipelineResults object
        
    Returns:
        Path to visualization PDF
    """
    doc = fitz.open(pdf_path)
    page = doc[0]
    
    # Color scheme
    colors = {
        'rectangle': (0, 0.8, 0),      # Green
        'square': (0, 0.6, 0),         # Dark green
        'circle': (0, 0, 1),           # Blue
        'polygon': (1, 0.5, 0),        # Orange
        'symbol': (1, 0, 0),           # Red
        'text_with_symbol': (1, 0, 0), # Red
        'text_no_symbol': (0.5, 0.5, 0.5)  # Gray
    }
    
    # Draw shapes
    print(f"      Drawing {len(results.shapes['rectangles'])} rectangles...")
    for i, rect in enumerate(results.shapes['rectangles'], 1):
        bbox = rect['bbox']
        if isinstance(bbox, (list, tuple)):
            bbox = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
        
        color = colors['square'] if rect['type'] == 'square' else colors['rectangle']
        page.draw_rect(bbox, color=color, width=2)
        
        # Add small label
        label = f"R{i}"
        page.insert_text(
            (bbox[0], bbox[1] - 2),
            label,
            fontsize=6,
            color=color
        )
    
    print(f"      Drawing {len(results.shapes['circles'])} circles...")
    for i, circle in enumerate(results.shapes['circles'], 1):
        center = circle['center']
        if isinstance(center, (list, tuple)):
            center = fitz.Point(center[0], center[1])
        
        page.draw_circle(
            center,
            circle['radius_mm'] * 2.834645,
            color=colors['circle'],
            width=2
        )
        
        # Add small label
        label = f"C{i}"
        page.insert_text(
            (center.x + 5, center.y),
            label,
            fontsize=6,
            color=colors['circle']
        )
    
    print(f"      Drawing {len(results.shapes['polygons'])} polygons...")
    for i, poly in enumerate(results.shapes['polygons'], 1):
        bbox = poly['bbox']
        if isinstance(bbox, (list, tuple)):
            bbox = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
        
        page.draw_rect(bbox, color=colors['polygon'], width=2)
        
        label = f"P{i}"
        page.insert_text(
            (bbox[0], bbox[1] - 2),
            label,
            fontsize=6,
            color=colors['polygon']
        )
    
    # Draw element occurrences
    print(f"      Drawing {len(results.element_occurrences)} element occurrences...")
    
    # Group by whether they have symbols
    with_symbols = [occ for occ in results.element_occurrences if occ.symbol]
    without_symbols = [occ for occ in results.element_occurrences if not occ.symbol]
    
    # Draw occurrences with symbols (highlight these)
    for occ in with_symbols:
        # Draw text bbox
        text_bbox = occ.text_bbox
        bbox = fitz.Rect(text_bbox[0], text_bbox[1], text_bbox[2], text_bbox[3])
        page.draw_rect(bbox, color=colors['text_with_symbol'], width=1.5)
        
        # Draw symbol bbox if available
        if occ.symbol and 'bbox' in occ.symbol:
            symbol_bbox = occ.symbol['bbox']
            if isinstance(symbol_bbox, (list, tuple)):
                symbol_bbox = fitz.Rect(symbol_bbox[0], symbol_bbox[1], symbol_bbox[2], symbol_bbox[3])
            page.draw_rect(symbol_bbox, color=colors['symbol'], width=2, dashes="[2 2]")
            
            # Draw line connecting text to symbol
            text_center = occ.text_center
            symbol_center = occ.symbol['center']
            page.draw_line(
                fitz.Point(text_center[0], text_center[1]),
                fitz.Point(symbol_center[0], symbol_center[1]),
                color=colors['symbol'],
                width=0.5,
                dashes="[1 1]"
            )
    
    # Add legend
    legend_x = page.rect.width - 300
    legend_y = 50
    
    page.draw_rect(
        fitz.Rect(legend_x - 10, legend_y - 10, legend_x + 290, legend_y + 280),
        color=(0, 0, 0),
        width=1,
        fill=(1, 1, 1)
    )
    
    page.insert_text((legend_x, legend_y), "VECTOR PIPELINE RESULTS", 
                    fontsize=12, color=(0, 0, 0))
    
    y = legend_y + 25
    
    # Statistics
    stats = results.statistics
    page.insert_text((legend_x, y), f"Text Elements: {stats['total_text_elements']}", 
                    fontsize=9, color=(0, 0, 0))
    y += 15
    
    page.insert_text((legend_x, y), f"Shapes: {stats['total_shapes']}", 
                    fontsize=9, color=(0, 0, 0))
    y += 12
    page.insert_text((legend_x + 10, y), f"Rectangles: {stats['rectangles']}", 
                    fontsize=8, color=colors['rectangle'])
    y += 12
    page.insert_text((legend_x + 10, y), f"Circles: {stats['circles']}", 
                    fontsize=8, color=colors['circle'])
    y += 12
    page.insert_text((legend_x + 10, y), f"Polygons: {stats['polygons']}", 
                    fontsize=8, color=colors['polygon'])
    y += 20
    
    page.insert_text((legend_x, y), f"Symbols: {stats['symbols_detected']}", 
                    fontsize=9, color=colors['symbol'])
    y += 20
    
    page.insert_text((legend_x, y), f"Element Occurrences: {stats['element_occurrences']}", 
                    fontsize=9, color=(0, 0, 0))
    y += 12
    page.insert_text((legend_x + 10, y), f"With symbols: {stats['occurrences_with_symbols']}", 
                    fontsize=8, color=colors['text_with_symbol'])
    y += 12
    page.insert_text((legend_x + 10, y), f"Without symbols: {stats['occurrences_without_symbols']}", 
                    fontsize=8, color=colors['text_no_symbol'])
    y += 20
    
    page.insert_text((legend_x, y), f"Unique Elements: {stats['unique_elements']}", 
                    fontsize=9, color=(0, 0, 0))
    y += 25
    
    # Legend items
    page.insert_text((legend_x, y), "Legend:", 
                    fontsize=9, color=(0, 0, 0))
    y += 15
    
    # Rectangle
    page.draw_rect(fitz.Rect(legend_x + 5, y - 8, legend_x + 25, y + 2), 
                  color=colors['rectangle'], width=2)
    page.insert_text((legend_x + 30, y), "Rectangle", 
                    fontsize=8, color=(0, 0, 0))
    y += 15
    
    # Circle
    page.draw_circle((legend_x + 15, y - 3), 8, color=colors['circle'], width=2)
    page.insert_text((legend_x + 30, y), "Circle", 
                    fontsize=8, color=(0, 0, 0))
    y += 15
    
    # Symbol
    page.draw_rect(fitz.Rect(legend_x + 5, y - 8, legend_x + 25, y + 2), 
                  color=colors['symbol'], width=2, dashes="[2 2]")
    page.insert_text((legend_x + 30, y), "Symbol", 
                    fontsize=8, color=(0, 0, 0))
    y += 15
    
    # Text with symbol
    page.draw_rect(fitz.Rect(legend_x + 5, y - 8, legend_x + 25, y + 2), 
                  color=colors['text_with_symbol'], width=1.5)
    page.insert_text((legend_x + 30, y), "Text with symbol", 
                    fontsize=8, color=(0, 0, 0))
    y += 15
    
    # Connection line
    page.draw_line(
        fitz.Point(legend_x + 5, y - 3),
        fitz.Point(legend_x + 25, y - 3),
        color=colors['symbol'],
        width=0.5,
        dashes="[1 1]"
    )
    page.insert_text((legend_x + 30, y), "Symbol connection", 
                    fontsize=8, color=(0, 0, 0))
    
    # Save
    doc.save(VIZ_OUTPUT_PATH)
    doc.close()
    
    return VIZ_OUTPUT_PATH


async def main(pdf_path: str, output_dir: str):
    """
    Run the vector element detection pipeline
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save output files
    """
    # Generate output filenames
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_json = os.path.join(output_dir, f"{pdf_name}_vector_results.json")
    output_viz = os.path.join(output_dir, f"{pdf_name}_vector_visualization.pdf")
    
    print("="*80)
    print("VECTOR ELEMENT DETECTION PIPELINE")
    print("="*80)
    print(f"\nPDF: {pdf_path}")
    print(f"Output directory: {output_dir}")
    print(f"\nNote: For RAG and LLM extraction, use test_rag_llm_extraction.py")
    
    # Initialize vector pipeline
    print(f"\n[PROCESSING] Initializing pipeline...")
    pipeline = VectorElementPipeline(
        symbol_search_radius_mm=17.0,
        min_shape_size_mm=3.0,
        max_shape_size_mm=150.0
    )
    
    # Process page
    print(f"   Detecting elements...")
    results = await pipeline.process_page(pdf_path, page_number=0)
    
    # Display results
    print(f"\n{'='*80}")
    print("PIPELINE RESULTS")
    print(f"{'='*80}")
    
    stats = results.statistics
    
    print(f"\n📄 Page {results.page_number}")
    print(f"\n📝 Text Extraction:")
    print(f"   Total text elements: {stats['total_text_elements']}")
    
    print(f"\n📐 Shape Detection:")
    print(f"   Total shapes: {stats['total_shapes']}")
    print(f"   Rectangles: {stats['rectangles']} ({stats['squares']} squares)")
    print(f"   Circles: {stats['circles']}")
    print(f"   Polygons: {stats['polygons']}")
    
    print(f"\n🎯 Symbol Detection:")
    print(f"   Symbols found: {stats['symbols_detected']}")
    
    print(f"\n🔗 Element Occurrences:")
    print(f"   Total occurrences: {stats['element_occurrences']}")
    print(f"   With symbols: {stats['occurrences_with_symbols']}")
    print(f"   Without symbols: {stats['occurrences_without_symbols']}")
    print(f"   Unique elements: {stats['unique_elements']}")
    
    # Show element counts
    if stats['element_counts']:
        print(f"\n📊 Element Counts:")
        for element_name, count in sorted(stats['element_counts'].items()):
            print(f"   {element_name}: {count} occurrence(s)")
    
    # Show sample occurrences
    print(f"\n📋 Sample Element Occurrences:")
    for i, occ in enumerate(results.element_occurrences[:10], 1):
        symbol_info = ""
        if occ.symbol:
            symbol_info = f" → {occ.symbol_type} symbol ({occ.symbol_size_mm:.1f}mm, {occ.distance_to_symbol_mm:.1f}mm away)"
        else:
            symbol_info = " → No symbol detected"
        
        print(f"   [{i}] {occ.element_name}{symbol_info}")
    
    if len(results.element_occurrences) > 10:
        print(f"   ... and {len(results.element_occurrences) - 10} more")
    
    # Filter examples
    print(f"\n🔍 Filtering Examples:")
    
    # Filter for BP elements only
    bp_occurrences = pipeline.filter_element_occurrences(
        results.element_occurrences,
        element_names=['BP1', 'BP3']
    )
    print(f"   BP elements only: {len(bp_occurrences)} occurrences")
    
    # Filter for high confidence with symbols
    high_conf_with_symbols = pipeline.filter_element_occurrences(
        results.element_occurrences,
        min_confidence=0.9,
        require_symbol=True
    )
    print(f"   High confidence with symbols: {len(high_conf_with_symbols)} occurrences")
    
    # Group by element
    grouped = pipeline.group_occurrences_by_element(results.element_occurrences)
    print(f"\n📦 Grouped by Element:")
    for element_name, occs in sorted(grouped.items())[:5]:
        print(f"   {element_name}: {len(occs)} occurrence(s)")
    
    # Save results
    print(f"\n💾 Saving results to: {output_json}")
    with open(output_json, 'w') as f:
        json.dump(results.to_dict(), f, indent=2)
    
    # Create visualization
    print(f"\n[VISUALIZATION] Creating overlay visualization...")
    # Temporarily set global variable for visualization function
    global VIZ_OUTPUT_PATH
    VIZ_OUTPUT_PATH = output_viz
    viz_path = await create_visualization(pdf_path, results)
    print(f"   ✅ Visualization saved to: {viz_path}")
    
    print(f"\n{'='*80}")
    print("✅ PIPELINE TEST COMPLETE!")
    print(f"{'='*80}")
    
    print(f"""
Summary:
- Extracted {stats['total_text_elements']} text elements
- Detected {stats['total_shapes']} shapes
- Found {stats['symbols_detected']} symbols near labels
- Created {stats['element_occurrences']} element occurrences
- Identified {stats['unique_elements']} unique elements

The pipeline successfully:
1. ✅ Extracted text with positions
2. ✅ Detected geometric shapes (rectangles, circles, polygons)
3. ✅ Found symbols near text labels
4. ✅ Associated symbols with labels
5. ✅ Generated structured element occurrences
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Vector Element Detection Pipeline Test',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test on default PDF (7_FLETT_RD.pdf)
  python test_vector_pipeline.py
  
  # Test on specific PDF
  python test_vector_pipeline.py --pdf /app/backend/rag_service/tests/gwynne1.pdf
  
  # Test with custom output directory
  python test_vector_pipeline.py --pdf gwynne1.pdf --output /app/backend/takeoff/tests/output/gwynne
        """
    )
    
    parser.add_argument(
        '--pdf',
        type=str,
        default=DEFAULT_PDF,
        help=f'Path to PDF file (default: {DEFAULT_PDF})'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='/app/backend/takeoff/tests/output',
        help='Output directory for results (default: /app/backend/takeoff/tests/output)'
    )
    
    parser.add_argument(
        '--page',
        type=int,
        default=0,
        help='Page number to process (0-indexed, default: 0)'
    )
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    # Run pipeline
    asyncio.run(main(args.pdf, args.output))
