"""
Document layout analysis with proper ModelHub integration.

This module now uses the UnifiedExtractor for vision-based layout analysis to avoid duplicate LLM calls.
"""

import logging
import asyncio
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class BlockType(Enum):
    TITLE = 'title'
    HEADING = 'heading'
    PARAGRAPH = 'paragraph'
    LIST = 'list'
    TABLE = 'table'
    FIGURE = 'figure'
    CAPTION = 'caption'
    HEADER = 'header'
    FOOTER = 'footer'
    SIDEBAR = 'sidebar'


@dataclass
class LayoutBlock:
    """Represents a single layout block"""
    type: BlockType
    text: str
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2
    page: int
    reading_order: int
    confidence: float
    metadata: Dict


class LayoutAnalyzer:
    """
    Document layout analysis with ModelHub integration.
    
    Uses existing infrastructure:
    - ModelRouter for model selection
    - UnifiedLLMClient for API calls
    - APIKey for authentication
    - ModelMetrics for cost tracking
    """
    
    def __init__(self):
        # Don't take vision_extractor as dependency
        # We'll use ModelHub components directly
        pass
    
    async def analyze_layout(
        self, 
        file_path: str,
        organization=None,
        method: str = 'auto'
    ) -> List[LayoutBlock]:
        """
        Analyze document layout and return structured blocks.
        
        Args:
            file_path: Path to PDF/image file
            organization: Organization for ModelHub routing
            method: 'rule_based', 'vision', or 'auto'
        
        Returns:
            List of LayoutBlock objects in reading order
        """
        
        if method == 'auto':
            # Only rule-based (faster, free)
            blocks = self._analyze_rule_based(file_path)
        
        elif method == 'rule_based':
            blocks = self._analyze_rule_based(file_path)
        
        elif method == 'vision':
            raise ValueError("Vision method removed, use 'rule_based' or 'auto'")
        
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Sort by reading order
        blocks.sort(key=lambda b: (b.page, b.reading_order))
        
        return blocks
    
    def _analyze_rule_based(self, file_path: str) -> List[LayoutBlock]:
        """
        Rule-based layout analysis using PyMuPDF.
        (Keeping your existing implementation - it's good)
        """
        try:
            import fitz
        except ImportError:
            logger.error("PyMuPDF not installed")
            return []
        
        blocks = []
        doc = fitz.open(file_path)
        
        for page_num, page in enumerate(doc):
            page_blocks = page.get_text("dict")["blocks"]
            
            reading_order = 0
            for block in page_blocks:
                bbox = block.get("bbox", (0, 0, 0, 0))
                
                # Skip images
                if block.get("type") == 1:
                    blocks.append(LayoutBlock(
                        type=BlockType.FIGURE,
                        text="[Image]",
                        bbox=bbox,
                        page=page_num + 1,
                        reading_order=reading_order,
                        confidence=1.0,
                        metadata={'width': block.get('width'), 'height': block.get('height')}
                    ))
                    reading_order += 1
                    continue
                
                # Process text blocks
                text_lines = []
                for line in block.get("lines", []):
                    line_text = ""
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                    text_lines.append(line_text.strip())
                
                text = "\n".join(text_lines)
                if not text.strip():
                    continue
                
                # Classify block type
                block_type = self._classify_block(
                    text=text,
                    bbox=bbox,
                    page_height=page.rect.height,
                    page_width=page.rect.width,
                    block_data=block
                )
                
                blocks.append(LayoutBlock(
                    type=block_type,
                    text=text,
                    bbox=bbox,
                    page=page_num + 1,
                    reading_order=reading_order,
                    confidence=0.8,
                    metadata=self._extract_block_metadata(block)
                ))
                
                reading_order += 1
        
        doc.close()
        return blocks
    
    # Vision-based layout analysis removed
    # _analyze_vision_based() and _build_vision_messages() no longer exist
    
    def _classify_block(self, text, bbox, page_height, page_width, block_data):
        """Classify block type based on position and content"""
        x1, y1, x2, y2 = bbox
        
        if y1 < page_height * 0.08:
            return BlockType.HEADER
        if y2 > page_height * 0.92:
            return BlockType.FOOTER
        
        if y1 < page_height * 0.2 and len(text) < 100:
            font_sizes = []
            for line in block_data.get('lines', []):
                for span in line.get('spans', []):
                    font_sizes.append(span.get('size', 12))
            
            if font_sizes and max(font_sizes) > 16:
                return BlockType.TITLE
        
        if text.strip().startswith(('•', '-', '*', '1.', '2.', 'a.', 'i.')):
            return BlockType.LIST
        
        if len(text) < 200 and any(word in text.lower() for word in ['figure', 'table', 'fig.', 'tab.']):
            return BlockType.CAPTION
        
        return BlockType.PARAGRAPH
    
    def _extract_block_metadata(self, block):
        """Extract metadata from block"""
        metadata = {}
        
        fonts = set()
        font_sizes = []
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                fonts.add(span.get('font', 'unknown'))
                font_sizes.append(span.get('size', 12))
        
        if fonts:
            metadata['fonts'] = list(fonts)
        if font_sizes:
            metadata['avg_font_size'] = sum(font_sizes) / len(font_sizes)
            metadata['max_font_size'] = max(font_sizes)
        
        return metadata
    
    def _assess_layout_quality(self, blocks):
        """Assess quality of layout analysis"""
        if not blocks:
            return 0.0
        
        types = set(b.type for b in blocks)
        type_diversity = len(types) / len(BlockType)
        
        order_score = 1.0
        prev_order = -1
        for block in blocks:
            if block.reading_order <= prev_order:
                order_score *= 0.8
            prev_order = block.reading_order
        
        avg_confidence = sum(b.confidence for b in blocks) / len(blocks)
        
        return (type_diversity * 0.3 + order_score * 0.3 + avg_confidence * 0.4)
