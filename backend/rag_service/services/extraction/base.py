# File: backend/rag_service/services/extraction/base.py

"""
Base classes for extraction services.

Provides common interfaces and data structures for all extractors.
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Union
from decimal import Decimal


@dataclass
class ExtractionResult:
    """
    Standard result format for all extraction methods.
    """
    success: bool
    extracted_text: str
    structured_data: Dict[str, Any]
    metadata: Dict[str, Any]
    extraction_method: str
    model_used: str
    provider_used: str
    tokens_used_input: int
    tokens_used_output: int
    image_count: int = 0
    cost_usd: Union[float, Decimal] = 0.0
    processing_time: float = 0.0
    confidence_score: float = 0.0
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'success': self.success,
            'text': self.extracted_text,
            'structured_data': self.structured_data,
            'metadata': {
                **self.metadata,
                'extraction_method': self.extraction_method,
                'model_used': self.model_used,
                'provider_used': self.provider_used,
                'tokens_used_input': self.tokens_used_input,
                'tokens_used_output': self.tokens_used_output,
                'image_count': self.image_count,
                'cost_usd': float(self.cost_usd),
                'processing_time': self.processing_time,
                'confidence_score': self.confidence_score,
                'warnings': self.warnings
            }
        }


class BaseExtractor:
    """
    Base class for all extractors.
    
    Provides common interfaces and utility methods.
    """
    
    async def extract(self, file_path: str) -> ExtractionResult:
        """
        Extract content from a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            ExtractionResult: Standardized extraction result
        """
        raise NotImplementedError("Subclasses must implement extract()")
    
    def _error_result(self, error_message: str) -> ExtractionResult:
        """
        Create a standardized error result.
        
        Args:
            error_message: Error message
            
        Returns:
            ExtractionResult: Error result
        """
        return ExtractionResult(
            success=False,
            extracted_text="",
            structured_data={},
            metadata={},
            extraction_method=self.__class__.__name__,
            model_used="",
            provider_used="",
            tokens_used_input=0,
            tokens_used_output=0,
            cost_usd=0.0,
            processing_time=0.0,
            confidence_score=0.0,
            warnings=[error_message]
        )
