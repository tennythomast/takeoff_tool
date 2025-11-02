"""
Count Analyzer Service for Takeoff Elements

This service analyzes engineering drawings to extract counts of elements
by leveraging:
1. Element IDs extracted from the drawings
2. Page numbers where elements are located
3. Vector/chunk data from the RAG service
4. Pattern matching and NLP to identify counts

The analyzer can:
- Find explicit counts mentioned near element IDs
- Detect patterns like "4 No.", "QTY: 12", "x8", etc.
- Flag elements where counts couldn't be determined
- Extract position/location information for elements
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from django.db.models import Q
from asgiref.sync import sync_to_async

from takeoff.models import TakeoffElement, Drawing, TakeoffExtraction
from rag_service.models import Document, DocumentPage, Chunk

logger = logging.getLogger(__name__)


class CountAnalyzer:
    """
    Analyzes engineering drawings to extract element counts using
    vector data and pattern matching
    """
    
    # Common count patterns in engineering drawings
    COUNT_PATTERNS = [
        # "4 No.", "4No.", "4 no"
        (r'(\d+)\s*[Nn][Oo]\.?', 'no_pattern'),
        # "QTY: 12", "QTY 12", "Qty:12"
        (r'[Qq][Tt][Yy][\s:]*(\d+)', 'qty_pattern'),
        # "x8", "X 8", "x 8"
        (r'[xX]\s*(\d+)', 'x_pattern'),
        # "8 OFF", "8OFF"
        (r'(\d+)\s*[Oo][Ff][Ff]', 'off_pattern'),
        # "(4)", "[4]"
        (r'[\(\[](\d+)[\)\]]', 'bracket_pattern'),
        # "COUNT: 5", "Count 5"
        (r'[Cc][Oo][Uu][Nn][Tt][\s:]*(\d+)', 'count_pattern'),
        # "TOTAL: 15", "Total 15"
        (r'[Tt][Oo][Tt][Aa][Ll][\s:]*(\d+)', 'total_pattern'),
        # Just a number near the element ID (last resort)
        (r'\b(\d+)\b', 'number_pattern'),
    ]
    
    # Patterns to exclude (dimensions, dates, etc.)
    EXCLUDE_PATTERNS = [
        r'\d+mm',  # dimensions
        r'\d+m',
        r'\d+\s*x\s*\d+',  # dimensions like "200 x 300"
        r'\d{4}[-/]\d{2}[-/]\d{2}',  # dates
        r'N\d+',  # rebar sizes like N16, N20
        r'\d+MPa',  # concrete grades
    ]
    
    def __init__(self):
        """Initialize the count analyzer"""
        self.logger = logging.getLogger(__name__)
    
    async def analyze_extraction(
        self,
        extraction_id: str,
        update_elements: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze all elements in an extraction to find counts
        
        Args:
            extraction_id: ID of the TakeoffExtraction
            update_elements: Whether to update element records with found counts
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Get the extraction
            extraction = await sync_to_async(
                lambda: TakeoffExtraction.objects.select_related('drawing').get(id=extraction_id)
            )()
            
            # Get all elements for this extraction
            elements = await sync_to_async(
                lambda: list(TakeoffElement.objects.filter(extraction=extraction).order_by('page_number', 'element_id'))
            )()
            
            self.logger.info(f"Analyzing {len(elements)} elements from extraction {extraction_id}")
            
            results = {
                'extraction_id': str(extraction_id),
                'drawing_id': str(extraction.drawing.id),
                'total_elements': len(elements),
                'elements_with_count': 0,
                'elements_without_count': 0,
                'elements_flagged': 0,
                'element_results': []
            }
            
            # Analyze each element
            for element in elements:
                element_result = await self.analyze_element(element)
                results['element_results'].append(element_result)
                
                if element_result['count_found']:
                    results['elements_with_count'] += 1
                    
                    # Update element if requested
                    if update_elements and element_result['count'] is not None:
                        await self._update_element_count(element, element_result)
                else:
                    results['elements_without_count'] += 1
                    
                if element_result['flagged']:
                    results['elements_flagged'] += 1
            
            self.logger.info(
                f"Analysis complete: {results['elements_with_count']}/{results['total_elements']} "
                f"elements have counts, {results['elements_flagged']} flagged"
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error analyzing extraction: {e}")
            raise
    
    async def analyze_element(self, element: TakeoffElement) -> Dict[str, Any]:
        """
        Analyze a single element to extract count and position
        
        Args:
            element: TakeoffElement instance
            
        Returns:
            Dictionary with analysis results for the element
        """
        result = {
            'element_id': element.element_id,
            'element_type': element.element_type,
            'page_number': element.page_number,
            'count': None,
            'count_found': False,
            'count_confidence': 0.0,
            'count_method': None,
            'position': None,
            'flagged': False,
            'flag_reason': None,
            'context_text': None
        }
        
        try:
            # Get the document and page data
            drawing = await sync_to_async(lambda: element.drawing)()
            rag_document = await sync_to_async(lambda: drawing.rag_document)()
            
            if not rag_document:
                result['flagged'] = True
                result['flag_reason'] = 'No RAG document linked to drawing'
                return result
            
            # Get the specific page chunks/content
            page_content = await self._get_page_content(
                rag_document,
                element.page_number,
                element.element_id
            )
            
            if not page_content:
                result['flagged'] = True
                result['flag_reason'] = 'No content found for page'
                return result
            
            # Search for count near the element ID
            count_data = self._extract_count_from_text(
                page_content,
                element.element_id,
                element.element_type
            )
            
            if count_data:
                result['count'] = count_data['count']
                result['count_found'] = True
                result['count_confidence'] = count_data['confidence']
                result['count_method'] = count_data['method']
                result['context_text'] = count_data['context']
                
                # Extract position if available
                position = self._extract_position(page_content, element.element_id)
                if position:
                    result['position'] = position
            else:
                result['flagged'] = True
                result['flag_reason'] = 'Count not found in document'
                result['context_text'] = page_content[:200] if page_content else None
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error analyzing element {element.element_id}: {e}")
            result['flagged'] = True
            result['flag_reason'] = f'Analysis error: {str(e)}'
            return result
    
    async def _get_page_content(
        self,
        document: Document,
        page_number: int,
        element_id: str
    ) -> Optional[str]:
        """
        Get the text content for a specific page, focusing on areas near the element ID
        
        Args:
            document: RAG Document instance
            page_number: Page number to retrieve
            element_id: Element ID to search for
            
        Returns:
            Text content from the page
        """
        try:
            # Try to get DocumentPage first
            page = await sync_to_async(
                lambda: DocumentPage.objects.filter(
                    document=document,
                    page_number=page_number
                ).first()
            )()
            
            if page:
                # Get page content
                content = await sync_to_async(lambda: page.content)()
                if content:
                    return content
            
            # Fall back to chunks
            chunks = await sync_to_async(
                lambda: list(Chunk.objects.filter(
                    document=document,
                    metadata__page_number=page_number
                ).order_by('chunk_index'))
            )()
            
            if chunks:
                # Combine chunk content
                combined_content = '\n'.join([chunk.content for chunk in chunks])
                return combined_content
            
            # Last resort: search all chunks for element ID
            chunks_with_id = await sync_to_async(
                lambda: list(Chunk.objects.filter(
                    document=document,
                    content__icontains=element_id
                ))
            )()
            
            if chunks_with_id:
                return '\n'.join([chunk.content for chunk in chunks_with_id])
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting page content: {e}")
            return None
    
    def _extract_count_from_text(
        self,
        text: str,
        element_id: str,
        element_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract count from text using pattern matching
        
        Args:
            text: Text content to search
            element_id: Element ID to search near
            element_type: Type of element
            
        Returns:
            Dictionary with count data or None
        """
        if not text:
            return None
        
        # Find the element ID in the text
        element_pattern = re.escape(element_id)
        matches = list(re.finditer(element_pattern, text, re.IGNORECASE))
        
        if not matches:
            # Element ID not found in text
            return None
        
        best_count = None
        best_confidence = 0.0
        best_method = None
        best_context = None
        
        # Search around each occurrence of the element ID
        for match in matches:
            start_pos = match.start()
            
            # Get context window (100 chars before and after)
            context_start = max(0, start_pos - 100)
            context_end = min(len(text), start_pos + 100)
            context = text[context_start:context_end]
            
            # Try each count pattern
            for pattern, method in self.COUNT_PATTERNS:
                count_matches = list(re.finditer(pattern, context))
                
                for count_match in count_matches:
                    # Check if this looks like a dimension or other excluded pattern
                    if self._is_excluded_number(context, count_match):
                        continue
                    
                    try:
                        count_value = int(count_match.group(1))
                        
                        # Validate count (reasonable range)
                        if count_value < 1 or count_value > 10000:
                            continue
                        
                        # Calculate confidence based on pattern type and proximity
                        distance = abs(count_match.start() - (start_pos - context_start))
                        confidence = self._calculate_confidence(method, distance, context)
                        
                        if confidence > best_confidence:
                            best_count = count_value
                            best_confidence = confidence
                            best_method = method
                            best_context = context.strip()
                    
                    except (ValueError, IndexError):
                        continue
        
        if best_count is not None:
            return {
                'count': best_count,
                'confidence': best_confidence,
                'method': best_method,
                'context': best_context
            }
        
        return None
    
    def _is_excluded_number(self, context: str, match: re.Match) -> bool:
        """Check if a number match should be excluded (dimension, date, etc.)"""
        # Get surrounding text
        start = max(0, match.start() - 10)
        end = min(len(context), match.end() + 10)
        surrounding = context[start:end]
        
        # Check against exclude patterns
        for pattern in self.EXCLUDE_PATTERNS:
            if re.search(pattern, surrounding, re.IGNORECASE):
                return True
        
        return False
    
    def _calculate_confidence(self, method: str, distance: int, context: str) -> float:
        """
        Calculate confidence score for a count match
        
        Higher confidence for:
        - Explicit count patterns (QTY, No., etc.)
        - Closer proximity to element ID
        - Clear context
        """
        # Base confidence by method
        method_confidence = {
            'qty_pattern': 0.95,
            'no_pattern': 0.90,
            'count_pattern': 0.90,
            'total_pattern': 0.85,
            'off_pattern': 0.80,
            'x_pattern': 0.75,
            'bracket_pattern': 0.70,
            'number_pattern': 0.50,  # Low confidence for bare numbers
        }
        
        base_conf = method_confidence.get(method, 0.5)
        
        # Proximity bonus (closer = higher confidence)
        proximity_factor = max(0, 1.0 - (distance / 100.0))
        
        # Final confidence
        confidence = base_conf * (0.7 + 0.3 * proximity_factor)
        
        return min(1.0, confidence)
    
    def _extract_position(self, text: str, element_id: str) -> Optional[Dict[str, Any]]:
        """
        Extract position/location information for an element
        
        Looks for:
        - Grid references (e.g., "A-1", "Grid B/3")
        - Coordinates
        - Location descriptions
        """
        if not text:
            return None
        
        # Find element ID position
        element_pattern = re.escape(element_id)
        match = re.search(element_pattern, text, re.IGNORECASE)
        
        if not match:
            return None
        
        # Get context around element ID
        start_pos = match.start()
        context_start = max(0, start_pos - 150)
        context_end = min(len(text), start_pos + 150)
        context = text[context_start:context_end]
        
        position_data = {}
        
        # Look for grid references
        grid_pattern = r'[Gg]rid\s*([A-Z]\d*[-/]?\d*)|([A-Z]\d*[-/]\d*)'
        grid_matches = re.findall(grid_pattern, context)
        if grid_matches:
            grids = [g[0] or g[1] for g in grid_matches if g[0] or g[1]]
            if grids:
                position_data['grid_reference'] = grids[0]
        
        # Look for level/floor
        level_pattern = r'[Ll]evel\s*(\d+|[A-Z]+)|[Ff]loor\s*(\d+)'
        level_match = re.search(level_pattern, context)
        if level_match:
            position_data['level'] = level_match.group(1) or level_match.group(2)
        
        # Look for zone/area
        zone_pattern = r'[Zz]one\s*([A-Z0-9]+)|[Aa]rea\s*([A-Z0-9]+)'
        zone_match = re.search(zone_pattern, context)
        if zone_match:
            position_data['zone'] = zone_match.group(1) or zone_match.group(2)
        
        return position_data if position_data else None
    
    async def _update_element_count(
        self,
        element: TakeoffElement,
        count_data: Dict[str, Any]
    ) -> None:
        """
        Update element with extracted count information
        
        Args:
            element: TakeoffElement to update
            count_data: Dictionary with count analysis results
        """
        try:
            # Update specifications with count data
            specs = element.specifications or {}
            specs['quantity'] = count_data['count']
            specs['quantity_confidence'] = count_data['count_confidence']
            specs['quantity_method'] = count_data['count_method']
            
            if count_data.get('position'):
                specs['position'] = count_data['position']
            
            # Update extraction notes
            notes = element.extraction_notes or {}
            notes['count_analysis'] = {
                'analyzed_at': str(timezone.now()),
                'context': count_data.get('context_text'),
                'method': count_data['count_method']
            }
            
            # Save updates
            await sync_to_async(lambda: TakeoffElement.objects.filter(id=element.id).update(
                specifications=specs,
                extraction_notes=notes
            ))()
            
            self.logger.debug(f"Updated element {element.element_id} with count {count_data['count']}")
            
        except Exception as e:
            self.logger.error(f"Error updating element {element.element_id}: {e}")
    
    async def analyze_drawing(
        self,
        drawing_id: str,
        update_elements: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze all elements in a drawing across all extractions
        
        Args:
            drawing_id: ID of the Drawing
            update_elements: Whether to update element records
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Get the latest extraction for this drawing
            extraction = await sync_to_async(
                lambda: TakeoffExtraction.objects.filter(
                    drawing_id=drawing_id
                ).order_by('-extraction_date').first()
            )()
            
            if not extraction:
                return {
                    'success': False,
                    'error': 'No extractions found for drawing'
                }
            
            # Analyze the extraction
            results = await self.analyze_extraction(
                str(extraction.id),
                update_elements=update_elements
            )
            
            results['success'] = True
            return results
            
        except Exception as e:
            self.logger.error(f"Error analyzing drawing: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Import timezone at the top if not already imported
from django.utils import timezone
