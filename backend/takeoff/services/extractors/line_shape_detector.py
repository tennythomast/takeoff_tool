"""
Adaptive Line-Based Shape Detector

Automatically adjusts clustering and detection parameters based on the 
specific characteristics of each PDF drawing. Works with:
- PDFs with closed shapes (normal case)
- PDFs with many tiny lines (like 7_FLETT_RD.pdf)
- PDFs with medium-sized line segments
- Mixed drawing styles

The detector analyzes line distribution and adapts accordingly.
"""

import logging
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from dataclasses import dataclass
import math
import statistics

from takeoff.shapes import (
    Circle, Rectangle, Polygon, Point, BoundingBox,
    ShapeStyle, LineStyle
)

logger = logging.getLogger(__name__)


@dataclass
class LineSegment:
    """A single line segment"""
    x0: float
    y0: float
    x1: float
    y1: float
    linewidth: float
    color: Tuple[float, float, float]
    
    @property
    def length(self) -> float:
        return math.sqrt((self.x1 - self.x0)**2 + (self.y1 - self.y0)**2)
    
    @property
    def midpoint(self) -> Point:
        return Point(x=(self.x0 + self.x1) / 2, y=(self.y0 + self.y1) / 2)
    
    @property
    def angle(self) -> float:
        """Angle in degrees"""
        return math.degrees(math.atan2(self.y1 - self.y0, self.x1 - self.x0))


@dataclass
class LineCluster:
    """Cluster of nearby line segments"""
    lines: List[LineSegment]
    
    @property
    def bbox(self) -> BoundingBox:
        if not self.lines:
            return BoundingBox(0, 0, 0, 0)
        xs, ys = [], []
        for line in self.lines:
            xs.extend([line.x0, line.x1])
            ys.extend([line.y0, line.y1])
        return BoundingBox(x0=min(xs), y0=min(ys), x1=max(xs), y1=max(ys))
    
    @property
    def center(self) -> Point:
        return self.bbox.center
    
    @property
    def total_length(self) -> float:
        return sum(line.length for line in self.lines)
    
    @property
    def avg_linewidth(self) -> float:
        return sum(l.linewidth for l in self.lines) / len(self.lines) if self.lines else 1.0
    
    @property
    def avg_color(self) -> Tuple[float, float, float]:
        if not self.lines:
            return (0, 0, 0)
        r = sum(l.color[0] for l in self.lines) / len(self.lines)
        g = sum(l.color[1] for l in self.lines) / len(self.lines)
        b = sum(l.color[2] for l in self.lines) / len(self.lines)
        return (r, g, b)


@dataclass
class LineAnalysis:
    """Analysis results of line distribution in PDF"""
    total_lines: int
    tiny_lines: int  # 0-5mm
    small_lines: int  # 5-10mm
    medium_lines: int  # 10-50mm
    large_lines: int  # 50mm+
    avg_length_mm: float
    median_length_mm: float
    drawing_style: str  # 'tiny_segments', 'mixed', 'normal'
    
    def __str__(self):
        return (f"LineAnalysis(total={self.total_lines}, "
                f"tiny={self.tiny_lines}, small={self.small_lines}, "
                f"medium={self.medium_lines}, style='{self.drawing_style}')")


class AdaptiveLineShapeDetector:
    """
    Adaptive detector that analyzes line distribution and adjusts parameters
    
    Automatically handles:
    - PDFs with many tiny lines (high cluster distance)
    - PDFs with medium lines (moderate cluster distance)
    - Mixed PDFs (adaptive strategy)
    """
    
    def __init__(self, 
                 auto_tune: bool = True,
                 min_circle_diameter_mm: float = 5.0,
                 max_circle_diameter_mm: float = 100.0,
                 min_rectangle_size_mm: float = 5.0,
                 max_rectangle_size_mm: float = 100.0):
        """
        Args:
            auto_tune: Automatically adjust parameters based on line analysis
            min_circle_diameter_mm: Minimum circle diameter
            max_circle_diameter_mm: Maximum circle diameter
            min_rectangle_size_mm: Minimum rectangle dimension
            max_rectangle_size_mm: Maximum rectangle dimension
        """
        self.auto_tune = auto_tune
        
        # Size filters (fixed)
        self.min_circle_diameter = min_circle_diameter_mm * 2.834645
        self.max_circle_diameter = max_circle_diameter_mm * 2.834645
        self.min_rectangle_size = min_rectangle_size_mm * 2.834645
        self.max_rectangle_size = max_rectangle_size_mm * 2.834645
        
        # Adaptive parameters (will be set based on analysis)
        self.cluster_distance = None
        self.circle_tolerance = None
        self.min_lines_per_cluster = None
        self.min_line_length_mm = None
        self.max_line_length_mm = None
        
        logger.info("AdaptiveLineShapeDetector initialized")
    
    def detect_shapes_from_pdfplumber(self, lines_data: List[Dict], page_number: int) -> Dict:
        """
        Detect shapes with adaptive parameter tuning
        """
        logger.info(f"="*60)
        logger.info(f"Processing page {page_number} with {len(lines_data)} lines")
        
        # Step 1: Analyze line distribution
        analysis = self._analyze_lines(lines_data)
        logger.info(f"Line analysis: {analysis}")
        
        # Step 2: Set adaptive parameters
        self._set_adaptive_parameters(analysis)
        logger.info(f"Adaptive parameters:")
        logger.info(f"  cluster_distance: {self.cluster_distance/2.834645:.1f}mm")
        logger.info(f"  circle_tolerance: {self.circle_tolerance:.2f}")
        logger.info(f"  min_lines_per_cluster: {self.min_lines_per_cluster}")
        logger.info(f"  line_length_range: {self.min_line_length_mm:.1f}-{self.max_line_length_mm:.1f}mm")
        
        # Step 3: Convert to LineSegment objects
        line_segments = self._convert_lines(lines_data)
        
        # Step 4: Filter lines by length
        filtered_lines = self._filter_lines(line_segments)
        logger.info(f"Filtered to {len(filtered_lines)} lines "
                   f"({self.min_line_length_mm:.1f}-{self.max_line_length_mm:.1f}mm range)")
        
        # Step 5: Cluster lines
        clusters = self._cluster_lines(filtered_lines)
        logger.info(f"Created {len(clusters)} clusters")
        
        # Log top clusters
        for i, cluster in enumerate(sorted(clusters, key=lambda c: len(c.lines), reverse=True)[:10], 1):
            bbox = cluster.bbox
            logger.info(f"  Cluster {i}: {len(cluster.lines)} lines, "
                       f"size: {bbox.width/2.834645:.1f}x{bbox.height/2.834645:.1f}mm")
        
        # Step 6: Classify clusters
        circles, rectangles, polygons, all_shapes = self._classify_clusters(clusters, page_number)
        
        logger.info(f"DETECTED: {len(circles)} circles, {len(rectangles)} rectangles, "
                   f"{len(polygons)} polygons (total: {len(all_shapes)})")
        logger.info(f"="*60)
        
        return {
            'circles': circles,
            'rectangles': rectangles,
            'polygons': polygons,
            'all_shapes': all_shapes
        }
    
    def _analyze_lines(self, lines_data: List[Dict]) -> LineAnalysis:
        """
        Analyze line distribution to determine drawing style
        """
        if not lines_data:
            return LineAnalysis(0, 0, 0, 0, 0, 0.0, 0.0, 'unknown')
        
        lengths_mm = []
        for line in lines_data:
            length = math.sqrt((line['x1']-line['x0'])**2 + (line['y1']-line['y0'])**2)
            length_mm = length / 2.834645
            lengths_mm.append(length_mm)
        
        # Count by size categories
        tiny = sum(1 for l in lengths_mm if 0 <= l < 5)
        small = sum(1 for l in lengths_mm if 5 <= l < 10)
        medium = sum(1 for l in lengths_mm if 10 <= l < 50)
        large = sum(1 for l in lengths_mm if l >= 50)
        
        avg_length = statistics.mean(lengths_mm)
        median_length = statistics.median(lengths_mm)
        
        # Determine drawing style
        total = len(lengths_mm)
        tiny_pct = (tiny / total) * 100
        medium_pct = (medium / total) * 100
        
        if tiny_pct > 70:
            # Most lines are tiny (< 5mm) - like 7_FLETT_RD.pdf
            drawing_style = 'tiny_segments'
        elif medium_pct > 30:
            # Significant medium lines
            drawing_style = 'normal'
        else:
            # Mixed
            drawing_style = 'mixed'
        
        return LineAnalysis(
            total_lines=total,
            tiny_lines=tiny,
            small_lines=small,
            medium_lines=medium,
            large_lines=large,
            avg_length_mm=avg_length,
            median_length_mm=median_length,
            drawing_style=drawing_style
        )
    
    def _set_adaptive_parameters(self, analysis: LineAnalysis):
        """
        Set clustering parameters based on line analysis
        """
        if analysis.drawing_style == 'tiny_segments':
            # Many tiny lines - need large cluster distance
            # Example: 7_FLETT_RD.pdf with 86% tiny lines
            self.cluster_distance = 20.0 * 2.834645  # 20mm
            self.circle_tolerance = 0.35
            self.min_lines_per_cluster = 2
            self.min_line_length_mm = 0.5  # Include tiny lines
            self.max_line_length_mm = 100.0
            
            logger.info("  Style: TINY_SEGMENTS - using large cluster distance")
            
        elif analysis.drawing_style == 'normal':
            # Normal-sized lines - moderate cluster distance
            self.cluster_distance = 10.0 * 2.834645  # 10mm
            self.circle_tolerance = 0.25
            self.min_lines_per_cluster = 2
            self.min_line_length_mm = 3.0
            self.max_line_length_mm = 150.0
            
            logger.info("  Style: NORMAL - using moderate cluster distance")
            
        else:  # mixed
            # Mixed - use middle ground
            self.cluster_distance = 15.0 * 2.834645  # 15mm
            self.circle_tolerance = 0.30
            self.min_lines_per_cluster = 2
            self.min_line_length_mm = 1.0
            self.max_line_length_mm = 120.0
            
            logger.info("  Style: MIXED - using balanced parameters")
        
        # Further fine-tune based on average line length
        if analysis.avg_length_mm < 3.0:
            # Very tiny average - increase cluster distance even more
            self.cluster_distance *= 1.5
            logger.info(f"  Adjusting: Very small avg length ({analysis.avg_length_mm:.1f}mm), "
                       f"increasing cluster distance")
        elif analysis.avg_length_mm > 20.0:
            # Large average - can use smaller cluster distance
            self.cluster_distance *= 0.7
            logger.info(f"  Adjusting: Large avg length ({analysis.avg_length_mm:.1f}mm), "
                       f"decreasing cluster distance")
    
    def _convert_lines(self, lines_data: List[Dict]) -> List[LineSegment]:
        """Convert pdfplumber lines to LineSegment objects"""
        line_segments = []
        for line in lines_data:
            color = line.get('stroking_color', (0, 0, 0))
            if not isinstance(color, (list, tuple)) or len(color) < 3:
                color = (0, 0, 0)
            
            line_segments.append(LineSegment(
                x0=line['x0'],
                y0=line['y0'],
                x1=line['x1'],
                y1=line['y1'],
                linewidth=line.get('linewidth', 1.0),
                color=tuple(color[:3])
            ))
        return line_segments
    
    def _filter_lines(self, lines: List[LineSegment]) -> List[LineSegment]:
        """Filter lines by length range"""
        filtered = []
        for line in lines:
            length_mm = line.length / 2.834645
            if self.min_line_length_mm <= length_mm <= self.max_line_length_mm:
                filtered.append(line)
        return filtered
    
    def _cluster_lines(self, lines: List[LineSegment]) -> List[LineCluster]:
        """
        Cluster lines using spatial grid for efficiency
        """
        if not lines:
            return []
        
        # Use spatial grid
        grid_size = max(50, self.cluster_distance / 2)  # Adaptive grid size
        grid = defaultdict(list)
        
        for idx, line in enumerate(lines):
            mid = line.midpoint
            cell_x = int(mid.x / grid_size)
            cell_y = int(mid.y / grid_size)
            
            # Add to cell and neighbors
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    grid[(cell_x + dx, cell_y + dy)].append(idx)
        
        # Cluster
        clusters = []
        used = set()
        
        for indices in grid.values():
            for idx in indices:
                if idx in used:
                    continue
                
                cluster_lines = [lines[idx]]
                used.add(idx)
                
                # Grow cluster iteratively
                changed = True
                iterations = 0
                max_iterations = 15
                
                while changed and iterations < max_iterations:
                    changed = False
                    iterations += 1
                    
                    for other_idx in indices:
                        if other_idx in used:
                            continue
                        
                        if self._is_line_near_cluster(lines[other_idx], cluster_lines):
                            cluster_lines.append(lines[other_idx])
                            used.add(other_idx)
                            changed = True
                
                # Keep if enough lines
                if len(cluster_lines) >= self.min_lines_per_cluster:
                    clusters.append(LineCluster(lines=cluster_lines))
        
        return clusters
    
    def _is_line_near_cluster(self, line: LineSegment, cluster: List[LineSegment]) -> bool:
        """Check if line is within cluster_distance of any line in cluster"""
        for cluster_line in cluster:
            if self._distance_between_lines(line, cluster_line) <= self.cluster_distance:
                return True
        return False
    
    def _distance_between_lines(self, line1: LineSegment, line2: LineSegment) -> float:
        """Minimum distance between two line segments"""
        points1 = [
            (line1.x0, line1.y0),
            (line1.x1, line1.y1),
            (line1.midpoint.x, line1.midpoint.y)
        ]
        points2 = [
            (line2.x0, line2.y0),
            (line2.x1, line2.y1),
            (line2.midpoint.x, line2.midpoint.y)
        ]
        
        min_dist = float('inf')
        for p1 in points1:
            for p2 in points2:
                dist = math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
                min_dist = min(min_dist, dist)
        
        return min_dist
    
    def _classify_clusters(self, clusters: List[LineCluster], page_number: int) -> Tuple[List, List, List, List]:
        """Classify all clusters"""
        circles, rectangles, polygons, all_shapes = [], [], [], []
        
        for cluster in clusters:
            shape = self._classify_cluster(cluster, page_number)
            if shape:
                shape_dict = shape.to_dict()
                if isinstance(shape, Circle):
                    circles.append(shape_dict)
                    all_shapes.append(shape)
                elif isinstance(shape, Rectangle):
                    rectangles.append(shape_dict)
                    all_shapes.append(shape)
                elif isinstance(shape, Polygon):
                    polygons.append(shape_dict)
                    all_shapes.append(shape)
        
        return circles, rectangles, polygons, all_shapes
    
    def _classify_cluster(self, cluster: LineCluster, page_number: int) -> Optional[object]:
        """Classify a single cluster"""
        bbox = cluster.bbox
        width, height = bbox.width, bbox.height
        
        # Minimum size
        if width < 5.67 or height < 5.67:  # 2mm
            return None
        
        style = ShapeStyle(
            stroke_width=cluster.avg_linewidth,
            stroke_color=cluster.avg_color,
            fill_color=None,
            line_style=LineStyle.SOLID
        )
        
        # Try circle
        if self._is_circular_cluster(cluster):
            diameter = (width + height) / 2
            if self.min_circle_diameter <= diameter <= self.max_circle_diameter:
                return Circle(
                    center=cluster.center,
                    radius=diameter / 2,
                    style=style,
                    page_number=page_number
                )
        
        # Try rectangle
        if self._is_rectangular_cluster(cluster):
            if (self.min_rectangle_size <= width <= self.max_rectangle_size and
                self.min_rectangle_size <= height <= self.max_rectangle_size):
                return Rectangle(
                    bbox=bbox,
                    style=style,
                    page_number=page_number
                )
        
        # Try polygon
        if 3 <= len(cluster.lines) <= 20:
            vertices = self._extract_vertices(cluster)
            if 3 <= len(vertices) <= 12:
                return Polygon(
                    vertices=vertices,
                    style=style,
                    page_number=page_number
                )
        
        return None
    
    def _is_circular_cluster(self, cluster: LineCluster) -> bool:
        """Check if cluster forms a circle"""
        bbox = cluster.bbox
        width, height = bbox.width, bbox.height
        
        if height == 0 or width == 0:
            return False
        
        # Aspect ratio
        aspect = width / height
        if not (0.65 <= aspect <= 1.35):
            return False
        
        # Line coverage
        expected_circ = math.pi * ((width + height) / 2)
        coverage = cluster.total_length / expected_circ if expected_circ > 0 else 0
        
        # Use adaptive tolerance
        min_coverage = max(0.2, 1.0 - self.circle_tolerance)
        max_coverage = min(3.0, 1.0 + self.circle_tolerance * 2)
        
        return min_coverage <= coverage <= max_coverage
    
    def _is_rectangular_cluster(self, cluster: LineCluster) -> bool:
        """Check if cluster forms a rectangle"""
        h_lines = v_lines = 0
        
        for line in cluster.lines:
            angle = abs(line.angle)
            if angle < 25 or angle > 155:
                h_lines += 1
            elif 65 < angle < 115:
                v_lines += 1
        
        return h_lines >= 1 and v_lines >= 1
    
    def _extract_vertices(self, cluster: LineCluster) -> List[Point]:
        """Extract vertices from cluster"""
        endpoints = []
        for line in cluster.lines:
            endpoints.append((line.x0, line.y0))
            endpoints.append((line.x1, line.y1))
        
        # Remove duplicates
        vertices = []
        tolerance = 7.0
        
        for point in endpoints:
            is_dup = False
            for vertex in vertices:
                if math.sqrt((point[0]-vertex[0])**2 + (point[1]-vertex[1])**2) < tolerance:
                    is_dup = True
                    break
            if not is_dup:
                vertices.append(point)
        
        # Sort by angle
        if len(vertices) >= 3:
            cx = sum(v[0] for v in vertices) / len(vertices)
            cy = sum(v[1] for v in vertices) / len(vertices)
            vertices.sort(key=lambda v: math.atan2(v[1]-cy, v[0]-cx))
        
        return [Point(x=v[0], y=v[1]) for v in vertices]


# Backward compatibility alias
LineBasedShapeDetector = AdaptiveLineShapeDetector