"""
Vector-based orchestration module

Provides pipeline orchestration for vector-based element detection
combining text extraction with geometric shape detection.
"""

from .vector_element_pipeline import (
    VectorElementPipeline,
    ElementOccurrence,
    PipelineResults,
    process_pdf_page
)

__all__ = [
    'VectorElementPipeline',
    'ElementOccurrence',
    'PipelineResults',
    'process_pdf_page',
]
