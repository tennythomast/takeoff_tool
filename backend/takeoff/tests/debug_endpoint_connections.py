"""
Debug endpoint connections for BP1 symbols

Analyzes why tiny strokes aren't connecting into circles
"""

import fitz
import math
from collections import defaultdict

PDF_PATH = "/app/backend/rag_service/tests/7_FLETT_RD.pdf"

# Focus on one BP1 that's NOT working
bp_center = (762.7, 1360.0)  # BP1 Label #8
radius_mm = 17
radius_pt = radius_mm * 2.834645

print("="*80)
print(f"DEBUG: ENDPOINT CONNECTIONS FOR BP1 at ({bp_center[0]:.0f}, {bp_center[1]:.0f})")
print("="*80)

doc = fitz.open(PDF_PATH)
page = doc[0]
drawings = page.get_drawings()

# Extract tiny lines near this BP
tiny_lines = []
for idx, drawing in enumerate(drawings):
    items = drawing.get('items', [])
    
    if len(items) == 1 and items[0][0] == 'l':
        pt1, pt2 = items[0][1], items[0][2]
        length = math.sqrt((pt2.x - pt1.x)**2 + (pt2.y - pt1.y)**2)
        length_mm = length / 2.834645
        
        if 0.05 <= length_mm <= 2.0:
            line_center = ((pt1.x + pt2.x) / 2, (pt1.y + pt2.y) / 2)
            dist = math.sqrt(
                (line_center[0] - bp_center[0])**2 + 
                (line_center[1] - bp_center[1])**2
            )
            
            if dist <= radius_pt:
                tiny_lines.append({
                    'index': idx,
                    'x0': pt1.x,
                    'y0': pt1.y,
                    'x1': pt2.x,
                    'y1': pt2.y,
                    'length_mm': length_mm,
                    'distance_mm': dist / 2.834645
                })

print(f"\n📏 Found {len(tiny_lines)} tiny lines within {radius_mm}mm")

# Sort by distance
tiny_lines.sort(key=lambda x: x['distance_mm'])

# Show closest lines
print(f"\n🔍 Closest 20 lines:")
for i, line in enumerate(tiny_lines[:20], 1):
    print(f"   [{i:2d}] {line['distance_mm']:5.1f}mm away, {line['length_mm']:.3f}mm long, "
          f"({line['x0']:.1f},{line['y0']:.1f}) → ({line['x1']:.1f},{line['y1']:.1f})")

# Analyze endpoint distances
print(f"\n📊 Analyzing endpoint connections...")

# Test different precisions
precisions = [0.01, 0.05, 0.1, 0.2, 0.5]

for precision in precisions:
    print(f"\n  Precision: {precision}")
    
    # Build endpoint map
    endpoint_map = defaultdict(list)
    
    for i, line in enumerate(tiny_lines):
        start_key = (round(line['x0'] / precision) * precision,
                    round(line['y0'] / precision) * precision)
        endpoint_map[start_key].append({
            'line_idx': i,
            'type': 'start',
            'x': line['x0'],
            'y': line['y0']
        })
        
        end_key = (round(line['x1'] / precision) * precision,
                  round(line['y1'] / precision) * precision)
        endpoint_map[end_key].append({
            'line_idx': i,
            'type': 'end',
            'x': line['x1'],
            'y': line['y1']
        })
    
    # Count connections
    total_endpoints = len(tiny_lines) * 2
    connected_endpoints = sum(1 for endpoints in endpoint_map.values() if len(endpoints) >= 2)
    
    print(f"    Total endpoints: {total_endpoints}")
    print(f"    Unique buckets: {len(endpoint_map)}")
    print(f"    Connected buckets: {connected_endpoints}")
    print(f"    Connection rate: {connected_endpoints / len(endpoint_map) * 100:.1f}%")

# Check actual endpoint distances
print(f"\n🔬 Checking actual endpoint distances...")

# For each line, find the closest endpoint of another line
min_distances = []

for i, line1 in enumerate(tiny_lines):
    # Check end of line1 to start of other lines
    min_dist = float('inf')
    
    for j, line2 in enumerate(tiny_lines):
        if i == j:
            continue
        
        # Distance from line1 end to line2 start
        dist = math.sqrt(
            (line1['x1'] - line2['x0'])**2 + 
            (line1['y1'] - line2['y0'])**2
        )
        
        if dist < min_dist:
            min_dist = dist
    
    min_distances.append(min_dist)

# Statistics
min_distances.sort()
print(f"   Minimum endpoint gap: {min_distances[0]:.4f} points")
print(f"   Median endpoint gap: {min_distances[len(min_distances)//2]:.4f} points")
print(f"   Maximum endpoint gap: {min_distances[-1]:.4f} points")

print(f"\n   Gaps < 0.1pt: {sum(1 for d in min_distances if d < 0.1)}")
print(f"   Gaps < 0.3pt: {sum(1 for d in min_distances if d < 0.3)}")
print(f"   Gaps < 0.5pt: {sum(1 for d in min_distances if d < 0.5)}")
print(f"   Gaps < 1.0pt: {sum(1 for d in min_distances if d < 1.0)}")

print(f"\n💡 RECOMMENDATION:")
if min_distances[0] > 0.5:
    print(f"   ⚠️  Lines are NOT connected! Minimum gap is {min_distances[0]:.4f}pt")
    print(f"   These might not be stroke-based symbols.")
    print(f"   Check if they're actually separate line segments (not a symbol).")
elif min_distances[len(min_distances)//2] > 0.3:
    print(f"   ⚠️  Some lines connect, but many don't.")
    print(f"   Increase tolerance to ~{min_distances[len(min_distances)//2]:.2f}pt")
else:
    print(f"   ✅ Lines are well-connected with current tolerance (0.3pt)")
    print(f"   Issue might be in path-finding algorithm.")

doc.close()
