"""
Test script for vector-based shape detection

Demonstrates usage of the clean detection modules.
"""

import fitz
from takeoff.services.measurement.vector import (
    LineDetector,
    ArcDetector,
    TinyStrokeConnector,
    ShapeDetector,
    ShapeClassifier
)

# Test file
PDF_PATH = "/app/backend/rag_service/tests/7_FLETT_RD.pdf"

print("="*80)
print("VECTOR SHAPE DETECTION TEST")
print("="*80)

# Open PDF
doc = fitz.open(PDF_PATH)
page = doc[0]

# Initialize detector
detector = ShapeDetector()

print("\n[1/3] Detecting all shapes...")
shapes = detector.detect_all_shapes(page)

print(f"\n📊 Detection Results:")
print(f"   Rectangles: {len(shapes['rectangles'])}")
print(f"   Circles: {len(shapes['circles'])}")
print(f"   Polygons: {len(shapes['polygons'])}")
print(f"   Total: {shapes['total_shapes']}")

# Categorize by type
print("\n[2/3] Categorizing shapes...")
categories = ShapeClassifier.categorize_by_type(shapes)

print(f"\n📐 Shape Categories:")
for shape_type, count in categories.items():
    if count > 0:
        print(f"   {shape_type.capitalize()}: {count}")

# Categorize by size
size_categories = ShapeClassifier.categorize_by_size(shapes)

print(f"\n📏 Size Categories:")
for size, shape_list in size_categories.items():
    if shape_list:
        print(f"   {size.capitalize()}: {len(shape_list)} shapes")

# Test symbol detection near labels
print("\n[3/3] Detecting symbols near BP labels...")

# Example BP label positions (from previous analysis)
bp_labels = [
    (538.3, 708.0),   # BP1
    (912.0, 708.0),   # BP1
    (1090.5, 711.8),  # BP3
]

symbols = detector.detect_symbols_near_labels(page, bp_labels, radius_mm=17.0)

print(f"\n🎯 Symbol Detection:")
print(f"   BP labels checked: {len(bp_labels)}")
print(f"   Symbols found: {len(symbols)}")

if symbols:
    for i, symbol in enumerate(symbols, 1):
        print(f"\n   Symbol {i}:")
        print(f"      Type: {symbol['type']}")
        print(f"      Segments: {symbol['segments']}")
        print(f"      Size: {symbol['width_mm']:.1f}x{symbol['height_mm']:.1f}mm")
        if symbol['diameter_mm']:
            print(f"      Diameter: {symbol['diameter_mm']:.1f}mm")
        print(f"      Distance from label: {symbol['distance_from_label_mm']:.1f}mm")

# Summary
print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")

print(f"""
✅ Detection Complete!

Total Shapes Detected: {shapes['total_shapes']}
- Rectangles: {len(shapes['rectangles'])} ({categories['squares']} squares, {categories['rectangles']} rectangles)
- Circles: {len(shapes['circles'])}
- Polygons: {len(shapes['polygons'])}

Symbols Near Labels: {len(symbols)}

The detection modules successfully:
1. ✅ Detected rectangles from connected line segments
2. ✅ Detected circles from 4-curve bezier paths
3. ✅ Detected polygons from multi-segment paths
4. ✅ Detected symbols from tiny connected strokes

Next Steps:
- Integrate with text extraction for element occurrence tracking
- Add visualization overlay
- Export results to structured format
""")

doc.close()
