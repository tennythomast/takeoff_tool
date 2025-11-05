"""
Debug script to find missing BP1 symbols

Investigates why some BP1 labels don't have associated symbols detected.
Tests different size thresholds and search radii.
"""

import fitz
import math
from collections import defaultdict

PDF_PATH = "/app/backend/rag_service/tests/7_FLETT_RD.pdf"

print("="*80)
print("DEBUG: MISSING BP1 SYMBOLS")
print("="*80)

# All BP1 label positions from the JSON
bp1_labels = [
    {"text": "BP1", "center": (538.3, 708.0)},
    {"text": "BP1", "center": (912.0, 708.0)},
    {"text": "BP1", "center": (1853.5, 1362.0)},
    {"text": "BP1", "center": (1607.0, 1360.0)},
    {"text": "BP1", "center": (1367.3, 1360.0)},
    {"text": "BP1", "center": (1127.5, 1360.1)},
    {"text": "BP1", "center": (944.6, 1360.0)},
    {"text": "BP1", "center": (761.7, 1360.0)},
]

print(f"\n📍 Total BP1 labels to check: {len(bp1_labels)}")

doc = fitz.open(PDF_PATH)
page = doc[0]
drawings = page.get_drawings()

print(f"📊 Total drawings in PDF: {len(drawings)}")

# Extract all line segments
all_lines = []
for idx, drawing in enumerate(drawings):
    items = drawing.get('items', [])
    
    if len(items) == 1 and items[0][0] == 'l':
        pt1, pt2 = items[0][1], items[0][2]
        length = math.sqrt((pt2.x - pt1.x)**2 + (pt2.y - pt1.y)**2)
        length_mm = length / 2.834645
        
        all_lines.append({
            'index': idx,
            'x0': pt1.x,
            'y0': pt1.y,
            'x1': pt2.x,
            'y1': pt2.y,
            'length': length,
            'length_mm': length_mm
        })

print(f"📏 Total line segments: {len(all_lines)}")

# Test different size thresholds
size_thresholds = [
    (0.01, 0.5),   # Very tiny
    (0.05, 1.0),   # Tiny
    (0.05, 2.0),   # Current setting
    (0.1, 2.0),    # Slightly larger
]

# Test different search radii
search_radii_mm = [10, 15, 17, 20, 25]

print(f"\n{'='*80}")
print("ANALYSIS BY BP1 LABEL")
print(f"{'='*80}")

for bp_idx, bp in enumerate(bp1_labels, 1):
    bp_center = (bp['center'][0], bp['center'][1])
    
    print(f"\n{'─'*80}")
    print(f"BP1 Label #{bp_idx} at ({bp_center[0]:.0f}, {bp_center[1]:.0f})")
    print(f"{'─'*80}")
    
    # Test each size threshold
    for min_mm, max_mm in size_thresholds:
        tiny_lines = [l for l in all_lines if min_mm <= l['length_mm'] <= max_mm]
        
        print(f"\n  Size range {min_mm}-{max_mm}mm: {len(tiny_lines)} lines")
        
        # Test each search radius
        for radius_mm in search_radii_mm:
            radius_pt = radius_mm * 2.834645
            
            # Find lines near this BP label
            nearby_lines = []
            for line in tiny_lines:
                line_center = ((line['x0'] + line['x1']) / 2, (line['y0'] + line['y1']) / 2)
                dist = math.sqrt(
                    (line_center[0] - bp_center[0])**2 + 
                    (line_center[1] - bp_center[1])**2
                )
                
                if dist <= radius_pt:
                    nearby_lines.append({
                        **line,
                        'distance_mm': dist / 2.834645
                    })
            
            if nearby_lines:
                # Sort by distance
                nearby_lines.sort(key=lambda x: x['distance_mm'])
                
                print(f"    Radius {radius_mm}mm: {len(nearby_lines)} lines")
                
                # Show closest lines
                if len(nearby_lines) > 0:
                    closest = nearby_lines[0]
                    print(f"      Closest: {closest['distance_mm']:.1f}mm away, {closest['length_mm']:.3f}mm long")
                
                # Try to connect them
                if len(nearby_lines) >= 8:
                    # Build endpoint map
                    endpoint_map = defaultdict(list)
                    precision = 0.05
                    
                    for i, line in enumerate(nearby_lines):
                        start_key = (round(line['x0'] / precision) * precision, 
                                   round(line['y0'] / precision) * precision)
                        endpoint_map[start_key].append({
                            'line_idx': i,
                            'x': line['x0'],
                            'y': line['y0'],
                            'other_x': line['x1'],
                            'other_y': line['y1']
                        })
                        
                        end_key = (round(line['x1'] / precision) * precision,
                                 round(line['y1'] / precision) * precision)
                        endpoint_map[end_key].append({
                            'line_idx': i,
                            'x': line['x1'],
                            'y': line['y1'],
                            'other_x': line['x0'],
                            'other_y': line['y0']
                        })
                    
                    # Try to find closed path
                    def find_closed_path(start_idx, lines, endpoint_map, max_depth=50):
                        visited = set()
                        path = [start_idx]
                        visited.add(start_idx)
                        
                        current_x = lines[start_idx]['x1']
                        current_y = lines[start_idx]['y1']
                        start_x = lines[start_idx]['x0']
                        start_y = lines[start_idx]['y0']
                        
                        tolerance = 0.3
                        
                        for depth in range(max_depth):
                            current_key = (round(current_x / precision) * precision,
                                         round(current_y / precision) * precision)
                            candidates = endpoint_map.get(current_key, [])
                            
                            next_line = None
                            for candidate in candidates:
                                line_idx = candidate['line_idx']
                                if line_idx in visited:
                                    continue
                                if abs(candidate['x'] - current_x) <= tolerance and \
                                   abs(candidate['y'] - current_y) <= tolerance:
                                    next_line = candidate
                                    break
                            
                            if next_line is None:
                                if abs(current_x - start_x) <= tolerance and \
                                   abs(current_y - start_y) <= tolerance:
                                    return path
                                else:
                                    return None
                            
                            path.append(next_line['line_idx'])
                            visited.add(next_line['line_idx'])
                            current_x = next_line['other_x']
                            current_y = next_line['other_y']
                            
                            if abs(current_x - start_x) <= tolerance and \
                               abs(current_y - start_y) <= tolerance:
                                return path
                        
                        return None
                    
                    # Try to find paths
                    paths = []
                    processed = set()
                    
                    for i in range(len(nearby_lines)):
                        if i in processed:
                            continue
                        
                        path = find_closed_path(i, nearby_lines, endpoint_map)
                        
                        if path and len(path) >= 8:
                            for line_idx in path:
                                processed.add(line_idx)
                            paths.append(path)
                    
                    if paths:
                        print(f"      ✅ Found {len(paths)} closed path(s)!")
                        for p_idx, path in enumerate(paths, 1):
                            path_lines = [nearby_lines[idx] for idx in path]
                            
                            # Calculate bounding box
                            all_x = []
                            all_y = []
                            for line in path_lines:
                                all_x.extend([line['x0'], line['x1']])
                                all_y.extend([line['y0'], line['y1']])
                            
                            width_mm = (max(all_x) - min(all_x)) / 2.834645
                            height_mm = (max(all_y) - min(all_y)) / 2.834645
                            
                            print(f"         Path {p_idx}: {len(path)} segments, {width_mm:.1f}x{height_mm:.1f}mm")

# Summary
print(f"\n{'='*80}")
print("SUMMARY & RECOMMENDATIONS")
print(f"{'='*80}")

print(f"""
Analysis complete for {len(bp1_labels)} BP1 labels.

Key Findings:
1. Check which labels found symbols and which didn't
2. Compare size thresholds - are symbols smaller than 0.05mm?
3. Check search radius - are symbols further than 17mm?
4. Look for connection issues - do lines connect properly?

Recommendations:
- If symbols found at smaller sizes: reduce min_length_mm
- If symbols found at larger radii: increase search radius
- If lines don't connect: adjust tolerance or precision
- If no lines found: symbols might be curves, not lines
""")

doc.close()
