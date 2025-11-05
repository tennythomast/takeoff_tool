"""
Visualize MuraNet detection results

Creates a comprehensive visualization showing:
1. Original floor plan
2. Detected walls (horizontal and vertical)
3. Binary threshold
4. Edge detection
5. Combined overlay
"""

import cv2
import numpy as np
import os
from pathlib import Path

print("="*80)
print("MURANET RESULTS VISUALIZATION")
print("="*80)

# Paths
INPUT_DIR = "/app/research/output/muranet"
OUTPUT_PATH = "/app/research/output/muranet/combined_visualization.jpg"

# Load images
print("\n📂 Loading detection results...")

try:
    original = cv2.imread(os.path.join(INPUT_DIR, "input_floorplan.jpg"))
    walls = cv2.imread(os.path.join(INPUT_DIR, "walls_detected.jpg"))
    binary = cv2.imread(os.path.join(INPUT_DIR, "binary_threshold.jpg"))
    edges = cv2.imread(os.path.join(INPUT_DIR, "edges_detected.jpg"))
    
    print(f"   ✓ Original: {original.shape[1]}x{original.shape[0]}")
    print(f"   ✓ Walls detected: {walls.shape[1]}x{walls.shape[0]}")
    print(f"   ✓ Binary threshold: {binary.shape[1]}x{binary.shape[0]}")
    print(f"   ✓ Edges: {edges.shape[1]}x{edges.shape[0]}")
    
except Exception as e:
    print(f"   ✗ Error loading images: {e}")
    exit(1)

# Create a grid visualization
print("\n🎨 Creating combined visualization...")

# Resize images to fit in grid (reduce size for display)
max_width = 1600
scale = max_width / original.shape[1]
new_width = int(original.shape[1] * scale)
new_height = int(original.shape[0] * scale)

original_resized = cv2.resize(original, (new_width, new_height))
walls_resized = cv2.resize(walls, (new_width, new_height))
binary_resized = cv2.resize(binary, (new_width, new_height))
edges_resized = cv2.resize(edges, (new_width, new_height))

# Convert grayscale to BGR for consistency
if len(binary_resized.shape) == 2:
    binary_resized = cv2.cvtColor(binary_resized, cv2.COLOR_GRAY2BGR)
if len(edges_resized.shape) == 2:
    edges_resized = cv2.cvtColor(edges_resized, cv2.COLOR_GRAY2BGR)

# Add labels to each image
def add_label(img, text, position='top'):
    """Add a label to an image"""
    img_copy = img.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.5
    thickness = 3
    
    # Get text size
    (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    
    # Calculate position
    if position == 'top':
        x = (img_copy.shape[1] - text_width) // 2
        y = 50
    else:
        x = (img_copy.shape[1] - text_width) // 2
        y = img_copy.shape[0] - 30
    
    # Draw background rectangle
    cv2.rectangle(img_copy, 
                  (x - 10, y - text_height - 10), 
                  (x + text_width + 10, y + baseline + 10),
                  (255, 255, 255), -1)
    
    # Draw text
    cv2.putText(img_copy, text, (x, y), font, font_scale, (0, 0, 0), thickness)
    
    return img_copy

original_labeled = add_label(original_resized, "1. Original Floor Plan")
walls_labeled = add_label(walls_resized, "2. Detected Walls")
binary_labeled = add_label(binary_resized, "3. Binary Threshold")
edges_labeled = add_label(edges_resized, "4. Edge Detection")

# Create 2x2 grid
print("   Creating 2x2 grid layout...")
top_row = np.hstack([original_labeled, walls_labeled])
bottom_row = np.hstack([binary_labeled, edges_labeled])
grid = np.vstack([top_row, bottom_row])

# Save grid
cv2.imwrite(OUTPUT_PATH, grid)
print(f"   ✓ Grid saved to: {OUTPUT_PATH}")

# Create detailed wall overlay
print("\n🎨 Creating detailed wall overlay...")

# Create a version with just walls on white background
wall_overlay = original_resized.copy()

# Add statistics overlay
stats_img = wall_overlay.copy()

# Add text box with statistics
stats_text = [
    "WALL DETECTION STATISTICS",
    "",
    "Horizontal lines: 2785",
    "Vertical lines: 644",
    "Wall segments: 22",
    "",
    "Legend:",
    "Red = Horizontal walls",
    "Blue = Vertical walls"
]

# Draw stats box
box_x = 50
box_y = 50
box_width = 500
line_height = 40

# Background
cv2.rectangle(stats_img, 
              (box_x - 20, box_y - 20),
              (box_x + box_width, box_y + len(stats_text) * line_height + 20),
              (255, 255, 255), -1)
cv2.rectangle(stats_img, 
              (box_x - 20, box_y - 20),
              (box_x + box_width, box_y + len(stats_text) * line_height + 20),
              (0, 0, 0), 3)

# Text
font = cv2.FONT_HERSHEY_SIMPLEX
for i, line in enumerate(stats_text):
    if i == 0:
        # Title
        cv2.putText(stats_img, line, (box_x, box_y + i * line_height + 30),
                   font, 0.8, (0, 0, 0), 2)
    elif "Red" in line:
        cv2.putText(stats_img, line, (box_x, box_y + i * line_height + 30),
                   font, 0.7, (0, 0, 255), 2)
    elif "Blue" in line:
        cv2.putText(stats_img, line, (box_x, box_y + i * line_height + 30),
                   font, 0.7, (255, 0, 0), 2)
    else:
        cv2.putText(stats_img, line, (box_x, box_y + i * line_height + 30),
                   font, 0.7, (0, 0, 0), 2)

# Blend with walls
alpha = 0.7
detailed_overlay = cv2.addWeighted(walls_resized, alpha, stats_img, 1-alpha, 0)

detailed_path = os.path.join(INPUT_DIR, "detailed_wall_overlay.jpg")
cv2.imwrite(detailed_path, detailed_overlay)
print(f"   ✓ Detailed overlay saved to: {detailed_path}")

# Create a zoomed view of a section
print("\n🔍 Creating zoomed detail view...")

# Take center section
h, w = original_resized.shape[:2]
crop_size = min(800, h//2, w//2)
center_x, center_y = w//2, h//2

x1 = max(0, center_x - crop_size//2)
y1 = max(0, center_y - crop_size//2)
x2 = min(w, x1 + crop_size)
y2 = min(h, y1 + crop_size)

original_crop = original_resized[y1:y2, x1:x2]
walls_crop = walls_resized[y1:y2, x1:x2]

# Side by side
zoom_comparison = np.hstack([original_crop, walls_crop])
zoom_comparison = add_label(zoom_comparison, "Zoomed Detail: Original vs Wall Detection")

zoom_path = os.path.join(INPUT_DIR, "zoomed_detail.jpg")
cv2.imwrite(zoom_path, zoom_comparison)
print(f"   ✓ Zoomed detail saved to: {zoom_path}")

print("\n" + "="*80)
print("VISUALIZATION COMPLETE")
print("="*80)

print(f"""
📁 Output files created:

1. Combined Grid (2x2):
   {OUTPUT_PATH}
   Shows: Original, Walls, Binary, Edges

2. Detailed Wall Overlay:
   {detailed_path}
   Shows: Walls with statistics overlay

3. Zoomed Detail:
   {zoom_path}
   Shows: Close-up comparison

📊 Detection Summary:
   - 2,785 horizontal lines (potential walls/dimensions)
   - 644 vertical lines (potential walls/columns)
   - 22 wall segments identified

💡 Observations:
   - Red lines = Horizontal elements
   - Blue lines = Vertical elements
   - Many lines are dimensions/annotations (not walls)
   - Need semantic understanding to filter actual walls

Next Steps:
   1. Review the visualizations
   2. Implement filtering to separate walls from annotations
   3. Integrate with shape detection for complete analysis
""")
