"""
Shape Detection Module

Detects geometric shapes from vector data:
1. Rectangles/Squares from connected line segments
2. Circles from bezier curves
3. Polygons from multi-segment paths
4. Symbols from tiny connected strokes

Combines line detection, arc detection, and stroke connection.
"""

import math
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import fitz  # PyMuPDF

try:
    from .line_detector import LineDetector, ArcDetector, TinyStrokeConnector
except ImportError:
    from line_detector import LineDetector, ArcDetector, TinyStrokeConnector


class ShapeDetector:
    """Main shape detector combining all detection methods"""
    
    def __init__(self):
        """Initialize shape detector with sub-detectors"""
        self.line_detector = LineDetector(min_length_mm=3.0, max_length_mm=150.0)
        self.arc_detector = ArcDetector(min_size_mm=3.0, max_size_mm=150.0)
        self.tiny_stroke_connector = TinyStrokeConnector(tolerance=0.3)  # Tighter tolerance for tiny strokes
        self.PT_TO_MM = 1 / 2.834645
    
    def detect_all_shapes(self, page: fitz.Page) -> Dict[str, List[Dict]]:
        """
        Detect all shapes on a PDF page
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            Dictionary with shape categories and their detections
        """
        # Extract lines and arcs
        all_lines = self.line_detector.extract_lines(page)
        all_arcs = self.arc_detector.extract_arcs(page)
        
        # Filter lines for shape detection
        shape_lines = self.line_detector.filter_by_length(all_lines, 3.0, 150.0)
        
        # Detect shapes
        rectangles = self.detect_rectangles(shape_lines)
        circles = self.detect_circles(all_arcs)
        polygons = self.detect_polygons(shape_lines)
        
        return {
            'rectangles': rectangles,
            'circles': circles,
            'polygons': polygons,
            'total_shapes': len(rectangles) + len(circles) + len(polygons)
        }
    
    def detect_rectangles(self, lines: List[Dict]) -> List[Dict]:
        """
        Detect rectangles from connected line segments
        
        Args:
            lines: List of line dictionaries
            
        Returns:
            List of detected rectangles
        """
        # Build endpoint connections
        endpoint_map = self._build_endpoint_map(lines, tolerance=1.0)
        
        # Find closed paths
        closed_paths = self._find_closed_paths(lines, endpoint_map)
        
        # Filter and classify rectangles
        rectangles = []
        for path in closed_paths:
            rect = self._classify_rectangle(path, lines)
            if rect:
                rectangles.append(rect)
        
        return rectangles
    
    def detect_circles(self, arcs: List[Dict]) -> List[Dict]:
        """
        Detect circles from arc/curve data
        
        Args:
            arcs: List of arc dictionaries
            
        Returns:
            List of detected circles
        """
        circles = []
        
        for arc in arcs:
            if arc['type'] == 'circle':
                diameter_mm = (arc['bbox_width_mm'] + arc['bbox_height_mm']) / 2
                
                circles.append({
                    'type': 'circle',
                    'center': arc['center'],
                    'diameter_mm': diameter_mm,
                    'radius_mm': diameter_mm / 2,
                    'bbox': arc['bbox'],
                    'aspect_ratio': arc['aspect_ratio'],
                    'curve_count': arc['curve_count'],
                    'source': 'bezier_curves'
                })
        
        return circles
    
    def detect_polygons(self, lines: List[Dict]) -> List[Dict]:
        """
        Detect polygons from connected line segments
        
        Args:
            lines: List of line dictionaries
            
        Returns:
            List of detected polygons
        """
        # Build endpoint connections
        endpoint_map = self._build_endpoint_map(lines, tolerance=1.0)
        
        # Find closed paths
        closed_paths = self._find_closed_paths(lines, endpoint_map)
        
        # Filter for polygons (non-rectangular shapes)
        polygons = []
        for path in closed_paths:
            polygon = self._classify_polygon(path, lines)
            if polygon:
                polygons.append(polygon)
        
        return polygons
    
    def detect_symbols_near_labels(
        self, 
        page: fitz.Page,
        label_positions: List[Tuple[float, float]],
        radius_mm: float = 17.0
    ) -> List[Dict]:
        """
        Detect symbols made of tiny strokes near text labels
        
        Args:
            page: PyMuPDF page object
            label_positions: List of (x, y) label positions
            radius_mm: Search radius in millimeters
            
        Returns:
            List of detected symbols
        """
        # Extract all lines including tiny ones
        tiny_detector = LineDetector(min_length_mm=0.05, max_length_mm=2.0)
        all_lines = tiny_detector.extract_lines(page)
        
        # Find symbols near labels
        symbols = self.tiny_stroke_connector.find_symbols_near_labels(
            all_lines, 
            label_positions, 
            radius_mm
        )
        
        return symbols
    
    def _build_endpoint_map(
        self, 
        lines: List[Dict], 
        tolerance: float = 1.0
    ) -> Dict[Tuple[float, float], List[Dict]]:
        """Build endpoint map for line connection"""
        endpoint_map = defaultdict(list)
        precision = 0.1
        
        for i, line in enumerate(lines):
            # Add start point
            start_key = self._round_point(line['x0'], line['y0'], precision)
            endpoint_map[start_key].append({
                'line_idx': i,
                'endpoint': 'start',
                'x': line['x0'],
                'y': line['y0'],
                'other_x': line['x1'],
                'other_y': line['y1']
            })
            
            # Add end point
            end_key = self._round_point(line['x1'], line['y1'], precision)
            endpoint_map[end_key].append({
                'line_idx': i,
                'endpoint': 'end',
                'x': line['x1'],
                'y': line['y1'],
                'other_x': line['x0'],
                'other_y': line['y0']
            })
        
        return endpoint_map
    
    def _round_point(self, x: float, y: float, precision: float) -> Tuple[float, float]:
        """Round point to precision"""
        return (round(x / precision) * precision, round(y / precision) * precision)
    
    def _points_match(self, x1: float, y1: float, x2: float, y2: float, tolerance: float) -> bool:
        """Check if points match within tolerance"""
        return abs(x1 - x2) <= tolerance and abs(y1 - y2) <= tolerance
    
    def _find_closed_paths(
        self, 
        lines: List[Dict], 
        endpoint_map: Dict,
        max_depth: int = 20
    ) -> List[List[int]]:
        """Find all closed paths from line connections"""
        closed_paths = []
        processed = set()
        
        for i in range(len(lines)):
            if i in processed:
                continue
            
            path = self._find_closed_path(i, lines, endpoint_map, max_depth)
            
            if path and len(path) >= 3:
                for line_idx in path:
                    processed.add(line_idx)
                closed_paths.append(path)
        
        return closed_paths
    
    def _find_closed_path(
        self, 
        start_line_idx: int, 
        lines: List[Dict], 
        endpoint_map: Dict,
        max_depth: int,
        tolerance: float = 1.0
    ) -> Optional[List[int]]:
        """Find a closed path starting from a line"""
        visited = set()
        path = [start_line_idx]
        visited.add(start_line_idx)
        
        current_x = lines[start_line_idx]['x1']
        current_y = lines[start_line_idx]['y1']
        start_x = lines[start_line_idx]['x0']
        start_y = lines[start_line_idx]['y0']
        
        for depth in range(max_depth):
            current_key = self._round_point(current_x, current_y, 0.1)
            candidates = endpoint_map.get(current_key, [])
            
            next_line = None
            for candidate in candidates:
                line_idx = candidate['line_idx']
                if line_idx in visited:
                    continue
                if self._points_match(candidate['x'], candidate['y'], current_x, current_y, tolerance):
                    next_line = candidate
                    break
            
            if next_line is None:
                if self._points_match(current_x, current_y, start_x, start_y, tolerance):
                    return path
                else:
                    return None
            
            path.append(next_line['line_idx'])
            visited.add(next_line['line_idx'])
            current_x = next_line['other_x']
            current_y = next_line['other_y']
            
            if self._points_match(current_x, current_y, start_x, start_y, tolerance):
                return path
        
        return None
    
    def _classify_rectangle(self, path: List[int], lines: List[Dict]) -> Optional[Dict]:
        """Classify a closed path as a rectangle"""
        # Only consider 4-segment paths
        if len(path) != 4:
            return None
        
        path_lines = [lines[idx] for idx in path]
        
        # Calculate bounding box
        all_x = []
        all_y = []
        for line in path_lines:
            all_x.extend([line['x0'], line['x1']])
            all_y.extend([line['y0'], line['y1']])
        
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        
        width = max_x - min_x
        height = max_y - min_y
        width_mm = width * self.PT_TO_MM
        height_mm = height * self.PT_TO_MM
        
        # Filter by size
        if width_mm < 3 or height_mm < 3:
            return None
        if width_mm > 200 or height_mm > 200:
            return None
        
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        aspect_ratio = width / height if height > 0 else 0
        is_square = 0.9 <= aspect_ratio <= 1.1
        
        return {
            'type': 'square' if is_square else 'rectangle',
            'bbox': (min_x, min_y, max_x, max_y),
            'center': (center_x, center_y),
            'width_mm': width_mm,
            'height_mm': height_mm,
            'aspect_ratio': aspect_ratio,
            'segments': len(path),
            'path_indices': path,
            'source': 'connected_lines'
        }
    
    def _classify_polygon(self, path: List[int], lines: List[Dict]) -> Optional[Dict]:
        """Classify a closed path as a polygon"""
        # Skip 4-segment paths (those are rectangles)
        if len(path) == 4:
            return None
        
        # Only consider paths with 3+ segments
        if len(path) < 3:
            return None
        
        path_lines = [lines[idx] for idx in path]
        
        # Calculate bounding box
        all_x = []
        all_y = []
        for line in path_lines:
            all_x.extend([line['x0'], line['x1']])
            all_y.extend([line['y0'], line['y1']])
        
        min_x, max_x = min(all_x), max(all_x)
        min_y, max_y = min(all_y), max(all_y)
        
        width = max_x - min_x
        height = max_y - min_y
        width_mm = width * self.PT_TO_MM
        height_mm = height * self.PT_TO_MM
        
        # Filter by size
        if width_mm < 3 or height_mm < 3:
            return None
        if width_mm > 200 or height_mm > 200:
            return None
        
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        aspect_ratio = width / height if height > 0 else 0
        
        # Determine polygon type
        if len(path) == 3:
            polygon_type = 'triangle'
        elif len(path) >= 8:
            # Check if it's a multi-segment circle
            is_circular = self._check_circularity(path_lines, center_x, center_y)
            polygon_type = 'multi_segment_circle' if is_circular else f'polygon_{len(path)}_sides'
        else:
            polygon_type = f'polygon_{len(path)}_sides'
        
        return {
            'type': polygon_type,
            'bbox': (min_x, min_y, max_x, max_y),
            'center': (center_x, center_y),
            'width_mm': width_mm,
            'height_mm': height_mm,
            'aspect_ratio': aspect_ratio,
            'segments': len(path),
            'path_indices': path,
            'source': 'connected_lines'
        }
    
    def _check_circularity(self, path_lines: List[Dict], center_x: float, center_y: float) -> bool:
        """Check if a multi-segment path forms a circle"""
        # Calculate distances from center to each vertex
        distances = []
        for line in path_lines:
            dist = math.sqrt((line['x0'] - center_x)**2 + (line['y0'] - center_y)**2)
            distances.append(dist)
        
        if not distances:
            return False
        
        avg_radius = sum(distances) / len(distances)
        max_radius = max(distances)
        min_radius = min(distances)
        
        # Check radial variance
        radius_variance = (max_radius - min_radius) / avg_radius if avg_radius > 0 else 1.0
        
        # Circular if variance is low (within 20%)
        return radius_variance < 0.2


class ShapeClassifier:
    """Classifies and categorizes detected shapes"""
    
    @staticmethod
    def categorize_by_type(shapes: Dict[str, List[Dict]]) -> Dict[str, int]:
        """Count shapes by type"""
        counts = {
            'squares': 0,
            'rectangles': 0,
            'circles': 0,
            'triangles': 0,
            'polygons': 0,
            'symbols': 0
        }
        
        for rect in shapes.get('rectangles', []):
            if rect['type'] == 'square':
                counts['squares'] += 1
            else:
                counts['rectangles'] += 1
        
        counts['circles'] = len(shapes.get('circles', []))
        
        for poly in shapes.get('polygons', []):
            if poly['type'] == 'triangle':
                counts['triangles'] += 1
            else:
                counts['polygons'] += 1
        
        return counts
    
    @staticmethod
    def categorize_by_size(shapes: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """Categorize shapes by size"""
        size_categories = {
            'tiny': [],      # < 5mm
            'small': [],     # 5-20mm
            'medium': [],    # 20-100mm
            'large': []      # > 100mm
        }
        
        all_shapes = []
        all_shapes.extend(shapes.get('rectangles', []))
        all_shapes.extend(shapes.get('circles', []))
        all_shapes.extend(shapes.get('polygons', []))
        
        for shape in all_shapes:
            # Determine size
            if 'width_mm' in shape:
                size = max(shape['width_mm'], shape['height_mm'])
            elif 'diameter_mm' in shape:
                size = shape['diameter_mm']
            else:
                continue
            
            if size < 5:
                size_categories['tiny'].append(shape)
            elif size < 20:
                size_categories['small'].append(shape)
            elif size < 100:
                size_categories['medium'].append(shape)
            else:
                size_categories['large'].append(shape)
        
        return size_categories
    
    @staticmethod
    def filter_by_proximity(
        shapes: List[Dict], 
        reference_point: Tuple[float, float], 
        radius_mm: float
    ) -> List[Dict]:
        """Filter shapes by proximity to a reference point"""
        PT_TO_MM = 1 / 2.834645
        radius_pt = radius_mm / PT_TO_MM
        
        nearby_shapes = []
        for shape in shapes:
            shape_center = shape.get('center')
            if not shape_center:
                continue
            
            distance = math.sqrt(
                (shape_center[0] - reference_point[0])**2 + 
                (shape_center[1] - reference_point[1])**2
            )
            
            if distance <= radius_pt:
                nearby_shapes.append({
                    **shape,
                    'distance_from_reference_mm': distance * PT_TO_MM
                })
        
        return nearby_shapes
