"""
Vector-based measurement and detection module

Provides clean interfaces for:
- Line detection (individual segments, paths, tiny strokes)
- Arc/curve detection (circles, arcs)
- Shape detection (rectangles, circles, polygons, symbols)
"""

from .line_detector import LineDetector, ArcDetector, TinyStrokeConnector
from .shape_detector import ShapeDetector, ShapeClassifier

__all__ = [
    'LineDetector',
    'ArcDetector',
    'TinyStrokeConnector',
    'ShapeDetector',
    'ShapeClassifier',
]
