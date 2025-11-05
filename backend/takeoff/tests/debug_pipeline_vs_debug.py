"""
Compare pipeline's TinyStrokeConnector with debug script's path finding

Tests the same BP1 label with both approaches to see why one works and the other doesn't.
"""

import sys
sys.path.insert(0, '/app/backend/takeoff/services/measurement/vector')

from line_detector import TinyStrokeConnector, LineDetector
import fitz
import math
from collections import defaultdict

PDF_PATH = "/app/backend/rag_service/tests/7_FLETT_RD.pdf"

# Test on BP1 at (762, 1360) - one that debug finds but pipeline doesn't
bp_center = (762.7, 1360.0)
radius_mm = 17.0

print("="*80)
print(f"COMPARISON: Pipeline vs Debug Script")
print(f"BP1 at ({bp_center[0]:.0f}, {bp_center[1]:.0f})")
print("="*80)

doc = fitz.open(PDF_PATH)
page = doc[0]

# ============================================================================
# METHOD 1: Pipeline's approach (using LineDetector + TinyStrokeConnector)
# ============================================================================
print("\n[METHOD 1] Pipeline's TinyStrokeConnector:")

line_detector = LineDetector(min_length_mm=0.05, max_length_mm=2.0)
all_lines = line_detector.extract_lines(page)

radius_pt = radius_mm * 2.834645
nearby_lines = []
for line in all_lines:
    line_center = ((line['x0'] + line['x1']) / 2, (line['y0'] + line['y1']) / 2)
    dist = math.sqrt((line_center[0] - bp_center[0])**2 + (line_center[1] - bp_center[1])**2)
    
    if dist <= radius_pt and line['length_mm'] < 2.0:
        nearby_lines.append(line)

print(f"  Nearby lines: {len(nearby_lines)}")

connector = TinyStrokeConnector(tolerance=0.3)
paths = connector.connect_strokes(nearby_lines, max_depth=100)

print(f"  Paths found: {len(paths)}")
if paths:
    for i, path in enumerate(paths, 1):
        print(f"    Path {i}: {len(path)} segments")

# ============================================================================
# METHOD 2: Debug script's approach (raw implementation)
# ============================================================================
print("\n[METHOD 2] Debug Script's Path Finding:")

# Extract raw lines
drawings = page.get_drawings()
raw_lines = []
for idx, drawing in enumerate(drawings):
    items = drawing.get('items', [])
    if len(items) == 1 and items[0][0] == 'l':
        pt1, pt2 = items[0][1], items[0][2]
        length_mm = math.sqrt((pt2.x - pt1.x)**2 + (pt2.y - pt1.y)**2) / 2.834645
        if 0.05 <= length_mm <= 2.0:
            line_center = ((pt1.x + pt2.x) / 2, (pt1.y + pt2.y) / 2)
            dist = math.sqrt((line_center[0] - bp_center[0])**2 + (line_center[1] - bp_center[1])**2)
            if dist <= radius_pt:
                raw_lines.append({
                    'x0': pt1.x,
                    'y0': pt1.y,
                    'x1': pt2.x,
                    'y1': pt2.y,
                    'length_mm': length_mm
                })

print(f"  Nearby lines: {len(raw_lines)}")

# Build endpoint map
endpoint_map = defaultdict(list)
precision = 0.05

for i, line in enumerate(raw_lines):
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

# Find paths
def find_closed_path(start_idx, lines, endpoint_map, max_depth=100):
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

debug_paths = []
processed = set()

for i in range(len(raw_lines)):
    if i in processed:
        continue
    
    path = find_closed_path(i, raw_lines, endpoint_map)
    
    if path and len(path) >= 8:
        for line_idx in path:
            processed.add(line_idx)
        debug_paths.append(path)

print(f"  Paths found: {len(debug_paths)}")
if debug_paths:
    for i, path in enumerate(debug_paths, 1):
        print(f"    Path {i}: {len(path)} segments")

# ============================================================================
# COMPARISON
# ============================================================================
print(f"\n{'='*80}")
print("COMPARISON RESULTS")
print(f"{'='*80}")

print(f"\nLine counts:")
print(f"  Pipeline: {len(nearby_lines)} lines")
print(f"  Debug: {len(raw_lines)} lines")

print(f"\nPath counts:")
print(f"  Pipeline: {len(paths)} paths")
print(f"  Debug: {len(debug_paths)} paths")

if len(nearby_lines) != len(raw_lines):
    print(f"\n⚠️  LINE COUNT MISMATCH!")
    print(f"  Difference: {abs(len(nearby_lines) - len(raw_lines))} lines")
    print(f"  This might be due to filtering or extraction differences.")

if len(paths) != len(debug_paths):
    print(f"\n⚠️  PATH COUNT MISMATCH!")
    print(f"  Pipeline found {len(paths)} paths")
    print(f"  Debug found {len(debug_paths)} paths")
    print(f"  The path-finding algorithms are producing different results!")

doc.close()
