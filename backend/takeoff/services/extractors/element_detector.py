"""
Element Detector - Combines shape extraction and text extraction
to detect engineering drawing elements
"""

import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from takeoff.models.shapes import Shape, Circle, Rectangle, Polygon, Point
from takeoff.models.elements import (
    DetectedElement, TextShapeAssociation, TextPosition,
    ElementType, classify_element_by_text, classify_element_by_shape,
    ELEMENT_PATTERNS
)
from takeoff.models.extraction import ExtractionResult, PageElements, ElementCount

from .vector_text_extractor import VectorTextExtractor
from .vector_shape_extractor import VectorShapeExtractor

logger = logging.getLogger(__name__)

@dataclass
class ElementDetectionConfig:
    """Configuration for element detection"""
    
    # Text-Shape Association thresholds
    inside_shape_confidence: float = 1.0
    near_threshold_mm: float = 10.0  # Maximum distance to consider "near"
    near_confidence_base: float = 0.7
    
    # Text validation
    min_text_font_size: float = 8.0  # Minimum font size for element labels
    max_text_font_size: float = 20.0  # Maximum font size for element labels
    require_bold_text: bool = False  # Some drawings use bold for element IDs
    
    # Element filtering
    min_element_confidence: float = 0.5  # Minimum confidence to include element
    
    # Leader line detection (Phase 2)
    enable_leader_detection: bool = True
    max_leader_length_mm: float = 50.0
    
    # Debug options
    debug_mode: bool = False
    export_debug_data: bool = False

class ElementDetector:
    """
    Detects engineering drawing elements by combining:
    - Vector shape extraction (circles, rectangles, polygons)
    - Text extraction
    - Spatial relationship analysis
    - Pattern matching
    """
    
    def __init__(self, config: ElementDetectionConfig = None):
        self.config = config or ElementDetectionConfig()
        self.text_extractor = VectorTextExtractor()
        self.shape_extractor = VectorShapeExtractor()
        self._mm_to_points = 2.834645
    
    def detect_elements(self, file_path: str) -> ExtractionResult:
        """
        Main entry point: Detect all elements in a PDF file
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            ExtractionResult with detected elements
        """
        try:
            logger.info(f"Starting element detection for: {file_path}")
            
            # Phase 1: Extract shapes and text
            shapes_result = self.shape_extractor.extract_from_file(file_path)
            text_result = self.text_extractor.extract_from_file(file_path)
            
            if not shapes_result['success'] or not text_result['success']:
                return ExtractionResult(
                    success=False,
                    file_path=file_path,
                    error="Failed to extract shapes or text"
                )
            
            # Phase 2: Detect elements page by page
            pages = []
            for page_num in range(shapes_result['total_pages']):
                page_shapes = shapes_result['pages'][page_num]
                page_text = text_result['pages'][page_num]
                
                page_elements = self._detect_page_elements(
                    page_shapes,
                    page_text,
                    page_num + 1
                )
                pages.append(page_elements)
            
            # Phase 3: Generate summary statistics
            summary = self._generate_summary(pages)
            
            result = ExtractionResult(
                success=True,
                file_path=file_path,
                total_pages=shapes_result['total_pages'],
                pages=pages,
                summary=summary
            )
            
            logger.info(f"Element detection complete. Found {summary['total_elements']} elements")
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting elements: {e}", exc_info=True)
            return ExtractionResult(
                success=False,
                file_path=file_path,
                error=str(e)
            )
    
    def _detect_page_elements(
        self,
        page_shapes: Dict,
        page_text: Dict,
        page_number: int
    ) -> PageElements:
        """
        Detect elements on a single page
        
        Process:
        1. Get all shapes from page
        2. Get all text instances from page
        3. For each shape, find associated text
        4. Validate text as element ID
        5. Create DetectedElement objects
        """
        logger.info(f"Processing page {page_number}")
        
        # Get shape objects
        all_shapes = page_shapes.get('all_shapes', [])
        text_instances = page_text.get('text_instances', [])
        
        logger.debug(f"  Shapes: {len(all_shapes)}, Text instances: {len(text_instances)}")
        
        detected_elements = []
        
        # Process each shape
        for shape in all_shapes:
            # Find text associated with this shape
            associations = self._find_text_associations(shape, text_instances)
            
            if not associations:
                logger.debug(f"  Shape at {shape.center.x:.1f}, {shape.center.y:.1f} has no text association")
                continue
            
            # Validate and create element
            element = self._create_element_from_associations(
                shape,
                associations,
                page_number
            )
            
            if element and element.confidence >= self.config.min_element_confidence:
                detected_elements.append(element.to_dict())
        
        logger.info(f"  Found {len(detected_elements)} elements on page {page_number}")
        
        return PageElements(
            page_number=page_number,
            elements=detected_elements
        )
    
    def _find_text_associations(
        self,
        shape: Shape,
        text_instances: List[Dict]
    ) -> List[TextShapeAssociation]:
        """
        Find all text instances associated with a shape
        
        Returns list of TextShapeAssociation objects sorted by confidence
        """
        associations = []
        near_threshold_points = self.config.near_threshold_mm * self._mm_to_points
        
        for text_instance in text_instances:
            # Get text center point
            text_center = Point(
                x=text_instance['center']['x'],
                y=text_instance['center']['y']
            )
            
            # Calculate distance from shape
            distance = self._calculate_distance(shape, text_center)
            
            # Determine position and confidence
            if self._is_text_inside_shape(shape, text_center):
                position = TextPosition.INSIDE
                confidence = self.config.inside_shape_confidence
            elif distance <= near_threshold_points:
                position = TextPosition.NEAR
                # Confidence decreases with distance
                confidence = self.config.near_confidence_base * (
                    1.0 - (distance / near_threshold_points)
                )
            else:
                # Text too far away
                continue
            
            # Validate text as potential element ID
            if not self._is_valid_element_text(text_instance):
                continue
            
            # Create association
            association = TextShapeAssociation(
                text_instance=text_instance,
                shape=shape,
                position=position,
                distance=distance,
                confidence=confidence
            )
            
            associations.append(association)
        
        # Sort by confidence (highest first)
        associations.sort(key=lambda a: a.confidence, reverse=True)
        
        return associations
    
    def _calculate_distance(self, shape: Shape, point: Point) -> float:
        """Calculate distance from shape to point"""
        if isinstance(shape, Circle):
            return shape.distance_to_point(point)
        elif isinstance(shape, (Rectangle, Polygon)):
            return shape.distance_to_point(point)
        else:
            # Fallback: distance to shape center
            return shape.center.distance_to(point)
    
    def _is_text_inside_shape(self, shape: Shape, point: Point) -> bool:
        """Check if point is inside shape"""
        return shape.contains_point(point)
    
    def _is_valid_element_text(self, text_instance: Dict) -> bool:
        """
        Validate if text instance could be an element ID
        
        Checks:
        - Font size in valid range
        - Text matches element pattern
        - Single word/token (not a sentence)
        - Appropriate font style (if configured)
        """
        text = text_instance.get('text', '').strip()
        font_size = text_instance.get('font_size', 0)
        
        # Check font size
        if not (self.config.min_text_font_size <= font_size <= self.config.max_text_font_size):
            return False
        
        # Check if single word
        if ' ' in text or len(text) > 10:  # Element IDs are usually short
            return False
        
        # Check if matches any element pattern
        for pattern in ELEMENT_PATTERNS:
            if pattern.matches(text):
                return True
        
        return False
    
    def _create_element_from_associations(
        self,
        shape: Shape,
        associations: List[TextShapeAssociation],
        page_number: int
    ) -> Optional[DetectedElement]:
        """
        Create a DetectedElement from shape and text associations
        
        Uses the highest-confidence association as the primary element ID
        """
        if not associations:
            return None
        
        # Get primary association (highest confidence)
        primary = associations[0]
        element_id = primary.text
        
        # Classify element type
        element_type = classify_element_by_shape(shape, element_id)
        
        # Overall confidence is based on association confidence
        confidence = primary.confidence
        
        # Create element
        element = DetectedElement(
            element_id=element_id,
            element_type=element_type,
            location=shape.center,
            shape=shape,
            associations=associations,
            page_number=page_number,
            confidence=confidence,
            metadata={
                'shape_size_mm': self._get_shape_size_mm(shape),
                'primary_association': primary.to_dict()
            }
        )
        
        return element
    
    def _get_shape_size_mm(self, shape: Shape) -> Dict:
        """Get shape size in millimeters"""
        shape_dict = shape.to_dict()
        
        if 'diameter_mm' in shape_dict:
            return {'diameter_mm': shape_dict['diameter_mm']}
        elif 'width_mm' in shape_dict:
            return {
                'width_mm': shape_dict['width_mm'],
                'height_mm': shape_dict['height_mm']
            }
        else:
            bbox = shape_dict['bbox']
            return {
                'width_mm': bbox['width'] / self._mm_to_points,
                'height_mm': bbox['height'] / self._mm_to_points
            }
    
    def _generate_summary(self, pages: List[PageElements]) -> Dict:
        """Generate summary statistics"""
        # Count elements by ID
        element_counts = defaultdict(list)
        element_types = defaultdict(int)
        
        for page in pages:
            for element in page.elements:
                element_id = element['element_id']
                element_type = element['element_type']
                
                element_counts[element_id].append({
                    'page': element['page_number'],
                    'location': element['location'],
                    'shape_type': element['shape_type'],
                    'confidence': element['confidence']
                })
                
                element_types[element_type] += 1
        
        # Create ElementCount objects
        counts = []
        for element_id, occurrences in sorted(element_counts.items()):
            counts.append(ElementCount(
                element_id=element_id,
                count=len(occurrences),
                element_type=occurrences[0].get('element', {}).get('element_type', 'unknown'),
                occurrences=occurrences
            ).to_dict())
        
        return {
            'total_elements': sum(len(p.elements) for p in pages),
            'unique_element_ids': len(element_counts),
            'element_counts': counts,
            'element_types': dict(element_types),
            'pages_processed': len(pages)
        }


def find_elements_in_drawing(
    file_path: str,
    element_ids: Optional[List[str]] = None,
    config: ElementDetectionConfig = None
) -> Dict:
    """
    Convenience function to find specific elements in a drawing
    
    Args:
        file_path: Path to PDF file
        element_ids: Optional list of specific element IDs to search for
        config: Optional configuration
        
    Returns:
        Dictionary with element counts and locations
    """
    detector = ElementDetector(config)
    result = detector.detect_elements(file_path)
    
    if not result.success:
        return {
            'success': False,
            'error': result.error
        }
    
    # If specific element IDs requested, filter results
    if element_ids:
        filtered_counts = [
            count for count in result.summary['element_counts']
            if count['element_id'] in element_ids
        ]
        
        return {
            'success': True,
            'file_path': file_path,
            'element_counts': filtered_counts,
            'total_found': sum(c['count'] for c in filtered_counts)
        }
    
    # Return full results
    return {
        'success': True,
        'file_path': file_path,
        'summary': result.summary,
        'pages': [
            {
                'page_number': p.page_number,
                'element_counts': p.element_counts,
                'total_elements': len(p.elements)
            }
            for p in result.pages
        ]
    }