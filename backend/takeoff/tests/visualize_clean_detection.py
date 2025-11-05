"""
Visualize detected shapes using the clean detection modules

Overlays all detected shapes on the PDF:
- Rectangles (green)
- Circles (blue)
- Polygons (orange)
- Symbols near labels (red)
"""

import sys
sys.path.insert(0, '/app/backend/takeoff/services/measurement/vector')

from shape_detector import ShapeDetector, ShapeClassifier
import fitz

# Configuration
PDF_PATH = "/app/backend/rag_service/tests/7_FLETT_RD.pdf"
OUTPUT_PATH = "/app/backend/takeoff/tests/output/clean_shapes_visualized.pdf"

print("="*80)
print("SHAPE VISUALIZATION - CLEAN MODULES")
print("="*80)

# Open PDF
doc = fitz.open(PDF_PATH)
page = doc[0]

# Detect shapes
print("\n[1/3] Detecting shapes...")
detector = ShapeDetector()
shapes = detector.detect_all_shapes(page)

print(f"   Rectangles: {len(shapes['rectangles'])}")
print(f"   Circles: {len(shapes['circles'])}")
print(f"   Polygons: {len(shapes['polygons'])}")
print(f"   Total: {shapes['total_shapes']}")

# Detect symbols near BP labels
print("\n[2/3] Detecting symbols near labels...")
bp_labels = [
    (538.3, 708.0),
    (912.0, 708.0),
    (1090.5, 711.8),
    (1809.6, 711.3),
    (1568.9, 710.4),
    (1329.3, 711.8),
    (1853.5, 1362.0),
    (1607.0, 1360.0),
    (1367.3, 1360.0),
    (1127.5, 1360.1),
    (944.6, 1360.0),
    (761.7, 1360.0),
]

symbols = detector.detect_symbols_near_labels(page, bp_labels, radius_mm=17.0)
print(f"   Symbols found: {len(symbols)}")

# Visualize
print("\n[3/3] Creating visualization...")

# Color scheme
colors = {
    'rectangle': (0, 0.8, 0),      # Green
    'square': (0, 0.6, 0),         # Dark green
    'circle': (0, 0, 1),           # Blue
    'polygon': (1, 0.5, 0),        # Orange
    'symbol': (1, 0, 0)            # Red
}

# Draw rectangles
print(f"   Drawing {len(shapes['rectangles'])} rectangles...")
for i, rect in enumerate(shapes['rectangles'], 1):
    bbox = fitz.Rect(rect['bbox'][0], rect['bbox'][1], rect['bbox'][2], rect['bbox'][3])
    
    # Choose color
    color = colors['square'] if rect['type'] == 'square' else colors['rectangle']
    
    # Draw outline
    page.draw_rect(bbox, color=color, width=3)
    
    # Add label
    shape_symbol = "■" if rect['type'] == 'square' else "▭"
    label = f"{shape_symbol}{i}\n{rect['width_mm']:.0f}×{rect['height_mm']:.0f}mm"
    
    # Position label
    label_y = bbox.y0 - 5
    if label_y < 20:
        label_y = bbox.y1 + 15
    
    page.insert_text(
        (bbox.x0, label_y),
        label,
        fontsize=8,
        color=color
    )

# Draw circles
print(f"   Drawing {len(shapes['circles'])} circles...")
for i, circle in enumerate(shapes['circles'], 1):
    # Draw circle outline
    page.draw_circle(
        circle['center'],
        circle['radius_mm'] * 2.834645,  # Convert mm to points
        color=colors['circle'],
        width=3
    )
    
    # Add label
    label = f"○{i}\nØ{circle['diameter_mm']:.0f}mm"
    
    # Position label to the right
    label_x = circle['center'][0] + circle['radius_mm'] * 2.834645 + 5
    label_y = circle['center'][1] + 5
    
    page.insert_text(
        (label_x, label_y),
        label,
        fontsize=8,
        color=colors['circle']
    )

# Draw polygons
print(f"   Drawing {len(shapes['polygons'])} polygons...")
for i, poly in enumerate(shapes['polygons'], 1):
    bbox = fitz.Rect(poly['bbox'][0], poly['bbox'][1], poly['bbox'][2], poly['bbox'][3])
    
    # Draw outline
    page.draw_rect(bbox, color=colors['polygon'], width=3)
    
    # Add label
    label = f"⬡{i}\n{poly['segments']} sides"
    
    label_y = bbox.y0 - 5
    if label_y < 20:
        label_y = bbox.y1 + 15
    
    page.insert_text(
        (bbox.x0, label_y),
        label,
        fontsize=8,
        color=colors['polygon']
    )

# Draw symbols
print(f"   Drawing {len(symbols)} symbols...")
for i, symbol in enumerate(symbols, 1):
    bbox = fitz.Rect(symbol['bbox'][0], symbol['bbox'][1], symbol['bbox'][2], symbol['bbox'][3])
    
    # Draw outline
    page.draw_rect(bbox, color=colors['symbol'], width=2, dashes="[2 2]")
    
    # Draw center point
    page.draw_circle(symbol['center'], 2, color=colors['symbol'], fill=colors['symbol'])
    
    # Add label
    label = f"⊗{i}\n{symbol['segments']}seg"
    
    label_x = bbox.x1 + 5
    label_y = symbol['center'][1] + 5
    
    page.insert_text(
        (label_x, label_y),
        label,
        fontsize=7,
        color=colors['symbol']
    )

# Add legend
legend_x = page.rect.width - 280
legend_y = 50

page.draw_rect(
    fitz.Rect(legend_x - 10, legend_y - 10, legend_x + 270, legend_y + 200),
    color=(0, 0, 0),
    width=1,
    fill=(1, 1, 1)
)

page.insert_text((legend_x, legend_y), "DETECTED SHAPES", 
                fontsize=12, color=(0, 0, 0))

y = legend_y + 25

# Statistics
categories = ShapeClassifier.categorize_by_type(shapes)

page.insert_text((legend_x, y), f"Total Shapes: {shapes['total_shapes']}", 
                fontsize=10, color=(0, 0, 0))
y += 20

page.insert_text((legend_x, y), f"Rectangles: {len(shapes['rectangles'])}", 
                fontsize=9, color=colors['rectangle'])
y += 12
page.insert_text((legend_x + 10, y), f"Squares: {categories['squares']}", 
                fontsize=8, color=colors['square'])
y += 12
page.insert_text((legend_x + 10, y), f"Rectangles: {categories['rectangles']}", 
                fontsize=8, color=colors['rectangle'])
y += 20

page.insert_text((legend_x, y), f"Circles: {len(shapes['circles'])}", 
                fontsize=9, color=colors['circle'])
y += 20

page.insert_text((legend_x, y), f"Polygons: {len(shapes['polygons'])}", 
                fontsize=9, color=colors['polygon'])
y += 20

page.insert_text((legend_x, y), f"Symbols: {len(symbols)}", 
                fontsize=9, color=colors['symbol'])
y += 25

# Legend items
page.insert_text((legend_x, y), "Legend:", 
                fontsize=9, color=(0, 0, 0))
y += 15

# Rectangle
page.draw_rect(fitz.Rect(legend_x + 5, y - 8, legend_x + 25, y + 2), 
              color=colors['rectangle'], width=3)
page.insert_text((legend_x + 30, y), "Rectangle", 
                fontsize=8, color=(0, 0, 0))
y += 15

# Square
page.draw_rect(fitz.Rect(legend_x + 5, y - 8, legend_x + 25, y + 2), 
              color=colors['square'], width=3)
page.insert_text((legend_x + 30, y), "Square", 
                fontsize=8, color=(0, 0, 0))
y += 15

# Circle
page.draw_circle((legend_x + 15, y - 3), 8, color=colors['circle'], width=3)
page.insert_text((legend_x + 30, y), "Circle", 
                fontsize=8, color=(0, 0, 0))
y += 15

# Polygon
page.draw_rect(fitz.Rect(legend_x + 5, y - 8, legend_x + 25, y + 2), 
              color=colors['polygon'], width=3)
page.insert_text((legend_x + 30, y), "Polygon", 
                fontsize=8, color=(0, 0, 0))
y += 15

# Symbol
page.draw_rect(fitz.Rect(legend_x + 5, y - 8, legend_x + 25, y + 2), 
              color=colors['symbol'], width=2, dashes="[2 2]")
page.insert_text((legend_x + 30, y), "Symbol (tiny strokes)", 
                fontsize=8, color=(0, 0, 0))

# Save
doc.save(OUTPUT_PATH)
doc.close()

print(f"\n{'='*80}")
print(f"✅ Visualization saved to: {OUTPUT_PATH}")
print(f"{'='*80}")

print(f"\n📊 SUMMARY:")
print(f"   Rectangles: {len(shapes['rectangles'])} ({categories['squares']} squares, {categories['rectangles']} rectangles)")
print(f"   Circles: {len(shapes['circles'])}")
print(f"   Polygons: {len(shapes['polygons'])}")
print(f"   Symbols: {len(symbols)}")
print(f"   Total: {shapes['total_shapes']} shapes + {len(symbols)} symbols")
print(f"\n✅ All shapes visualized with color-coded overlays and labels!")
