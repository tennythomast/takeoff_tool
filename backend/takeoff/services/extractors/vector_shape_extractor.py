import fitz  # PyMuPDF
from typing import List, Dict, Tuple, Optional
import logging
from dataclasses import dataclass

from takeoff.shapes import (
    Circle, Rectangle, Polygon, Point, BoundingBox,
    ShapeStyle, LineStyle, Shape
)
from .line_shape_detector import LineBasedShapeDetector

logger = logging.getLogger(__name__)

@dataclass
class ShapeExtractionConfig:
    """Configuration for shape extraction and filtering"""
    
    # Size filters (in mm)
    min_circle_diameter_mm: float = 10.0
    max_circle_diameter_mm: float = 50.0
    min_rectangle_width_mm: float = 10.0
    max_rectangle_width_mm: float = 60.0
    min_rectangle_height_mm: float = 10.0
    max_rectangle_height_mm: float = 60.0
    min_rectangle_aspect_ratio: float = 0.3
    max_rectangle_aspect_ratio: float = 3.0
    
    # Style filters
    min_stroke_width: float = 0.5  # points
    max_stroke_width: float = 6.0  # points
    require_solid_lines: bool = True
    allow_fills: bool = True
    max_stroke_lightness: float = 0.5  # 0=black, 1=white
    
    # Polygon filters
    min_polygon_vertices: int = 3
    max_polygon_vertices: int = 12
    
    # Detection sensitivity
    circle_tolerance: float = 0.1  # How close to perfect circle
    rectangle_tolerance: float = 5.0  # Angle tolerance for rectangles (degrees)

class VectorShapeExtractor:
    """
    Extracts vector shapes (circles, rectangles, polygons) from PDF pages
    with filtering for engineering element symbols
    """
    
    def __init__(self, config: ShapeExtractionConfig = None):
        self.config = config or ShapeExtractionConfig()
        self._mm_to_points = 2.834645  # Conversion factor
    
    def extract_from_file(self, file_path: str) -> Dict:
        """
        Extract shapes from PDF file
        
        Returns:
            Dictionary with shapes organized by page
        """
        try:
            doc = fitz.open(file_path)
            result = {
                'success': True,
                'file_path': file_path,
                'total_pages': len(doc),
                'pages': []
            }
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_shapes = self._extract_page_shapes(page, page_num + 1)
                result['pages'].append(page_shapes)
            
            doc.close()
            
            # Add statistics
            result['statistics'] = self._calculate_statistics(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting shapes from {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path
            }
    
    def _extract_page_shapes(self, page: fitz.Page, page_number: int) -> Dict:
        """Extract shapes from a single page"""
        page_rect = page.rect
        
        shapes_data = {
            'page_number': page_number,
            'page_size': {
                'width': page_rect.width,
                'height': page_rect.height
            },
            'circles': [],
            'rectangles': [],
            'polygons': [],
            'all_shapes': []
        }
        
        # Get all drawing paths from the page
        drawings = page.get_drawings()
        
        logger.info(f"Page {page_number}: Found {len(drawings)} drawing objects")
        
        for drawing in drawings:
            try:
                # Extract style information
                style = self._extract_style(drawing)
                
                # Skip if style doesn't match element symbols
                if not self._is_valid_element_style(style):
                    continue
                
                # Analyze the path items
                items = drawing.get('items', [])
                shape = self._analyze_path(items, style, page_number)
                
                if shape:
                    # Add to appropriate category
                    shape_dict = shape.to_dict()
                    if isinstance(shape, Circle):
                        shapes_data['circles'].append(shape_dict)
                    elif isinstance(shape, Rectangle):
                        shapes_data['rectangles'].append(shape_dict)
                    elif isinstance(shape, Polygon):
                        shapes_data['polygons'].append(shape_dict)
                    
                    shapes_data['all_shapes'].append(shape)
                    
            except Exception as e:
                logger.warning(f"Error processing drawing: {e}")
                continue
        
        logger.info(f"Page {page_number}: Extracted {len(shapes_data['circles'])} circles, "
                   f"{len(shapes_data['rectangles'])} rectangles, "
                   f"{len(shapes_data['polygons'])} polygons")
        
        return shapes_data
    
    def _extract_style(self, drawing: Dict) -> ShapeStyle:
        """Extract style information from drawing object"""
        # Get stroke color (default to black)
        color = drawing.get('color', [0, 0, 0])
        if isinstance(color, (list, tuple)) and len(color) >= 3:
            stroke_color = tuple(color[:3])
        else:
            stroke_color = (0, 0, 0)
        
        # Get fill color
        fill = drawing.get('fill', None)
        if fill and isinstance(fill, (list, tuple)) and len(fill) >= 3:
            fill_color = tuple(fill[:3])
        else:
            fill_color = None
        
        # Get stroke width
        width = drawing.get('width', 1.0)
        
        # Detect line style (simplified - PyMuPDF doesn't always provide this)
        dashes = drawing.get('dashes', None)
        if dashes and len(dashes) > 0:
            line_style = LineStyle.DASHED
        else:
            line_style = LineStyle.SOLID
        
        return ShapeStyle(
            stroke_width=width,
            stroke_color=stroke_color,
            fill_color=fill_color,
            line_style=line_style
        )
    
    def _is_valid_element_style(self, style: ShapeStyle) -> bool:
        """Check if style is appropriate for element symbols"""
        # Check stroke width
        if style.stroke_width is None:
            return False
        if not (self.config.min_stroke_width <= style.stroke_width <= self.config.max_stroke_width):
            return False
        
        # Require solid lines if configured
        if self.config.require_solid_lines and style.line_style != LineStyle.SOLID:
            return False
        
        # Check stroke color (should be dark)
        r, g, b = style.stroke_color
        lightness = (r + g + b) / 3
        if lightness > self.config.max_stroke_lightness:
            return False
        
        return True
    
    def _analyze_path(self, items: List, style: ShapeStyle, page_number: int) -> Optional[Shape]:
        """Analyze path items to detect shape type"""
        if not items:
            return None
        
        # Try to detect circle
        circle = self._detect_circle(items, style, page_number)
        if circle:
            return circle
        
        # Try to detect rectangle
        rectangle = self._detect_rectangle(items, style, page_number)
        if rectangle:
            return rectangle
        
        # Try to detect polygon
        polygon = self._detect_polygon(items, style, page_number)
        if polygon:
            return polygon
        
        return None
    
    def _detect_circle(self, items: List, style: ShapeStyle, page_number: int) -> Optional[Circle]:
        """Detect if path items form a circle"""
        # Look for curve items that form a circle
        # PyMuPDF represents circles as 4 Bezier curves
        
        curves = [item for item in items if item[0] == 'c']
        
        if len(curves) != 4:
            return None
        
        # Get all points from curves
        points = []
        for curve in curves:
            # curve = ('c', p1, p2, p3, p4)
            # p1 = start, p2/p3 = control points, p4 = end
            if len(curve) >= 5:
                points.extend([curve[1], curve[4]])
        
        if not points:
            return None
        
        # Calculate center as average of all points
        center_x = sum(p.x for p in points) / len(points)
        center_y = sum(p.y for p in points) / len(points)
        center = Point(center_x, center_y)
        
        # Calculate radius as average distance from center
        distances = [((p.x - center_x)**2 + (p.y - center_y)**2)**0.5 for p in points]
        avg_radius = sum(distances) / len(distances)
        
        # Check if points are approximately equidistant (circle test)
        max_deviation = max(abs(d - avg_radius) for d in distances)
        if max_deviation / avg_radius > self.config.circle_tolerance:
            return None
        
        # Create circle object
        circle = Circle(
            center=center,
            radius=avg_radius,
            style=style,
            page_number=page_number
        )
        
        # Apply size filters
        if not self._is_valid_circle_size(circle):
            return None
        
        return circle
    
    def _detect_rectangle(self, items: List, style: ShapeStyle, page_number: int) -> Optional[Rectangle]:
        """Detect if path items form a rectangle"""
        # Look for 4 line segments forming a rectangle
        lines = [item for item in items if item[0] == 'l']
        
        if len(lines) != 4:
            return None
        
        # Get all unique points
        points = []
        for line in lines:
            # line = ('l', p1, p2)
            if len(line) >= 3:
                points.extend([line[1], line[2]])
        
        if len(points) < 4:
            return None
        
        # Calculate bounding box
        x_coords = [p.x for p in points]
        y_coords = [p.y for p in points]
        
        bbox = BoundingBox(
            x0=min(x_coords),
            y0=min(y_coords),
            x1=max(x_coords),
            y1=max(y_coords)
        )
        
        # Check if lines are approximately horizontal/vertical (rectangle test)
        # This is a simplified check - a more robust version would check angles
        
        # Create rectangle object
        rectangle = Rectangle(
            bbox=bbox,
            style=style,
            page_number=page_number
        )
        
        # Apply size filters
        if not self._is_valid_rectangle_size(rectangle):
            return None
        
        return rectangle
    
    def _detect_polygon(self, items: List, style: ShapeStyle, page_number: int) -> Optional[Polygon]:
        """Detect polygon from path items"""
        # Get all line segments
        lines = [item for item in items if item[0] == 'l']
        
        vertex_count = len(lines)
        
        # Filter by vertex count
        if not (self.config.min_polygon_vertices <= vertex_count <= self.config.max_polygon_vertices):
            return None
        
        # Exclude triangles and quadrilaterals (handled separately)
        if vertex_count < 5:
            return None
        
        # Extract vertices
        vertices = []
        for line in lines:
            if len(line) >= 2:
                vertices.append(line[1])
        
        if len(vertices) < self.config.min_polygon_vertices:
            return None
        
        # Create polygon object
        polygon = Polygon(
            vertices=vertices,
            style=style,
            page_number=page_number
        )
        
        # Apply size filters (check bounding box)
        bbox = polygon.bbox
        width_mm = bbox.width / self._mm_to_points
        height_mm = bbox.height / self._mm_to_points
        
        if (width_mm < self.config.min_rectangle_width_mm or 
            width_mm > self.config.max_rectangle_width_mm or
            height_mm < self.config.min_rectangle_height_mm or
            height_mm > self.config.max_rectangle_height_mm):
            return None
        
        return polygon
    
    def _is_valid_circle_size(self, circle: Circle) -> bool:
        """Check if circle size is within valid range for element symbols"""
        diameter_mm = circle.diameter_mm
        return (self.config.min_circle_diameter_mm <= diameter_mm <= 
                self.config.max_circle_diameter_mm)
    
    def _is_valid_rectangle_size(self, rectangle: Rectangle) -> bool:
        """Check if rectangle size is within valid range for element symbols"""
        width_mm = rectangle.width_mm
        height_mm = rectangle.height_mm
        aspect_ratio = rectangle.aspect_ratio
        
        # Check dimensions
        if (width_mm < self.config.min_rectangle_width_mm or 
            width_mm > self.config.max_rectangle_width_mm):
            return False
        
        if (height_mm < self.config.min_rectangle_height_mm or 
            height_mm > self.config.max_rectangle_height_mm):
            return False
        
        # Check aspect ratio
        if (aspect_ratio < self.config.min_rectangle_aspect_ratio or 
            aspect_ratio > self.config.max_rectangle_aspect_ratio):
            return False
        
        return True
    
    def _calculate_statistics(self, result: Dict) -> Dict:
        """Calculate statistics about extracted shapes"""
        stats = {
            'total_circles': 0,
            'total_rectangles': 0,
            'total_polygons': 0,
            'total_shapes': 0,
            'pages_processed': len(result.get('pages', []))
        }
        
        for page_data in result.get('pages', []):
            stats['total_circles'] += len(page_data.get('circles', []))
            stats['total_rectangles'] += len(page_data.get('rectangles', []))
            stats['total_polygons'] += len(page_data.get('polygons', []))
        
        stats['total_shapes'] = (stats['total_circles'] + 
                                stats['total_rectangles'] + 
                                stats['total_polygons'])
        
        return stats