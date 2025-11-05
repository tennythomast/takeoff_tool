"""
Integrated Element Detector

Combines VectorTextExtractor (for element identification) with 
AdaptiveLineShapeDetector (for shape detection) to create a powerful
element detection system that:

1. Uses VectorTextExtractor to find element labels (BP1, PF1, etc.)
2. Uses AdaptiveLineShapeDetector to find all shapes in the drawing
3. Spatially associates shapes with nearby element labels
4. Filters out shapes that aren't near any identified elements
5. Returns complete element data with both text and shape information

This approach leverages the strengths of both systems:
- Text extraction is excellent at identifying element IDs
- Shape detection is excellent at finding geometric boundaries
- Spatial association links them together
"""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import math

from takeoff.services.extractors.vector_text_extractor import VectorTextExtractor
from takeoff.services.extractors.line_shape_detector import AdaptiveLineShapeDetector
from takeoff.shapes import Circle, Rectangle, Polygon, Point, BoundingBox

logger = logging.getLogger(__name__)


@dataclass
class IntegratedElement:
    """An element with both text and shape information"""
    element_id: str
    element_type: str  # 'BP', 'PF', 'SF', etc.
    text_bbox: BoundingBox
    text_position: Point
    shape: Optional[object]  # Circle, Rectangle, or Polygon
    shape_bbox: Optional[BoundingBox]
    distance_mm: float  # Distance between text and shape
    confidence: float
    page_number: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        result = {
            'element_id': self.element_id,
            'element_type': self.element_type,
            'text_bbox': {
                'x0': self.text_bbox.x0,
                'y0': self.text_bbox.y0,
                'x1': self.text_bbox.x1,
                'y1': self.text_bbox.y1
            },
            'text_position': {
                'x': self.text_position.x,
                'y': self.text_position.y
            },
            'distance_mm': self.distance_mm,
            'confidence': self.confidence,
            'page_number': self.page_number
        }
        
        if self.shape:
            # Shape is already a dict from shape detection
            result['shape'] = self.shape if isinstance(self.shape, dict) else self.shape.to_dict()
            
        if self.shape_bbox:
            result['shape_bbox'] = {
                'x0': self.shape_bbox.x0,
                'y0': self.shape_bbox.y0,
                'x1': self.shape_bbox.x1,
                'y1': self.shape_bbox.y1
            }
        
        return result


class IntegratedElementDetector:
    """
    Combines text extraction and shape detection for robust element identification
    """
    
    def __init__(self, 
                 max_distance_mm: float = 50.0,
                 require_shape: bool = False):
        """
        Args:
            max_distance_mm: Maximum distance between text and shape to associate them
            require_shape: If True, only return elements that have an associated shape
        """
        self.text_extractor = VectorTextExtractor()
        self.shape_detector = AdaptiveLineShapeDetector()
        self.max_distance = max_distance_mm * 2.834645  # Convert to points
        self.require_shape = require_shape
        
        logger.info(f"IntegratedElementDetector initialized:")
        logger.info(f"  max_distance: {max_distance_mm}mm")
        logger.info(f"  require_shape: {require_shape}")
    
    def detect_elements(self, pdf_path: str, overlay_json: str = None) -> Dict:
        """
        Detect elements by combining text extraction and shape detection
        
        Args:
            pdf_path: Path to PDF file
            overlay_json: Optional path to overlay_data.json (if None, will extract text)
            
        Returns:
            Dict with detected elements, statistics, and debug info
        """
        logger.info(f"="*80)
        logger.info(f"INTEGRATED ELEMENT DETECTION")
        logger.info(f"PDF: {pdf_path}")
        if overlay_json:
            logger.info(f"Overlay data: {overlay_json}")
        logger.info(f"="*80)
        
        # Step 1: Extract text elements
        logger.info("\n[1/3] Extracting text elements...")
        
        if overlay_json:
            # Load from overlay_data.json
            import json
            with open(overlay_json, 'r') as f:
                text_result = json.load(f)
            text_result['success'] = True
        else:
            # Extract from PDF
            text_result = self.text_extractor.extract_from_file(pdf_path)
        
        if not text_result.get('success'):
            return {
                'success': False,
                'error': 'Text extraction failed',
                'elements': []
            }
        
        text_elements = self._parse_text_elements(text_result)
        logger.info(f"   Found {len(text_elements)} text elements")
        
        # Step 2: Detect shapes
        logger.info("\n[2/3] Detecting shapes...")
        shape_result = self._detect_shapes(pdf_path)
        
        if not shape_result.get('success'):
            return {
                'success': False,
                'error': 'Shape detection failed',
                'elements': []
            }
        
        shapes = shape_result.get('shapes', [])
        logger.info(f"   Found {len(shapes)} shapes")
        
        # Step 3: Associate text with shapes
        logger.info("\n[3/3] Associating text with shapes...")
        integrated_elements = self._associate_text_and_shapes(text_elements, shapes)
        
        logger.info(f"   Created {len(integrated_elements)} integrated elements")
        
        # Statistics
        with_shape = sum(1 for e in integrated_elements if e.shape is not None)
        without_shape = len(integrated_elements) - with_shape
        
        logger.info(f"\n{'='*80}")
        logger.info(f"RESULTS:")
        logger.info(f"   Total elements: {len(integrated_elements)}")
        logger.info(f"   With shapes: {with_shape}")
        logger.info(f"   Without shapes: {without_shape}")
        logger.info(f"{'='*80}\n")
        
        return {
            'success': True,
            'elements': [e.to_dict() for e in integrated_elements],
            'statistics': {
                'total_elements': len(integrated_elements),
                'with_shapes': with_shape,
                'without_shapes': without_shape,
                'total_text_elements': len(text_elements),
                'total_shapes': len(shapes)
            },
            'text_result': text_result,
            'shape_result': shape_result
        }
    
    def _parse_text_elements(self, text_result: Dict) -> List[Dict]:
        """Parse text extraction results into element list"""
        elements = []
        
        # Check if we have the overlay_data format (from vector_text_extractor output)
        if 'elements' in text_result and 'metadata' in text_result:
            # This is overlay_data.json format
            for elem in text_result.get('elements', []):
                element_id = elem.get('element_id', '')
                occurrences = elem.get('occurrences', [])
                
                for occurrence in occurrences:
                    bbox = occurrence.get('bbox', {})
                    page_num = occurrence.get('page', 1)
                    
                    elements.append({
                        'element_id': element_id,
                        'element_type': self._extract_element_type(element_id),
                        'bbox': BoundingBox(
                            x0=bbox.get('x0', 0),
                            y0=bbox.get('y0', 0),
                            x1=bbox.get('x1', 0),
                            y1=bbox.get('y1', 0)
                        ),
                        'position': Point(
                            x=occurrence.get('x', (bbox.get('x0', 0) + bbox.get('x1', 0)) / 2),
                            y=occurrence.get('y', (bbox.get('y0', 0) + bbox.get('y1', 0)) / 2)
                        ),
                        'page_number': page_num,
                        'confidence': occurrence.get('confidence', 1.0)
                    })
        else:
            # Standard format with pages
            for page_data in text_result.get('pages', []):
                page_num = page_data.get('page_number', 1)
                
                for text_elem in page_data.get('text_elements', []):
                    text = text_elem.get('text', '').strip()
                    bbox = text_elem.get('bbox', {})
                    
                    # Check if this looks like an element ID
                    if self._is_element_id(text):
                        elements.append({
                            'element_id': text,
                            'element_type': self._extract_element_type(text),
                            'bbox': BoundingBox(
                                x0=bbox.get('x0', 0),
                                y0=bbox.get('y0', 0),
                                x1=bbox.get('x1', 0),
                                y1=bbox.get('y1', 0)
                            ),
                            'position': Point(
                                x=(bbox.get('x0', 0) + bbox.get('x1', 0)) / 2,
                                y=(bbox.get('y0', 0) + bbox.get('y1', 0)) / 2
                            ),
                            'page_number': page_num,
                            'confidence': text_elem.get('confidence', 1.0)
                        })
        
        logger.info(f"   Parsed {len(elements)} element IDs from text")
        return elements
    
    def _is_element_id(self, text: str) -> bool:
        """Check if text looks like an element ID (e.g., BP1, PF2, SF3)"""
        import re
        # Pattern: 2-3 uppercase letters followed by 1-3 digits
        pattern = r'^[A-Z]{2,3}\d{1,3}$'
        return bool(re.match(pattern, text))
    
    def _extract_element_type(self, element_id: str) -> str:
        """Extract element type from ID (e.g., 'BP1' -> 'BP')"""
        import re
        match = re.match(r'^([A-Z]{2,3})\d+$', element_id)
        return match.group(1) if match else 'UNKNOWN'
    
    def _detect_shapes(self, pdf_path: str) -> Dict:
        """Detect shapes using AdaptiveLineShapeDetector"""
        import pdfplumber
        
        try:
            shapes = []
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    lines = page.lines
                    
                    # Detect shapes on this page
                    result = self.shape_detector.detect_shapes_from_pdfplumber(lines, page_num)
                    
                    # Collect all shapes
                    for circle_dict in result.get('circles', []):
                        shapes.append({
                            'type': 'circle',
                            'page_number': page_num,
                            'data': circle_dict,
                            'center': Point(
                                x=circle_dict['center']['x'],
                                y=circle_dict['center']['y']
                            ),
                            'bbox': BoundingBox(
                                x0=circle_dict['bbox']['x0'],
                                y0=circle_dict['bbox']['y0'],
                                x1=circle_dict['bbox']['x1'],
                                y1=circle_dict['bbox']['y1']
                            )
                        })
                    
                    for rect_dict in result.get('rectangles', []):
                        shapes.append({
                            'type': 'rectangle',
                            'page_number': page_num,
                            'data': rect_dict,
                            'center': Point(
                                x=(rect_dict['bbox']['x0'] + rect_dict['bbox']['x1']) / 2,
                                y=(rect_dict['bbox']['y0'] + rect_dict['bbox']['y1']) / 2
                            ),
                            'bbox': BoundingBox(
                                x0=rect_dict['bbox']['x0'],
                                y0=rect_dict['bbox']['y0'],
                                x1=rect_dict['bbox']['x1'],
                                y1=rect_dict['bbox']['y1']
                            )
                        })
                    
                    for poly_dict in result.get('polygons', []):
                        shapes.append({
                            'type': 'polygon',
                            'page_number': page_num,
                            'data': poly_dict,
                            'center': Point(
                                x=poly_dict['bbox']['center']['x'],
                                y=poly_dict['bbox']['center']['y']
                            ),
                            'bbox': BoundingBox(
                                x0=poly_dict['bbox']['x0'],
                                y0=poly_dict['bbox']['y0'],
                                x1=poly_dict['bbox']['x1'],
                                y1=poly_dict['bbox']['y1']
                            )
                        })
            
            return {
                'success': True,
                'shapes': shapes
            }
            
        except Exception as e:
            logger.error(f"Shape detection failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'shapes': []
            }
    
    def _associate_text_and_shapes(self, text_elements: List[Dict], shapes: List[Dict]) -> List[IntegratedElement]:
        """Associate text elements with nearby shapes"""
        integrated = []
        used_shapes = set()
        
        for text_elem in text_elements:
            text_pos = text_elem['position']
            text_page = text_elem['page_number']
            
            # Find nearest shape on same page
            nearest_shape = None
            nearest_distance = float('inf')
            nearest_idx = None
            
            for idx, shape in enumerate(shapes):
                if idx in used_shapes:
                    continue
                    
                if shape['page_number'] != text_page:
                    continue
                
                # Calculate distance between text and shape center
                shape_center = shape['center']
                distance = math.sqrt(
                    (text_pos.x - shape_center.x)**2 + 
                    (text_pos.y - shape_center.y)**2
                )
                
                if distance < nearest_distance and distance <= self.max_distance:
                    nearest_distance = distance
                    nearest_shape = shape
                    nearest_idx = idx
            
            # Create integrated element
            if nearest_shape or not self.require_shape:
                if nearest_idx is not None:
                    used_shapes.add(nearest_idx)
                
                distance_mm = nearest_distance / 2.834645 if nearest_shape else 0
                
                integrated.append(IntegratedElement(
                    element_id=text_elem['element_id'],
                    element_type=text_elem['element_type'],
                    text_bbox=text_elem['bbox'],
                    text_position=text_elem['position'],
                    shape=nearest_shape['data'] if nearest_shape else None,
                    shape_bbox=nearest_shape['bbox'] if nearest_shape else None,
                    distance_mm=distance_mm,
                    confidence=text_elem['confidence'],
                    page_number=text_elem['page_number']
                ))
                
                if nearest_shape:
                    logger.debug(f"   Associated {text_elem['element_id']} with "
                               f"{nearest_shape['type']} (distance: {distance_mm:.1f}mm)")
                else:
                    logger.debug(f"   No shape found for {text_elem['element_id']}")
        
        return integrated


def main():
    """Test the integrated detector"""
    import sys
    
    pdf_path = '/app/backend/rag_service/tests/7_FLETT_RD.pdf'
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    
    print("="*80)
    print("INTEGRATED ELEMENT DETECTOR TEST")
    print("="*80 + "\n")
    
    detector = IntegratedElementDetector(
        max_distance_mm=50.0,
        require_shape=False
    )
    
    result = detector.detect_elements(pdf_path)
    
    if result['success']:
        print("\n" + "="*80)
        print("DETECTED ELEMENTS:")
        print("="*80)
        
        for elem in result['elements']:
            shape_info = f"{elem['shape']['type']}" if elem.get('shape') else "no shape"
            print(f"   {elem['element_id']} ({elem['element_type']}): {shape_info}, "
                  f"distance: {elem['distance_mm']:.1f}mm")
        
        print("\n" + "="*80)
        print("STATISTICS:")
        print("="*80)
        stats = result['statistics']
        print(f"   Total elements: {stats['total_elements']}")
        print(f"   With shapes: {stats['with_shapes']}")
        print(f"   Without shapes: {stats['without_shapes']}")
        print(f"   Text elements found: {stats['total_text_elements']}")
        print(f"   Shapes detected: {stats['total_shapes']}")
        print("="*80 + "\n")
    else:
        print(f"\n❌ Detection failed: {result.get('error')}")


if __name__ == '__main__':
    main()
