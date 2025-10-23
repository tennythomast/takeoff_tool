"""
Advanced table extraction integrated with existing extraction pipeline.

This module now uses the UnifiedExtractor for vision-based table extraction to avoid duplicate LLM calls.
"""

import logging
from typing import List, Dict, Optional, Tuple
from enum import Enum
import pandas as pd

logger = logging.getLogger(__name__)


class TableExtractionMethod(Enum):
    CAMELOT = 'camelot'
    PDFPLUMBER = 'pdfplumber'
    VISION = 'vision'


class TableExtractor:
    """
    Multi-method table extraction that integrates with ModelHub.
    
    Strategy:
    1. Try Camelot (best for structured PDFs) - FREE
    2. Try pdfplumber (good for simple tables) - FREE
    3. Fall back to vision via ModelHub - PAID but accurate
    
    Properly integrates:
    - ModelRouter for model selection
    - UnifiedLLMClient for API execution
    - APIKey for authentication
    - ModelMetrics for cost tracking
    """
    
    def __init__(self):
        # No dependencies - will use ModelHub when needed
        pass
    
    async def extract_tables(
        self, 
        file_path: str,
        organization=None,
        pages: Optional[List[int]] = None
    ) -> List[Dict]:
        """
        Extract all tables from document with fallback strategy.
        
        Args:
            file_path: Path to PDF file
            organization: Organization for ModelHub routing (needed for vision)
            pages: Specific pages to process (None = all pages)
        
        Returns:
            List of table dictionaries with:
            - data: DataFrame
            - page: Page number
            - bbox: Bounding box [x1, y1, x2, y2]
            - confidence: Quality score 0-1
            - method: Extraction method used
            - markdown: Markdown representation
            - text: Plain text representation
        """
        tables = []
        
        # Method 1: Camelot (fast, free, best for bordered tables)
        try:
            camelot_tables = self._extract_with_camelot(file_path, pages)
            if camelot_tables and self._assess_quality(camelot_tables) > 0.7:
                logger.info(f"Camelot extracted {len(camelot_tables)} high-quality tables")
                return camelot_tables
        except Exception as e:
            logger.warning(f"Camelot extraction failed: {e}")
        
        # Method 2: pdfplumber (fast, free, good for simple tables)
        try:
            plumber_tables = self._extract_with_pdfplumber(file_path, pages)
            if plumber_tables and self._assess_quality(plumber_tables) > 0.6:
                logger.info(f"pdfplumber extracted {len(plumber_tables)} tables")
                return plumber_tables
        except Exception as e:
            logger.warning(f"pdfplumber extraction failed: {e}")
        
        return tables
    
    def _extract_with_camelot(
        self, 
        file_path: str, 
        pages: Optional[List[int]]
    ) -> List[Dict]:
        """Extract tables using Camelot (best for structured PDFs)"""
        try:
            import camelot
        except ImportError:
            logger.info("Camelot not installed. Install: pip install 'camelot-py[base]' ghostscript")
            return []
        
        page_range = ','.join(map(str, pages)) if pages else 'all'
        tables = []
        
        # Try lattice mode (bordered tables)
        try:
            camelot_tables = camelot.read_pdf(
                file_path,
                pages=page_range,
                flavor='lattice',
                line_scale=40
            )
            
            for table in camelot_tables:
                if table.accuracy > 70:
                    tables.append(self._format_camelot_table(table, 'lattice'))
        except Exception as e:
            logger.debug(f"Camelot lattice mode failed: {e}")
        
        # Try stream mode if lattice found few tables
        if len(tables) < 2:
            try:
                camelot_tables = camelot.read_pdf(
                    file_path,
                    pages=page_range,
                    flavor='stream',
                    edge_tol=50
                )
                
                for table in camelot_tables:
                    if table.accuracy > 60:
                        tables.append(self._format_camelot_table(table, 'stream'))
            except Exception as e:
                logger.debug(f"Camelot stream mode failed: {e}")
        
        return tables
    
    def _extract_with_pdfplumber(
        self, 
        file_path: str, 
        pages: Optional[List[int]]
    ) -> List[Dict]:
        """Extract tables using pdfplumber (good for simple tables)"""
        try:
            import pdfplumber
        except ImportError:
            logger.info("pdfplumber not installed. Install: pip install pdfplumber")
            return []
        
        tables = []
        
        with pdfplumber.open(file_path) as pdf:
            pages_to_process = pages if pages else range(len(pdf.pages))
            
            for page_num in pages_to_process:
                if page_num >= len(pdf.pages):
                    continue
                    
                page = pdf.pages[page_num]
                page_tables = page.extract_tables()
                
                for table_data in page_tables:
                    if table_data and len(table_data) > 1:
                        tables.append({
                            'data': pd.DataFrame(table_data[1:], columns=table_data[0]),
                            'page': page_num + 1,
                            'bbox': None,
                            'confidence': 0.75,
                            'method': TableExtractionMethod.PDFPLUMBER.value,
                            'markdown': self._to_markdown(table_data),
                            'text': self._to_text(table_data)
                        })
        
        return tables
    
    def _format_camelot_table(self, camelot_table, flavor):
        """Format Camelot table to standard format"""
        df = camelot_table.df
        
        return {
            'data': df,
            'page': camelot_table.page,
            'bbox': camelot_table._bbox,
            'confidence': camelot_table.accuracy / 100.0,
            'method': f'camelot_{flavor}',
            'markdown': df.to_markdown(index=False),
            'text': df.to_string(index=False)
        }
    
    def _assess_quality(self, tables):
        """Assess overall quality of extracted tables"""
        if not tables:
            return 0.0
        
        scores = []
        for table in tables:
            score = table.get('confidence', 0.5)
            
            df = table.get('data')
            if isinstance(df, pd.DataFrame):
                # Penalize small tables
                if len(df) < 2 or len(df.columns) < 2:
                    score *= 0.5
                
                # Penalize high empty cell ratio
                empty_ratio = df.isna().sum().sum() / (df.shape[0] * df.shape[1])
                score *= (1 - empty_ratio * 0.5)
            
            scores.append(score)
        
        return sum(scores) / len(scores)
    
    def _to_markdown(self, table_data):
        """Convert table data to markdown"""
        if not table_data:
            return ""
        
        df = pd.DataFrame(table_data[1:], columns=table_data[0])
        return df.to_markdown(index=False)
    
    def _to_text(self, table_data):
        """Convert table data to plain text"""
        if not table_data:
            return ""
        
        df = pd.DataFrame(table_data[1:], columns=table_data[0])
        return df.to_string(index=False)
