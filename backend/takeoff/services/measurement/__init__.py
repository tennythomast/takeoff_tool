"""
Measurement services for takeoff analysis
"""

# Import vector module (always available)
from . import vector

# Try to import count_analyzer if it exists
try:
    from .count_analyzer import CountAnalyzer
    __all__ = ['CountAnalyzer', 'vector']
except ImportError:
    __all__ = ['vector']
