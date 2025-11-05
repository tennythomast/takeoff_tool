"""
MuraNet Floor Plan Detection

MuraNet is a deep learning model specifically designed for floor plan analysis.
It can detect:
- Walls
- Doors
- Windows
- Rooms
- Other architectural elements

Paper: "MuraNet: Multi-task Floor Plan Recognition with Relation Attention"
GitHub: https://github.com/art-programmer/FloorplanTransformation
"""

import os
import sys
from pathlib import Path
import cv2
import numpy as np
import fitz  # PyMuPDF
import torch

print("="*80)
print("MURANET FLOOR PLAN DETECTION")
print("="*80)

# Configuration
PDF_PATH = "/app/backend/rag_service/tests/gwynne1.pdf"
OUTPUT_DIR = "/app/research/output/muranet"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def check_dependencies():
    """Check if required dependencies are available"""
    print("\n[1/5] Checking dependencies...")
    
    dependencies = {
        'torch': False,
        'torchvision': False,
        'cv2': False,
        'numpy': False,
        'PIL': False
    }
    
    try:
        import torch
        dependencies['torch'] = True
        print(f"   ✓ PyTorch {torch.__version__}")
    except ImportError:
        print("   ✗ PyTorch not installed")
    
    try:
        import torchvision
        dependencies['torchvision'] = True
        print(f"   ✓ torchvision {torchvision.__version__}")
    except ImportError:
        print("   ✗ torchvision not installed")
    
    try:
        import cv2
        dependencies['cv2'] = True
        print(f"   ✓ OpenCV {cv2.__version__}")
    except ImportError:
        print("   ✗ OpenCV not installed")
    
    try:
        import numpy
        dependencies['numpy'] = True
        print(f"   ✓ NumPy {numpy.__version__}")
    except ImportError:
        print("   ✗ NumPy not installed")
    
    try:
        from PIL import Image
        dependencies['PIL'] = True
        print(f"   ✓ PIL/Pillow")
    except ImportError:
        print("   ✗ PIL/Pillow not installed")
    
    all_available = all(dependencies.values())
    
    if not all_available:
        print("\n   ⚠️  Missing dependencies. Install with:")
        print("   pip install torch torchvision opencv-python-headless pillow")
        return False
    
    return True

def pdf_to_image(pdf_path, page_num=0, dpi=300):
    """Convert PDF page to image"""
    print(f"\n[2/5] Converting PDF to image (DPI: {dpi})...")
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    
    # Render page to pixmap
    mat = fitz.Matrix(dpi/72, dpi/72)
    pix = page.get_pixmap(matrix=mat)
    
    # Convert to numpy array
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    
    # Convert RGBA to RGB if needed
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
    
    doc.close()
    
    print(f"   Image size: {img.shape[1]}x{img.shape[0]} pixels")
    
    # Save image
    img_path = os.path.join(OUTPUT_DIR, "input_floorplan.jpg")
    cv2.imwrite(img_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    print(f"   ✓ Saved to: {img_path}")
    
    return img, img_path

def download_muranet_model():
    """Download or check for MuraNet model"""
    print("\n[3/5] Checking for MuraNet model...")
    
    model_dir = "/app/research/models/muranet"
    os.makedirs(model_dir, exist_ok=True)
    
    print("""
   MuraNet Model Setup:
   
   Option 1: Use FloorplanTransformation (Original Implementation)
   - GitHub: https://github.com/art-programmer/FloorplanTransformation
   - Clone repo and use their pre-trained model
   - Supports: walls, doors, windows, icons
   
   Option 2: Use CubiCasa5k Pre-trained Model
   - Dataset: https://github.com/CubiCasa/CubiCasa5k
   - Pre-trained on 5000 floor plans
   - Better for residential floor plans
   
   Option 3: Use Simplified Approach (RECOMMENDED for POC)
   - Use edge detection + contour analysis
   - Detect walls as thick lines
   - Detect rooms as enclosed regions
   - No ML model needed
   
   For now, we'll implement Option 3 as a baseline.
""")
    
    return None

def detect_walls_simple(img):
    """Simple wall detection using edge detection and morphology"""
    print("\n[4/5] Detecting walls (simple approach)...")
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    
    # Threshold to get black lines (walls)
    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    
    # Morphological operations to connect wall segments
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(binary, kernel, iterations=1)
    
    # Find contours (potential walls)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours by area (walls should be reasonably sized)
    min_area = 100
    wall_contours = [c for c in contours if cv2.contourArea(c) > min_area]
    
    print(f"   Found {len(wall_contours)} potential wall segments")
    
    # Detect horizontal and vertical lines (typical walls)
    edges = cv2.Canny(gray, 50, 150)
    
    # Use Hough Line Transform to detect straight lines
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=50, maxLineGap=10)
    
    horizontal_lines = []
    vertical_lines = []
    
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            
            # Calculate angle
            angle = np.abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            
            # Classify as horizontal or vertical
            if angle < 10 or angle > 170:
                horizontal_lines.append(line[0])
            elif 80 < angle < 100:
                vertical_lines.append(line[0])
        
        print(f"   Horizontal lines: {len(horizontal_lines)}")
        print(f"   Vertical lines: {len(vertical_lines)}")
    
    return {
        'contours': wall_contours,
        'horizontal_lines': horizontal_lines,
        'vertical_lines': vertical_lines,
        'binary': binary,
        'edges': edges
    }

def visualize_results(img, detection_results):
    """Visualize detected walls and elements"""
    print("\n[5/5] Creating visualization...")
    
    # Create output image
    output = img.copy()
    
    # Draw horizontal lines (walls) in red
    for line in detection_results['horizontal_lines']:
        x1, y1, x2, y2 = line
        cv2.line(output, (x1, y1), (x2, y2), (255, 0, 0), 3)
    
    # Draw vertical lines (walls) in blue
    for line in detection_results['vertical_lines']:
        x1, y1, x2, y2 = line
        cv2.line(output, (x1, y1), (x2, y2), (0, 0, 255), 3)
    
    # Save results
    output_path = os.path.join(OUTPUT_DIR, "walls_detected.jpg")
    cv2.imwrite(output_path, cv2.cvtColor(output, cv2.COLOR_RGB2BGR))
    print(f"   ✓ Wall detection saved to: {output_path}")
    
    # Save binary image
    binary_path = os.path.join(OUTPUT_DIR, "binary_threshold.jpg")
    cv2.imwrite(binary_path, detection_results['binary'])
    print(f"   ✓ Binary image saved to: {binary_path}")
    
    # Save edges
    edges_path = os.path.join(OUTPUT_DIR, "edges_detected.jpg")
    cv2.imwrite(edges_path, detection_results['edges'])
    print(f"   ✓ Edges saved to: {edges_path}")
    
    return output_path

def setup_muranet_proper():
    """Instructions for setting up actual MuraNet"""
    print("\n" + "="*80)
    print("SETTING UP ACTUAL MURANET")
    print("="*80)
    
    print("""
To use the actual MuraNet model:

1. **Clone FloorplanTransformation Repository**:
   ```bash
   cd /app/research/models
   git clone https://github.com/art-programmer/FloorplanTransformation.git
   cd FloorplanTransformation
   ```

2. **Install Dependencies**:
   ```bash
   pip install torch torchvision
   pip install opencv-python pillow
   pip install scipy scikit-image
   ```

3. **Download Pre-trained Weights**:
   - Download from: https://github.com/art-programmer/FloorplanTransformation/releases
   - Place in: /app/research/models/muranet/checkpoint.pth

4. **Run Inference**:
   ```python
   from FloorplanTransformation.floorplan_dataset_maps import FloorplanGraphDataset
   from FloorplanTransformation.models.model import Model
   
   # Load model
   model = Model()
   model.load_state_dict(torch.load('checkpoint.pth'))
   model.eval()
   
   # Run inference
   with torch.no_grad():
       output = model(input_image)
   ```

5. **Alternative: Use CubiCasa5k**:
   - GitHub: https://github.com/CubiCasa/CubiCasa5k
   - Pre-trained on 5000 residential floor plans
   - Better documented and easier to use

6. **Alternative: Use RoomFormer** (Latest):
   - Paper: "RoomFormer: Room-wise Floor Plan Generation"
   - State-of-the-art for floor plan parsing
   - GitHub: Search for "RoomFormer floor plan"
""")

# Main execution
if __name__ == "__main__":
    print(f"\n📁 Input PDF: {PDF_PATH}")
    print(f"📁 Output Directory: {OUTPUT_DIR}")
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Cannot proceed without required dependencies")
        sys.exit(1)
    
    # Convert PDF to image
    img, img_path = pdf_to_image(PDF_PATH, dpi=200)
    
    # Check for MuraNet model
    model = download_muranet_model()
    
    # Run simple wall detection (baseline)
    results = detect_walls_simple(img)
    
    # Visualize results
    output_path = visualize_results(img, results)
    
    # Show setup instructions for actual MuraNet
    setup_muranet_proper()
    
    print("\n" + "="*80)
    print("DETECTION COMPLETE")
    print("="*80)
    
    print(f"""
Summary:
- Simple wall detection completed
- Detected {len(results['horizontal_lines'])} horizontal walls
- Detected {len(results['vertical_lines'])} vertical walls
- Output saved to: {OUTPUT_DIR}

Next Steps:
1. Review the simple detection results
2. If satisfactory, integrate with shape detection
3. If need better accuracy, set up actual MuraNet model
4. Consider hybrid approach: MuraNet for walls + our shape detection for elements

Recommendation:
Current approach (vector + shape detection) is working well.
Use MuraNet/wall detection as ENHANCEMENT for:
- Room boundary detection
- Wall thickness measurement
- Structural element classification
""")
