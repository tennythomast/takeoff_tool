"""
Line and Stroke Detection Module

Handles detection of:
1. Individual line segments
2. Arc/curve segments (bezier curves)
3. Tiny connected strokes (for symbols)

Based on PyMuPDF's page.get_drawings() vector data.
"""

import math
from typing import List, Dict, Tuple, Optional, Set
from collections import defaultdict
import fitz  # PyMuPDF


class LineDetector:
    """Detects and analyzes line segments from PDF vector data"""
    
    def __init__(self, min_length_mm: float = 0.05, max_length_mm: float = 200.0):
        """
        Initialize line detector
        
        Args:
            min_length_mm: Minimum line length to consider (default 0.05mm)
            max_length_mm: Maximum line length to consider (default 200mm)
        """
        self.min_length_mm = min_length_mm
        self.max_length_mm = max_length_mm
        self.PT_TO_MM = 1 / 2.834645  # Conversion factor
        
    def extract_lines(self, page: fitz.Page) -> List[Dict]:
        """
        Extract all line segments from a PDF page
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            List of line dictionaries with coordinates and metadata
        """
        drawings = page.get_drawings()
        lines = []
        
        for idx, drawing in enumerate(drawings):
            items = drawing.get('items', [])
            
            # Process single line segments
            if len(items) == 1 and items[0][0] == 'l':
                line = self._process_line_item(idx, items[0], drawing)
                if line:
                    lines.append(line)
            
            # Process multi-item paths with lines
            elif len(items) > 1:
                path_lines = self._process_line_path(idx, items, drawing)
                lines.extend(path_lines)
        
        return lines
    
    def _process_line_item(self, idx: int, item: tuple, drawing: Dict) -> Optional[Dict]:
        """Process a single line item"""
        pt1, pt2 = item[1], item[2]
        length = math.sqrt((pt2.x - pt1.x)**2 + (pt2.y - pt1.y)**2)
        length_mm = length * self.PT_TO_MM
        
        # Filter by length
        if not (self.min_length_mm <= length_mm <= self.max_length_mm):
            return None
        
        return {
            'index': idx,
            'type': 'single_line',
            'x0': pt1.x,
            'y0': pt1.y,
            'x1': pt2.x,
            'y1': pt2.y,
            'length': length,
            'length_mm': length_mm,
            'color': drawing.get('color', (0, 0, 0)),
            'width': drawing.get('width', 1.0)
        }
    
    def _process_line_path(self, idx: int, items: List, drawing: Dict) -> List[Dict]:
        """Process a multi-item path containing lines"""
        path_lines = []
        
        for item_idx, item in enumerate(items):
            if item[0] == 'l':
                pt1, pt2 = item[1], item[2]
                length = math.sqrt((pt2.x - pt1.x)**2 + (pt2.y - pt1.y)**2)
                length_mm = length * self.PT_TO_MM
                
                if self.min_length_mm <= length_mm <= self.max_length_mm:
                    path_lines.append({
                        'index': idx,
                        'type': 'path_line',
                        'path_item_idx': item_idx,
                        'x0': pt1.x,
                        'y0': pt1.y,
                        'x1': pt2.x,
                        'y1': pt2.y,
                        'length': length,
                        'length_mm': length_mm,
                        'color': drawing.get('color', (0, 0, 0)),
                        'width': drawing.get('width', 1.0)
                    })
        
        return path_lines
    
    def filter_by_length(self, lines: List[Dict], min_mm: float, max_mm: float) -> List[Dict]:
        """Filter lines by length range"""
        return [l for l in lines if min_mm <= l['length_mm'] <= max_mm]
    
    def categorize_by_size(self, lines: List[Dict]) -> Dict[str, List[Dict]]:
        """Categorize lines by size"""
        return {
            'tiny': [l for l in lines if l['length_mm'] < 1.0],
            'small': [l for l in lines if 1.0 <= l['length_mm'] < 10.0],
            'medium': [l for l in lines if 10.0 <= l['length_mm'] < 50.0],
            'large': [l for l in lines if l['length_mm'] >= 50.0]
        }


class ArcDetector:
    """Detects and analyzes arc/curve segments from PDF vector data"""
    
    def __init__(self, min_size_mm: float = 1.0, max_size_mm: float = 200.0):
        """
        Initialize arc detector
        
        Args:
            min_size_mm: Minimum arc bounding box size (default 1mm)
            max_size_mm: Maximum arc bounding box size (default 200mm)
        """
        self.min_size_mm = min_size_mm
        self.max_size_mm = max_size_mm
        self.PT_TO_MM = 1 / 2.834645
    
    def extract_arcs(self, page: fitz.Page) -> List[Dict]:
        """
        Extract all arc/curve segments from a PDF page
        
        Args:
            page: PyMuPDF page object
            
        Returns:
            List of arc dictionaries with metadata
        """
        drawings = page.get_drawings()
        arcs = []
        
        for idx, drawing in enumerate(drawings):
            items = drawing.get('items', [])
            rect = drawing.get('rect')
            
            if not rect or not items:
                continue
            
            # Count curve operations
            curve_count = len([item for item in items if item[0] == 'c'])
            
            if curve_count > 0:
                arc = self._process_arc(idx, drawing, items, curve_count)
                if arc:
                    arcs.append(arc)
        
        return arcs
    
    def _process_arc(self, idx: int, drawing: Dict, items: List, curve_count: int) -> Optional[Dict]:
        """Process an arc/curve drawing"""
        rect = drawing.get('rect')
        
        bbox_width = rect[2] - rect[0]
        bbox_height = rect[3] - rect[1]
        bbox_width_mm = bbox_width * self.PT_TO_MM
        bbox_height_mm = bbox_height * self.PT_TO_MM
        
        # Filter by size
        if bbox_width_mm < self.min_size_mm or bbox_height_mm < self.min_size_mm:
            return None
        if bbox_width_mm > self.max_size_mm or bbox_height_mm > self.max_size_mm:
            return None
        
        center_x = (rect[0] + rect[2]) / 2
        center_y = (rect[1] + rect[3]) / 2
        aspect_ratio = bbox_width / bbox_height if bbox_height > 0 else 0
        
        # Classify arc type
        arc_type = self._classify_arc(curve_count, aspect_ratio)
        
        return {
            'index': idx,
            'type': arc_type,
            'curve_count': curve_count,
            'bbox': rect,
            'bbox_width_mm': bbox_width_mm,
            'bbox_height_mm': bbox_height_mm,
            'center': (center_x, center_y),
            'aspect_ratio': aspect_ratio,
            'color': drawing.get('color', (0, 0, 0)),
            'width': drawing.get('width', 1.0),
            'items': items
        }
    
    def _classify_arc(self, curve_count: int, aspect_ratio: float) -> str:
        """Classify arc by curve count and aspect ratio"""
        # Circles typically have 4 bezier curves
        if curve_count == 4 and 0.75 <= aspect_ratio <= 1.35:
            return 'circle'
        elif curve_count >= 2:
            return 'arc'
        else:
            return 'curve'


class TinyStrokeConnector:
    """Connects tiny line strokes to form symbols (e.g., BP markers)"""
    
    def __init__(self, tolerance: float = 0.5):
        """
        Initialize tiny stroke connector
        
        Args:
            tolerance: Endpoint matching tolerance in points (default 0.5pt)
        """
        self.tolerance = tolerance
        self.PT_TO_MM = 1 / 2.834645
    
    def connect_strokes(self, lines: List[Dict], max_depth: int = 100) -> List[List[int]]:
        """
        Connect tiny line strokes into closed paths
        
        Finds ALL possible closed paths and returns them sorted by length (longest first).
        This ensures we capture complete symbols rather than partial paths.
        
        Args:
            lines: List of line dictionaries
            max_depth: Maximum path depth to search (increased to 100 for complex symbols)
            
        Returns:
            List of paths sorted by length (longest first), where each path is a list of line indices
        """
        # Build endpoint map
        endpoint_map = self._build_endpoint_map(lines)
        
        # Find ALL closed paths (don't mark as processed yet)
        all_paths = []
        
        for i in range(len(lines)):
            path = self._find_closed_path(i, lines, endpoint_map, max_depth)
            
            if path and len(path) >= 4:  # Minimum 4 segments for a symbol (lowered from 8)
                all_paths.append(path)
        
        # Remove duplicate paths (same set of lines, different starting point)
        unique_paths = []
        seen_sets = []
        
        for path in all_paths:
            path_set = frozenset(path)
            if path_set not in seen_sets:
                seen_sets.append(path_set)
                unique_paths.append(path)
        
        # Sort by length (longest first) - prioritize complete symbols
        unique_paths.sort(key=len, reverse=True)
        
        # Now mark lines as processed and collect non-overlapping paths
        closed_paths = []
        processed = set()
        
        for path in unique_paths:
            # Check if any line in this path is already used
            if not any(line_idx in processed for line_idx in path):
                closed_paths.append(path)
                for line_idx in path:
                    processed.add(line_idx)
        
        return closed_paths
    
    def _build_endpoint_map(self, lines: List[Dict]) -> Dict[Tuple[float, float], List[Dict]]:
        """Build a map of endpoints for fast lookup"""
        endpoint_map = defaultdict(list)
        
        for i, line in enumerate(lines):
            # Add start point
            start_key = self._round_point(line['x0'], line['y0'])
            endpoint_map[start_key].append({
                'line_idx': i,
                'endpoint': 'start',
                'x': line['x0'],
                'y': line['y0'],
                'other_x': line['x1'],
                'other_y': line['y1']
            })
            
            # Add end point
            end_key = self._round_point(line['x1'], line['y1'])
            endpoint_map[end_key].append({
                'line_idx': i,
                'endpoint': 'end',
                'x': line['x1'],
                'y': line['y1'],
                'other_x': line['x0'],
                'other_y': line['y0']
            })
        
        return endpoint_map
    
    def _round_point(self, x: float, y: float, precision: float = 0.05) -> Tuple[float, float]:
        """Round point to precision for indexing"""
        return (round(x / precision) * precision, round(y / precision) * precision)
    
    def _points_match(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        """Check if two points match within tolerance"""
        return abs(x1 - x2) <= self.tolerance and abs(y1 - y2) <= self.tolerance
    
    def _find_closed_path(
        self, 
        start_line_idx: int, 
        lines: List[Dict], 
        endpoint_map: Dict, 
        max_depth: int
    ) -> Optional[List[int]]:
        """Find a closed path starting from a given line"""
        visited = set()
        path = [start_line_idx]
        visited.add(start_line_idx)
        
        current_x = lines[start_line_idx]['x1']
        current_y = lines[start_line_idx]['y1']
        start_x = lines[start_line_idx]['x0']
        start_y = lines[start_line_idx]['y0']
        
        for depth in range(max_depth):
            current_key = self._round_point(current_x, current_y)
            candidates = endpoint_map.get(current_key, [])
            
            next_line = None
            for candidate in candidates:
                line_idx = candidate['line_idx']
                if line_idx in visited:
                    continue
                if self._points_match(candidate['x'], candidate['y'], current_x, current_y):
                    next_line = candidate
                    break
            
            if next_line is None:
                # Check if we've closed the loop
                if self._points_match(current_x, current_y, start_x, start_y):
                    return path
                else:
                    return None
            
            path.append(next_line['line_idx'])
            visited.add(next_line['line_idx'])
            current_x = next_line['other_x']
            current_y = next_line['other_y']
            
            # Check if we've closed the loop
            if self._points_match(current_x, current_y, start_x, start_y):
                return path
        
        return None
    
    def find_symbols_near_labels(
        self, 
        lines: List[Dict], 
        label_positions: List[Tuple[float, float]], 
        radius_mm: float = 17.0
    ) -> List[Dict]:
        """
        Find symbols made of tiny strokes near text labels
        
        Args:
            lines: List of all line segments
            label_positions: List of (x, y) label center positions
            radius_mm: Search radius in millimeters
            
        Returns:
            List of detected symbols with metadata
        """
        radius_pt = radius_mm / self.PT_TO_MM
        symbols = []
        
        for label_pos in label_positions:
            # Find lines near this label
            nearby_lines = []
            for line in lines:
                line_center = ((line['x0'] + line['x1']) / 2, (line['y0'] + line['y1']) / 2)
                dist = math.sqrt(
                    (line_center[0] - label_pos[0])**2 + 
                    (line_center[1] - label_pos[1])**2
                )
                
                if dist <= radius_pt and line['length_mm'] < 2.0:  # Tiny lines only (increased to 2mm)
                    nearby_lines.append(line)
            
            if len(nearby_lines) < 4:  # Need at least 4 lines to form a symbol
                continue
            
            # Connect nearby lines
            paths = self.connect_strokes(nearby_lines)
            
            if paths:
                # Take the largest path as the symbol
                largest_path = max(paths, key=len)
                symbol = self._analyze_symbol(largest_path, nearby_lines, label_pos)
                if symbol:
                    symbols.append(symbol)
        
        return symbols
    
    def _analyze_symbol(
        self, 
        path: List[int], 
        lines: List[Dict], 
        label_pos: Tuple[float, float]
    ) -> Optional[Dict]:
        """Analyze a connected path to determine symbol properties"""
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
        
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        aspect_ratio = width / height if height > 0 else 0
        
        # Check circularity
        is_circular = 0.75 <= aspect_ratio <= 1.35
        
        # Calculate radial variance
        distances = []
        for line in path_lines:
            dist = math.sqrt((line['x0'] - center_x)**2 + (line['y0'] - center_y)**2)
            distances.append(dist)
        
        avg_radius = sum(distances) / len(distances) if distances else 0
        max_radius = max(distances) if distances else 0
        min_radius = min(distances) if distances else 0
        radius_variance = (max_radius - min_radius) / avg_radius if avg_radius > 0 else 0
        
        is_equidistant = radius_variance < 0.3
        
        # Classify shape
        if is_circular and is_equidistant:
            shape_type = 'circle'
        elif is_circular:
            shape_type = 'circular_polygon'
        else:
            shape_type = 'polygon'
        
        # Calculate distance from label
        dist_from_label = math.sqrt(
            (center_x - label_pos[0])**2 + 
            (center_y - label_pos[1])**2
        ) * self.PT_TO_MM
        
        return {
            'type': shape_type,
            'segments': len(path),
            'center': (center_x, center_y),
            'bbox': (min_x, min_y, max_x, max_y),
            'width_mm': width_mm,
            'height_mm': height_mm,
            'diameter_mm': (width_mm + height_mm) / 2 if is_circular else None,
            'aspect_ratio': aspect_ratio,
            'is_circular': is_circular,
            'is_equidistant': is_equidistant,
            'distance_from_label_mm': dist_from_label,
            'path_indices': path
        }
