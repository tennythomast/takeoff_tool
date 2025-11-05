"""
YOLO-based Engineering Drawing Detection

Test YOLO models for detecting:
- Walls
- Structural elements
- Shapes (circles, rectangles)
- Annotations

Using Ultralytics YOLOv8 as the base model.
"""

import os
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import fitz  # PyMuPDF

# Check if ultralytics is installed
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("⚠️  Ultralytics YOLO not installed. Install with: pip install ultralytics")

print("="*80)
print("YOLO ENGINEERING DRAWING DETECTION")
print("="*80)

# Configuration
PDF_PATH = "/app/backend/rag_service/tests/gwynne1.pdf"
OUTPUT_DIR = "/app/research/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def pdf_to_image(pdf_path, page_num=0, dpi=300):
    """Convert PDF page to image for YOLO processing"""
    doc = fitz.open(pdf_path)
    page = doc[page_num]
    
    # Render page to pixmap at high DPI
    mat = fitz.Matrix(dpi/72, dpi/72)
    pix = page.get_pixmap(matrix=mat)
    
    # Convert to numpy array
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    
    # Convert RGBA to RGB if needed
    if pix.n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
    
    doc.close()
    return img

def test_pretrained_yolo():
    """Test with pre-trained YOLO model"""
    if not YOLO_AVAILABLE:
        print("\n❌ Cannot run YOLO test - ultralytics not installed")
        return
    
    print("\n[1/3] Converting PDF to image...")
    img = pdf_to_image(PDF_PATH, dpi=200)  # Lower DPI for faster processing
    print(f"   Image size: {img.shape[1]}x{img.shape[0]} pixels")
    
    # Save the image
    img_path = os.path.join(OUTPUT_DIR, "gwynne1_page0.jpg")
    cv2.imwrite(img_path, cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    print(f"   Saved to: {img_path}")
    
    print("\n[2/3] Loading YOLO model...")
    # Try YOLOv8 pre-trained on COCO (general objects)
    # Note: This won't detect engineering-specific elements, but tests the pipeline
    try:
        model = YOLO('yolov8n.pt')  # nano model for speed
        print("   ✓ YOLOv8n loaded")
    except Exception as e:
        print(f"   ✗ Failed to load model: {e}")
        return
    
    print("\n[3/3] Running detection...")
    results = model(img_path, conf=0.25)
    
    # Process results
    print(f"\n📊 Detection Results:")
    if len(results) > 0:
        result = results[0]
        boxes = result.boxes
        
        if len(boxes) > 0:
            print(f"   Detected {len(boxes)} objects")
            
            # Count by class
            class_counts = {}
            for box in boxes:
                cls_id = int(box.cls[0])
                cls_name = model.names[cls_id]
                class_counts[cls_name] = class_counts.get(cls_name, 0) + 1
            
            print(f"\n   Detected classes:")
            for cls_name, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"      {cls_name}: {count}")
            
            # Save annotated image
            annotated = result.plot()
            output_path = os.path.join(OUTPUT_DIR, "gwynne1_yolo_detected.jpg")
            cv2.imwrite(output_path, annotated)
            print(f"\n   ✓ Annotated image saved to: {output_path}")
        else:
            print("   No objects detected")
    else:
        print("   No results returned")

def analyze_for_custom_training():
    """Analyze what we need for custom YOLO training on engineering drawings"""
    print("\n" + "="*80)
    print("CUSTOM YOLO TRAINING REQUIREMENTS")
    print("="*80)
    
    print("""
For training YOLO on engineering drawings, we need:

1. **Dataset**:
   - 500-1000+ annotated engineering drawings
   - Bounding boxes for:
     * Walls (interior, exterior)
     * Doors
     * Windows
     * Structural elements (columns, beams)
     * Symbols (electrical, plumbing)
     * Text annotations
     * Dimension lines
     * Shapes (circles, rectangles for elements)

2. **Annotation Format**:
   - YOLO format: <class_id> <x_center> <y_center> <width> <height>
   - Normalized coordinates (0-1)
   - Tools: LabelImg, Roboflow, CVAT

3. **Classes to Detect**:
   - wall_interior
   - wall_exterior
   - door
   - window
   - column
   - beam
   - circle_element (BP, PF markers)
   - rectangle_element
   - text_label
   - dimension_line

4. **Training Process**:
   - Use YOLOv8 as base
   - Transfer learning from COCO weights
   - Train for 100-300 epochs
   - Validate on held-out drawings

5. **Advantages over Current Approach**:
   ✓ Detects semantic elements (walls, doors) not just shapes
   ✓ Handles complex overlapping elements
   ✓ Can detect text regions
   ✓ Fast inference (real-time)
   
6. **Disadvantages**:
   ✗ Requires large annotated dataset
   ✗ Training time and compute
   ✗ May not be as precise as vector-based detection for exact dimensions
   ✗ Struggles with very small elements

7. **Hybrid Approach** (RECOMMENDED):
   - Use YOLO for semantic detection (walls, doors, rooms)
   - Use vector extraction for precise measurements
   - Use shape detection for element markers
   - Combine all three for complete understanding
""")

def check_available_models():
    """Check for available pre-trained models on engineering drawings"""
    print("\n" + "="*80)
    print("AVAILABLE ENGINEERING DRAWING MODELS")
    print("="*80)
    
    print("""
Pre-trained models to explore:

1. **Roboflow Universe**:
   - Search for "floor plan", "engineering drawing", "blueprint"
   - Community-trained models available
   - Example: https://universe.roboflow.com/

2. **Hugging Face**:
   - YOLOv5/v8 models fine-tuned on architectural drawings
   - Search: "floor plan detection", "blueprint detection"

3. **GitHub Repositories**:
   - CubiCasa5k dataset (floor plan parsing)
   - RPLAN dataset (residential floor plans)
   - FloorNet models

4. **Academic Models**:
   - Papers with code: "floor plan analysis"
   - Often include pre-trained weights

Next Steps:
1. Search Roboflow Universe for engineering drawing models
2. Test with a pre-trained model if available
3. If none suitable, consider creating custom dataset
4. Start with small dataset (100 images) for proof of concept
""")

# Main execution
if __name__ == "__main__":
    print(f"\n📁 PDF: {PDF_PATH}")
    print(f"📁 Output: {OUTPUT_DIR}")
    
    # Test with pre-trained YOLO (will detect general objects, not engineering-specific)
    test_pretrained_yolo()
    
    # Show what's needed for custom training
    analyze_for_custom_training()
    
    # Show available models
    check_available_models()
    
    print("\n" + "="*80)
    print("EXPERIMENT COMPLETE")
    print("="*80)
    print("""
Summary:
- Pre-trained YOLO tested on engineering drawing
- Custom training requirements documented
- Next steps: Find or create engineering drawing dataset

Recommendation:
Use HYBRID approach combining:
1. YOLO for semantic detection (walls, doors, rooms)
2. Vector extraction for precise measurements (our current approach)
3. Shape detection for element markers (our current approach)
""")
