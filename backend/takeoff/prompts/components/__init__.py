"""
Components module for prompt building
"""

from .rules import get_combined_rules, UNIVERSAL_EXTRACTION_RULES

__all__ = [
    'get_combined_rules',
    'UNIVERSAL_EXTRACTION_RULES',
]