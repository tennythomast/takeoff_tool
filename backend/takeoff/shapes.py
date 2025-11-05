"""
Shape and Element Detection Models

These are dataclass models used for vector shape extraction and element detection.
They are separate from Django models to avoid conflicts.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Union
from datetime import datetime
from enum import Enum

# ============================================================================
# Shape Models
# ============================================================================

class ShapeType(Enum):
    CIRCLE = "circle"
    RECTANGLE = "rectangle"
    SQUARE = "square"
    POLYGON = "polygon"
    ELLIPSE = "ellipse"
    UNKNOWN = "unknown"

class LineStyle(Enum):
    SOLID = "solid"
    DASHED = "dashed"
    DOTTED = "dotted"
    DASH_DOT = "dash_dot"

@dataclass
class Point:
    x: float
    y: float
    
    def distance_to(self, other: 'Point') -> float:
        """Calculate Euclidean distance to another point"""
        return ((self.x - other.x)**2 + (self.y - other.y)**2)**0.5

@dataclass
class BoundingBox:
    x0: float
    y0: float
    x1: float
    y1: float
    
    @property
    def width(self) -> float:
        return abs(self.x1 - self.x0)
    
    @property
    def height(self) -> float:
        return abs(self.y1 - self.y0)
    
    @property
    def center(self) -> Point:
        return Point(
            x=(self.x0 + self.x1) / 2,
            y=(self.y0 + self.y1) / 2
        )
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    @property
    def diagonal(self) -> float:
        return (self.width**2 + self.height**2)**0.5
    
    def contains_point(self, point: Point) -> bool:
        """Check if a point is inside this bounding box"""
        return (self.x0 <= point.x <= self.x1 and 
                self.y0 <= point.y <= self.y1)
    
    def to_dict(self) -> dict:
        return {
            'x0': self.x0,
            'y0': self.y0,
            'x1': self.x1,
            'y1': self.y1,
            'width': self.width,
            'height': self.height,
            'center': {'x': self.center.x, 'y': self.center.y}
        }

@dataclass
class ShapeStyle:
    stroke_width: float
    stroke_color: Tuple[float, float, float]  # RGB 0-1
    fill_color: Optional[Tuple[float, float, float]] = None
    line_style: LineStyle = LineStyle.SOLID
    opacity: float = 1.0
    
    def is_valid_element_style(self) -> bool:
        """Check if this style is typical for element symbols"""
        # Element symbols typically have:
        # - Medium stroke width (1-6 points)
        # - Solid lines
        # - Dark stroke color
        
        if not (1.0 <= self.stroke_width <= 6.0):
            return False
        
        if self.line_style != LineStyle.SOLID:
            return False
        
        # Check stroke color (should be dark)
        r, g, b = self.stroke_color
        avg_color = (r + g + b) / 3
        if avg_color > 0.5:  # Too light
            return False
        
        return True

@dataclass
class Circle:
    center: Point
    radius: float
    style: ShapeStyle
    page_number: int
    
    @property
    def bbox(self) -> BoundingBox:
        return BoundingBox(
            x0=self.center.x - self.radius,
            y0=self.center.y - self.radius,
            x1=self.center.x + self.radius,
            y1=self.center.y + self.radius
        )
    
    @property
    def diameter(self) -> float:
        return self.radius * 2
    
    @property
    def diameter_mm(self) -> float:
        """Convert diameter from points to mm"""
        return self.diameter / 2.834645
    
    def contains_point(self, point: Point) -> bool:
        """Check if point is inside circle"""
        return self.center.distance_to(point) <= self.radius
    
    def distance_to_point(self, point: Point) -> float:
        """Distance from circle edge to point"""
        return abs(self.center.distance_to(point) - self.radius)
    
    def to_dict(self) -> dict:
        return {
            'type': 'circle',
            'center': {'x': self.center.x, 'y': self.center.y},
            'radius': self.radius,
            'diameter': self.diameter,
            'diameter_mm': self.diameter_mm,
            'bbox': self.bbox.to_dict(),
            'style': {
                'stroke_width': self.style.stroke_width,
                'stroke_color': self.style.stroke_color,
                'fill_color': self.style.fill_color,
                'line_style': self.style.line_style.value
            },
            'page_number': self.page_number
        }

@dataclass
class Rectangle:
    bbox: BoundingBox
    style: ShapeStyle
    page_number: int
    rounded_corners: bool = False
    
    @property
    def center(self) -> Point:
        return self.bbox.center
    
    @property
    def width(self) -> float:
        return self.bbox.width
    
    @property
    def height(self) -> float:
        return self.bbox.height
    
    @property
    def width_mm(self) -> float:
        return self.width / 2.834645
    
    @property
    def height_mm(self) -> float:
        return self.height / 2.834645
    
    @property
    def aspect_ratio(self) -> float:
        """Width / Height ratio"""
        return self.width / self.height if self.height > 0 else 0
    
    @property
    def is_square(self) -> bool:
        """Check if rectangle is approximately square"""
        return 0.9 <= self.aspect_ratio <= 1.1
    
    def contains_point(self, point: Point) -> bool:
        """Check if point is inside rectangle"""
        return self.bbox.contains_point(point)
    
    def distance_to_point(self, point: Point) -> float:
        """Minimum distance from rectangle edge to point"""
        if self.contains_point(point):
            return 0.0
        
        dx = max(self.bbox.x0 - point.x, 0, point.x - self.bbox.x1)
        dy = max(self.bbox.y0 - point.y, 0, point.y - self.bbox.y1)
        return (dx**2 + dy**2)**0.5
    
    def to_dict(self) -> dict:
        return {
            'type': 'rectangle' if not self.is_square else 'square',
            'bbox': self.bbox.to_dict(),
            'width': self.width,
            'height': self.height,
            'width_mm': self.width_mm,
            'height_mm': self.height_mm,
            'aspect_ratio': self.aspect_ratio,
            'is_square': self.is_square,
            'rounded_corners': self.rounded_corners,
            'style': {
                'stroke_width': self.style.stroke_width,
                'stroke_color': self.style.stroke_color,
                'fill_color': self.style.fill_color,
                'line_style': self.style.line_style.value
            },
            'page_number': self.page_number
        }

@dataclass
class Polygon:
    vertices: List[Point]
    style: ShapeStyle
    page_number: int
    
    @property
    def vertex_count(self) -> int:
        return len(self.vertices)
    
    @property
    def bbox(self) -> BoundingBox:
        x_coords = [v.x for v in self.vertices]
        y_coords = [v.y for v in self.vertices]
        return BoundingBox(
            x0=min(x_coords),
            y0=min(y_coords),
            x1=max(x_coords),
            y1=max(y_coords)
        )
    
    @property
    def center(self) -> Point:
        return self.bbox.center
    
    @property
    def shape_type(self) -> str:
        """Classify polygon by vertex count"""
        if self.vertex_count == 3:
            return "triangle"
        elif self.vertex_count == 5:
            return "pentagon"
        elif self.vertex_count == 6:
            return "hexagon"
        elif self.vertex_count == 8:
            return "octagon"
        else:
            return f"polygon_{self.vertex_count}"
    
    def contains_point(self, point: Point) -> bool:
        """Check if point is inside polygon using ray casting"""
        x, y = point.x, point.y
        n = len(self.vertices)
        inside = False
        
        p1 = self.vertices[0]
        for i in range(1, n + 1):
            p2 = self.vertices[i % n]
            if y > min(p1.y, p2.y):
                if y <= max(p1.y, p2.y):
                    if x <= max(p1.x, p2.x):
                        if p1.y != p2.y:
                            xinters = (y - p1.y) * (p2.x - p1.x) / (p2.y - p1.y) + p1.x
                        if p1.x == p2.x or x <= xinters:
                            inside = not inside
            p1 = p2
        
        return inside
    
    def distance_to_point(self, point: Point) -> float:
        """Approximate distance from polygon edge to point"""
        if self.contains_point(point):
            return 0.0
        
        # Use bounding box as approximation
        return Rectangle(
            bbox=self.bbox,
            style=self.style,
            page_number=self.page_number
        ).distance_to_point(point)
    
    def to_dict(self) -> dict:
        return {
            'type': 'polygon',
            'shape_type': self.shape_type,
            'vertex_count': self.vertex_count,
            'vertices': [{'x': v.x, 'y': v.y} for v in self.vertices],
            'bbox': self.bbox.to_dict(),
            'style': {
                'stroke_width': self.style.stroke_width,
                'stroke_color': self.style.stroke_color,
                'fill_color': self.style.fill_color,
                'line_style': self.style.line_style.value
            },
            'page_number': self.page_number
        }

# Union type for all shapes (Python 3.9 compatible)
Shape = Union[Circle, Rectangle, Polygon]

# ============================================================================
# Element Models
# ============================================================================

class ElementType(Enum):
    # Structural
    BORED_PIER = "bored_pier"
    PAD_FOOTING = "pad_footing"
    STRIP_FOOTING = "strip_footing"
    COLUMN = "column"
    BEAM = "beam"
    PILE = "pile"
    
    # Architectural
    DOOR = "door"
    WINDOW = "window"
    ROOM = "room"
    
    # MEP
    EQUIPMENT = "equipment"
    FIXTURE = "fixture"
    OUTLET = "outlet"
    
    # Civil
    MANHOLE = "manhole"
    CATCH_BASIN = "catch_basin"
    VALVE = "valve"
    
    # Generic
    UNKNOWN = "unknown"

class TextPosition(Enum):
    INSIDE = "inside"          # Text center inside shape
    NEAR = "near"             # Text near shape (< 10mm)
    LEADER = "leader"         # Text connected by leader line
    DISTANT = "distant"       # Text too far, low confidence

@dataclass
class ElementPattern:
    """Regex patterns for different element ID types"""
    pattern: str
    element_type: ElementType
    description: str
    
    def matches(self, text: str) -> bool:
        import re
        return bool(re.match(self.pattern, text, re.IGNORECASE))

# Common element ID patterns
ELEMENT_PATTERNS = [
    # Structural - Piers/Piles
    ElementPattern(r'^BP\d+$', ElementType.BORED_PIER, "Bored Pier (BP1, BP2, etc.)"),
    ElementPattern(r'^P\d+$', ElementType.PILE, "Pile (P1, P2, etc.)"),
    
    # Structural - Footings
    ElementPattern(r'^PF\d+$', ElementType.PAD_FOOTING, "Pad Footing (PF1, PF2, etc.)"),
    ElementPattern(r'^SF\d+$', ElementType.STRIP_FOOTING, "Strip Footing (SF1, SF2, etc.)"),
    ElementPattern(r'^F\d+$', ElementType.PAD_FOOTING, "Footing (F1, F2, etc.)"),
    
    # Structural - Columns/Beams
    ElementPattern(r'^C\d+$', ElementType.COLUMN, "Column (C1, C2, etc.)"),
    ElementPattern(r'^B\d+$', ElementType.BEAM, "Beam (B1, B2, etc.)"),
    
    # Architectural
    ElementPattern(r'^D\d+$', ElementType.DOOR, "Door (D1, D2, etc.)"),
    ElementPattern(r'^W\d+$', ElementType.WINDOW, "Window (W1, W2, etc.)"),
    ElementPattern(r'^\d{3}$', ElementType.ROOM, "Room number (101, 102, etc.)"),
    
    # MEP
    ElementPattern(r'^EQ-?\d+$', ElementType.EQUIPMENT, "Equipment (EQ1, EQ-1, etc.)"),
    ElementPattern(r'^[A-Z]{2,4}-?\d+$', ElementType.EQUIPMENT, "Equipment tag (HVAC-1, AHU1, etc.)"),
    
    # Civil
    ElementPattern(r'^MH-?\d+$', ElementType.MANHOLE, "Manhole (MH1, MH-1, etc.)"),
    ElementPattern(r'^CB-?\d+$', ElementType.CATCH_BASIN, "Catch Basin (CB1, CB-1, etc.)"),
    ElementPattern(r'^V-?\d+$', ElementType.VALVE, "Valve (V1, V-1, etc.)"),
]

@dataclass
class TextShapeAssociation:
    """Association between text instance and shape"""
    text_instance: Dict  # From vector text extractor
    shape: Shape
    position: TextPosition
    distance: float  # Distance from shape to text center (in points)
    confidence: float  # 0.0 to 1.0
    
    @property
    def text(self) -> str:
        return self.text_instance.get('text', '')
    
    @property
    def text_center(self) -> Point:
        center = self.text_instance.get('center', {})
        return Point(x=center.get('x', 0), y=center.get('y', 0))
    
    def to_dict(self) -> dict:
        return {
            'text': self.text,
            'text_bbox': self.text_instance.get('bbox'),
            'text_center': {'x': self.text_center.x, 'y': self.text_center.y},
            'shape': self.shape.to_dict(),
            'position': self.position.value,
            'distance': self.distance,
            'distance_mm': self.distance / 2.834645,
            'confidence': self.confidence
        }

@dataclass
class DetectedElement:
    """A detected element with shape and label"""
    element_id: str
    element_type: ElementType
    location: Point
    shape: Shape
    associations: List[TextShapeAssociation]
    page_number: int
    confidence: float = 1.0
    metadata: Dict = field(default_factory=dict)
    
    @property
    def primary_text(self) -> str:
        """Get the primary text label (usually the element ID)"""
        if self.associations:
            return max(self.associations, key=lambda a: a.confidence).text
        return self.element_id
    
    @property
    def shape_type(self) -> str:
        if hasattr(self.shape, 'shape_type'):
            return self.shape.shape_type
        return self.shape.to_dict()['type']
    
    def to_dict(self) -> dict:
        return {
            'element_id': self.element_id,
            'element_type': self.element_type.value,
            'location': {'x': self.location.x, 'y': self.location.y},
            'shape': self.shape.to_dict(),
            'shape_type': self.shape_type,
            'associations': [a.to_dict() for a in self.associations],
            'page_number': self.page_number,
            'confidence': self.confidence,
            'metadata': self.metadata
        }

def classify_element_by_text(text: str) -> ElementType:
    """Classify element type based on text pattern"""
    for pattern in ELEMENT_PATTERNS:
        if pattern.matches(text):
            return pattern.element_type
    return ElementType.UNKNOWN

def classify_element_by_shape(shape: Shape, text: str = None) -> ElementType:
    """Classify element type based on shape and optional text"""
    shape_dict = shape.to_dict()
    shape_type = shape_dict['type']
    
    # First, try text-based classification if available
    if text:
        text_type = classify_element_by_text(text)
        if text_type != ElementType.UNKNOWN:
            return text_type
    
    # Fallback to shape-based heuristics
    if shape_type == 'circle':
        diameter_mm = shape_dict.get('diameter_mm', 0)
        if diameter_mm > 30:
            return ElementType.BORED_PIER
        elif diameter_mm > 20:
            return ElementType.COLUMN
        else:
            return ElementType.PILE
    
    elif shape_type in ['rectangle', 'square']:
        width_mm = shape_dict.get('width_mm', 0)
        height_mm = shape_dict.get('height_mm', 0)
        is_square = shape_dict.get('is_square', False)
        
        if is_square and width_mm < 40:
            return ElementType.PAD_FOOTING
        elif width_mm > 50:
            return ElementType.EQUIPMENT
        else:
            return ElementType.PAD_FOOTING
    
    elif shape_type == 'hexagon':
        return ElementType.STRIP_FOOTING
    
    return ElementType.UNKNOWN

# ============================================================================
# Extraction Result Models
# ============================================================================

@dataclass
class PageShapes:
    """Shapes extracted from a single page"""
    page_number: int
    page_size: Dict[str, float]
    circles: List[Dict]
    rectangles: List[Dict]
    polygons: List[Dict]
    total_shapes: int = 0
    
    def __post_init__(self):
        self.total_shapes = len(self.circles) + len(self.rectangles) + len(self.polygons)

@dataclass
class PageElements:
    """Elements detected on a single page"""
    page_number: int
    elements: List[Dict]
    element_counts: Dict[str, int] = field(default_factory=dict)
    
    def __post_init__(self):
        # Calculate element counts
        for element in self.elements:
            element_id = element.get('element_id')
            if element_id:
                self.element_counts[element_id] = self.element_counts.get(element_id, 0) + 1

@dataclass
class ElementCount:
    """Count summary for a specific element ID"""
    element_id: str
    count: int
    element_type: str
    occurrences: List[Dict]  # List of locations where element appears
    
    def to_dict(self) -> dict:
        return {
            'element_id': self.element_id,
            'count': self.count,
            'element_type': self.element_type,
            'occurrences': self.occurrences
        }

@dataclass
class ExtractionResult:
    """Complete extraction result"""
    success: bool
    file_path: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    total_pages: int = 0
    pages: List[PageElements] = field(default_factory=list)
    summary: Dict = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'success': self.success,
            'file_path': self.file_path,
            'timestamp': self.timestamp,
            'total_pages': self.total_pages,
            'pages': [
                {
                    'page_number': p.page_number,
                    'elements': p.elements,
                    'element_counts': p.element_counts
                }
                for p in self.pages
            ],
            'summary': self.summary,
            'error': self.error
        }
