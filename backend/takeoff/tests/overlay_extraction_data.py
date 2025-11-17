"""
Overlay Vector Extraction Data on PDF

Reads overlay_data.json and annotates the PDF with all extracted information
"""

import json
import fitz  # PyMuPDF
import sys
import os


def overlay_extraction_data(pdf_path: str, overlay_json: str, output_path: str = None):
    """
    Overlay extraction data from overlay_data.json onto PDF
    
    Args:
        pdf_path: Path to original PDF
        overlay_json: Path to overlay_data.json
        output_path: Where to save annotated PDF
    """
    
    if output_path is None:
        output_path = pdf_path.replace('.pdf', '_overlay_annotated.pdf')
    
    # Load overlay data
    print(f"📂 Loading overlay data from: {overlay_json}")
    with open(overlay_json, 'r') as f:
        data = json.load(f)
    
    # Open PDF
    print(f"📄 Opening PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    
    print(f"\n📊 Overlay Data Structure:")
    print(f"   Keys: {list(data.keys())}")
    
    # Color scheme
    colors = {
        'text': (0, 0, 1),          # Blue
        'shape': (0, 1, 0),         # Green
        'circle': (0, 0.8, 0),      # Dark Green
        'rectangle': (0, 0.5, 0.8), # Cyan
        'polygon': (0.8, 0, 0.8),   # Purple
        'element': (1, 0.5, 0),     # Orange
        'label': (0.5, 0, 0)        # Dark Red
    }
    
    # Get elements from overlay data
    elements = data.get('elements', [])
    metadata = data.get('metadata', {})
    
    print(f"   Total elements: {metadata.get('total_elements', len(elements))}")
    print(f"   Generated at: {metadata.get('generated_at', 'unknown')}")
    
    # Group occurrences by page
    page_occurrences = {}
    for element in elements:
        element_id = element.get('element_id', 'unknown')
        occurrences = element.get('occurrences', [])
        
        for occurrence in occurrences:
            page_num = occurrence.get('page', 1)
            if page_num not in page_occurrences:
                page_occurrences[page_num] = []
            
            page_occurrences[page_num].append({
                'element_id': element_id,
                'bbox': occurrence.get('bbox', {}),
                'x': occurrence.get('x', 0),
                'y': occurrence.get('y', 0),
                'font_size': occurrence.get('font_size', 0),
                'confidence': occurrence.get('confidence', 1.0)
            })
    
    # Process each page
    for page_num in sorted(page_occurrences.keys()):
        page_idx = page_num - 1
        
        if page_idx >= len(doc):
            print(f"⚠️  Skipping page {page_num} (not in PDF)")
            continue
            
        page = doc[page_idx]
        
        print(f"\n{'='*80}")
        print(f"📄 PAGE {page_num}")
        print(f"{'='*80}")
        
        occurrences = page_occurrences[page_num]
        print(f"   Element occurrences: {len(occurrences)}")
        
        # Draw each element occurrence
        print(f"\n   Drawing {len(occurrences)} element occurrences...")
        
        element_counts = {}
        
        for i, occurrence in enumerate(occurrences, 1):
            bbox = occurrence.get('bbox', {})
            if not bbox:
                continue
            
            element_id = occurrence.get('element_id', 'unknown')
            
            # Count occurrences per element
            if element_id not in element_counts:
                element_counts[element_id] = 0
            element_counts[element_id] += 1
            
            # Create rectangle
            rect = fitz.Rect(
                bbox.get('x0', 0), 
                bbox.get('y0', 0),
                bbox.get('x1', 0), 
                bbox.get('y1', 0)
            )
            
            # Draw element box with thick dashed line
            page.draw_rect(rect, color=colors['element'], width=3, dashes=[5, 3])
            
            # Draw center point
            center_x = occurrence.get('x', (rect.x0 + rect.x1) / 2)
            center_y = occurrence.get('y', (rect.y0 + rect.y1) / 2)
            page.draw_circle((center_x, center_y), 3, color=colors['element'], fill=colors['element'])
            
            # Add label with element ID
            confidence = occurrence.get('confidence', 1.0)
            label = f"{element_id}"
            
            # Position label above the box
            label_y = rect.y0 - 5
            if label_y < 20:  # If too close to top, put below
                label_y = rect.y1 + 12
            
            page.insert_text(
                (rect.x0, label_y),
                label,
                fontsize=10,
                color=colors['element']
            )
            
            # Add confidence if less than 1.0
            if confidence < 1.0:
                conf_label = f"({confidence:.0%})"
                page.insert_text(
                    (rect.x1 + 2, label_y),
                    conf_label,
                    fontsize=7,
                    color=colors['label']
                )
            
            print(f"      [{i:2d}] {element_id} at ({center_x:.0f}, {center_y:.0f}), "
                  f"bbox: {rect.width:.0f}x{rect.height:.0f}pt, conf: {confidence:.0%}")
        
        # Print summary
        print(f"\n   Element Summary:")
        for elem_id, count in sorted(element_counts.items()):
            print(f"      {elem_id}: {count} occurrence(s)")
        
        # Add legend
        add_legend(page, colors, len(occurrences), element_counts)
    
    # Save
    doc.save(output_path)
    doc.close()
    
    print(f"\n{'='*80}")
    print(f"✅ Annotated PDF saved to: {output_path}")
    print(f"{'='*80}\n")
    
    return output_path


def add_legend(page, colors, total_occurrences, element_counts):
    """Add legend to page"""
    
    legend_x = page.rect.width - 220
    legend_y = 50
    
    # Calculate height based on number of elements
    legend_height = 80 + (len(element_counts) * 15)
    
    # Background
    page.draw_rect(
        fitz.Rect(legend_x - 10, legend_y - 10, legend_x + 210, legend_y + legend_height),
        color=(0, 0, 0),
        width=1,
        fill=(1, 1, 1)
    )
    
    # Title
    page.insert_text((legend_x, legend_y), "ELEMENT OVERLAY", 
                    fontsize=11, color=(0, 0, 0))
    
    y = legend_y + 20
    
    # Total occurrences
    page.insert_text((legend_x, y), f"Total Occurrences: {total_occurrences}", 
                    fontsize=9, color=(0, 0, 0))
    y += 20
    
    # Element breakdown
    page.insert_text((legend_x, y), "Elements Detected:", 
                    fontsize=9, color=(0, 0, 0))
    y += 15
    
    for elem_id, count in sorted(element_counts.items()):
        # Draw sample box
        page.draw_rect(fitz.Rect(legend_x + 5, y - 8, legend_x + 20, y + 2), 
                      color=colors['element'], width=2, dashes=[5, 3])
        
        # Element info
        page.insert_text((legend_x + 25, y), f"{elem_id}: {count}x", 
                        fontsize=8, color=colors['element'])
        y += 15
    
    # Legend explanation
    y += 5
    page.insert_text((legend_x, y), "Legend:", 
                    fontsize=8, color=(0, 0, 0))
    y += 12
    
    page.draw_rect(fitz.Rect(legend_x + 5, y - 8, legend_x + 20, y + 2), 
                  color=colors['element'], width=3, dashes=[5, 3])
    page.insert_text((legend_x + 25, y), "Element bbox", 
                    fontsize=7, color=(0, 0, 0))
    y += 12
    
    page.draw_circle((legend_x + 12, y - 3), 3, color=colors['element'], fill=colors['element'])
    page.insert_text((legend_x + 25, y), "Element center", 
                    fontsize=7, color=(0, 0, 0))


def main():
    """Main entry point"""
    
    # Default paths
    overlay_json = '/Users/tennythomas/Documents/Start Up/Takeoff_arcana/takeoff_tool/backend/takeoff/tests/output/vector_extraction_20251102_092836/overlay_data.json'
    pdf_path = '/Users/tennythomas/Documents/Start Up/Takeoff_arcana/takeoff_tool/backend/rag_service/tests/7_FLETT_RD.pdf'
    output_path = '/Users/tennythomas/Documents/Start Up/Takeoff_arcana/takeoff_tool/backend/takeoff/tests/output/7_FLETT_RD_overlay_annotated.pdf'
    
    # Command line overrides
    if len(sys.argv) > 1:
        overlay_json = sys.argv[1]
    if len(sys.argv) > 2:
        pdf_path = sys.argv[2]
    if len(sys.argv) > 3:
        output_path = sys.argv[3]
    
    print("="*80)
    print("🎨 OVERLAY EXTRACTION DATA VISUALIZATION")
    print("="*80 + "\n")
    
    # Check if files exist
    if not os.path.exists(overlay_json):
        print(f"❌ Overlay JSON not found: {overlay_json}")
        return
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return
    
    # Create visualization
    result = overlay_extraction_data(pdf_path, overlay_json, output_path)
    
    print(f"🎨 Visualization complete!")
    print(f"📥 Open the annotated PDF: {result}")


if __name__ == '__main__':
    main()
