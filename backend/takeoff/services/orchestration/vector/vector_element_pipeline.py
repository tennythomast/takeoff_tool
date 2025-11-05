"""
Vector Element Detection Pipeline

Orchestrates the complete vector-based element detection workflow:
1. Extract text elements from PDF (vector_text_extractor)
2. Detect all shapes (lines, arcs, rectangles, circles, polygons)
3. Find symbols near text labels
4. Associate symbols with their text labels
5. Generate structured element occurrences

This pipeline combines text extraction with geometric shape detection
to identify element occurrences in engineering drawings.
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import fitz  # PyMuPDF

try:
    from ...extractors.vector_text_extractor import VectorTextExtractor
    from ...measurement.vector import ShapeDetector, ShapeClassifier, LineDetector
except ImportError:
    # Fallback for standalone execution
    import sys
    sys.path.insert(0, '/app/backend')
    from takeoff.services.extractors.vector_text_extractor import VectorTextExtractor
    from takeoff.services.measurement.vector import ShapeDetector, ShapeClassifier, LineDetector

logger = logging.getLogger(__name__)


@dataclass
class ElementOccurrence:
    """Represents a detected element occurrence with text and symbol"""
    element_name: str
    text_bbox: Tuple[float, float, float, float]
    text_center: Tuple[float, float]
    symbol: Optional[Dict] = None
    symbol_type: Optional[str] = None
    symbol_size_mm: Optional[float] = None
    distance_to_symbol_mm: Optional[float] = None
    page_number: int = 1
    confidence: float = 1.0


@dataclass
class PipelineResults:
    """Complete results from the vector element pipeline"""
    page_number: int
    text_elements: List[Dict]
    shapes: Dict[str, List[Dict]]
    element_occurrences: List[ElementOccurrence]
    statistics: Dict[str, int]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization"""
        import fitz
        
        def make_serializable(obj):
            """Convert non-serializable objects to serializable format"""
            if isinstance(obj, fitz.Rect):
                # Convert Rect to list [x0, y0, x1, y1]
                return [obj.x0, obj.y0, obj.x1, obj.y1]
            elif isinstance(obj, fitz.Point):
                # Convert Point to list [x, y]
                return [obj.x, obj.y]
            elif isinstance(obj, tuple):
                return list(obj)
            elif isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(item) for item in obj]
            else:
                return obj
        
        return {
            'page_number': self.page_number,
            'text_elements': make_serializable(self.text_elements),
            'shapes': make_serializable(self.shapes),
            'element_occurrences': [make_serializable(asdict(occ)) for occ in self.element_occurrences],
            'statistics': make_serializable(self.statistics)
        }


class VectorElementPipeline:
    """
    Orchestrates vector-based element detection pipeline
    
    Pipeline stages:
    1. Text extraction
    2. Shape detection
    3. Symbol-label association
    4. Element occurrence generation
    """
    
    def __init__(
        self,
        symbol_search_radius_mm: float = 17.0,
        min_shape_size_mm: float = 3.0,
        max_shape_size_mm: float = 150.0
    ):
        """
        Initialize pipeline
        
        Args:
            symbol_search_radius_mm: Radius to search for symbols near text labels
            min_shape_size_mm: Minimum shape size to detect
            max_shape_size_mm: Maximum shape size to detect
        """
        self.symbol_search_radius_mm = symbol_search_radius_mm
        self.min_shape_size_mm = min_shape_size_mm
        self.max_shape_size_mm = max_shape_size_mm
        
        # Initialize extractors and detectors
        self.text_extractor = VectorTextExtractor()
        self.shape_detector = ShapeDetector()
        
        # Configure shape detector
        self.shape_detector.line_detector = LineDetector(
            min_length_mm=min_shape_size_mm,
            max_length_mm=max_shape_size_mm
        )
        
        logger.info(
            f"VectorElementPipeline initialized: "
            f"symbol_radius={symbol_search_radius_mm}mm, "
            f"shape_size={min_shape_size_mm}-{max_shape_size_mm}mm"
        )
    
    async def process_page(
        self,
        pdf_path: str,
        page_number: int = 0
    ) -> PipelineResults:
        """
        Process a single PDF page through the complete pipeline
        
        Args:
            pdf_path: Path to PDF file
            page_number: Page number (0-indexed)
            
        Returns:
            PipelineResults with all detected elements and shapes
        """
        logger.info(f"Processing page {page_number + 1} from {pdf_path}")
        
        # Open PDF
        doc = fitz.open(pdf_path)
        page = doc[page_number]
        
        try:
            # Stage 1: Extract text elements
            logger.info("[1/4] Extracting text elements...")
            text_elements = await self._extract_text_elements(page)
            logger.info(f"   Found {len(text_elements)} text elements")
            
            # Stage 2: Detect shapes
            logger.info("[2/4] Detecting shapes...")
            shapes = self._detect_shapes(page)
            total_shapes = shapes['total_shapes']
            logger.info(
                f"   Found {total_shapes} shapes: "
                f"{len(shapes['rectangles'])} rectangles, "
                f"{len(shapes['circles'])} circles, "
                f"{len(shapes['polygons'])} polygons"
            )
            
            # Stage 3: Find symbols near text labels
            logger.info("[3/4] Finding symbols near text labels...")
            label_positions = self._extract_label_positions(text_elements)
            symbols = self._detect_symbols_near_labels(page, label_positions)
            logger.info(f"   Found {len(symbols)} symbols near {len(label_positions)} labels")
            
            # Stage 4: Associate symbols with text labels
            logger.info("[4/4] Associating symbols with labels...")
            element_occurrences = self._associate_symbols_with_labels(
                text_elements,
                symbols
            )
            logger.info(f"   Created {len(element_occurrences)} element occurrences")
            
            # Generate statistics
            statistics = self._generate_statistics(
                text_elements,
                shapes,
                symbols,
                element_occurrences
            )
            
            results = PipelineResults(
                page_number=page_number + 1,
                text_elements=text_elements,
                shapes=shapes,
                element_occurrences=element_occurrences,
                statistics=statistics
            )
            
            logger.info(f"✅ Pipeline complete for page {page_number + 1}")
            return results
            
        finally:
            doc.close()
    
    async def _extract_text_elements(self, page: fitz.Page) -> List[Dict]:
        """
        Extract text elements from page using PyMuPDF directly
        
        Returns:
            List of text element dictionaries with bbox, center, text, etc.
        """
        # Extract text with PyMuPDF (simpler, no file dependency)
        text_elements = []
        
        # Get text blocks with positions
        blocks = page.get_text("dict")['blocks']
        
        for block in blocks:
            if block.get('type') != 0:  # Skip non-text blocks
                continue
            
            for line in block.get('lines', []):
                for span in line.get('spans', []):
                    text = span.get('text', '').strip()
                    if not text:
                        continue
                    
                    bbox = span.get('bbox', [0, 0, 0, 0])
                    
                    text_elements.append({
                        'text': text,
                        'bbox': {
                            'x0': bbox[0],
                            'y0': bbox[1],
                            'x1': bbox[2],
                            'y1': bbox[3]
                        },
                        'center': {
                            'x': (bbox[0] + bbox[2]) / 2,
                            'y': (bbox[1] + bbox[3]) / 2
                        },
                        'font_name': span.get('font', 'unknown'),
                        'font_size': span.get('size', 0),
                        'color': span.get('color', 0),
                        'flags': span.get('flags', 0)
                    })
        
        return text_elements
    
    def _detect_shapes(self, page: fitz.Page) -> Dict[str, List[Dict]]:
        """
        Detect all shapes on the page
        
        Returns:
            Dictionary with rectangles, circles, polygons, and total count
        """
        return self.shape_detector.detect_all_shapes(page)
    
    def _extract_label_positions(self, text_elements: List[Dict]) -> List[Tuple[float, float]]:
        """
        Extract center positions of text labels for symbol detection
        
        Args:
            text_elements: List of text element dictionaries
            
        Returns:
            List of (x, y) center positions
        """
        positions = []
        for element in text_elements:
            center = element.get('center', {})
            if center:
                positions.append((center['x'], center['y']))
        
        return positions
    
    def _detect_symbols_near_labels(
        self,
        page: fitz.Page,
        label_positions: List[Tuple[float, float]]
    ) -> List[Dict]:
        """
        Detect symbols (tiny stroke shapes) near text labels
        
        Args:
            page: PyMuPDF page object
            label_positions: List of (x, y) label positions
            
        Returns:
            List of detected symbols with metadata
        """
        if not label_positions:
            return []
        
        return self.shape_detector.detect_symbols_near_labels(
            page,
            label_positions,
            radius_mm=self.symbol_search_radius_mm
        )
    
    def _associate_symbols_with_labels(
        self,
        text_elements: List[Dict],
        symbols: List[Dict]
    ) -> List[ElementOccurrence]:
        """
        Associate detected symbols with their nearest text labels
        
        Args:
            text_elements: List of text elements
            symbols: List of detected symbols
            
        Returns:
            List of ElementOccurrence objects
        """
        element_occurrences = []
        matched_text_indices = set()  # Track which text elements have been matched
        
        # For each symbol, find the closest text label
        for symbol in symbols:
            symbol_center = symbol['center']
            
            # Find closest text element
            closest_text = None
            closest_text_idx = None
            min_distance = float('inf')
            
            for idx, text_elem in enumerate(text_elements):
                text_center = text_elem['center']
                distance = self._calculate_distance(
                    symbol_center[0], symbol_center[1],
                    text_center['x'], text_center['y']
                )
                
                if distance < min_distance:
                    min_distance = distance
                    closest_text = text_elem
                    closest_text_idx = idx
            
            if closest_text:
                # Mark this text element as matched
                matched_text_indices.add(closest_text_idx)
                
                # Create element occurrence
                occurrence = ElementOccurrence(
                    element_name=closest_text['text'],
                    text_bbox=(
                        closest_text['bbox']['x0'],
                        closest_text['bbox']['y0'],
                        closest_text['bbox']['x1'],
                        closest_text['bbox']['y1']
                    ),
                    text_center=(
                        closest_text['center']['x'],
                        closest_text['center']['y']
                    ),
                    symbol=symbol,
                    symbol_type=symbol['type'],
                    symbol_size_mm=symbol.get('diameter_mm') or symbol.get('width_mm'),
                    distance_to_symbol_mm=symbol.get('distance_from_label_mm'),
                    page_number=1,
                    confidence=1.0
                )
                
                element_occurrences.append(occurrence)
        
        # Also include text elements without symbols
        for idx, text_elem in enumerate(text_elements):
            if idx not in matched_text_indices:
                occurrence = ElementOccurrence(
                    element_name=text_elem['text'],
                    text_bbox=(
                        text_elem['bbox']['x0'],
                        text_elem['bbox']['y0'],
                        text_elem['bbox']['x1'],
                        text_elem['bbox']['y1']
                    ),
                    text_center=(
                        text_elem['center']['x'],
                        text_elem['center']['y']
                    ),
                    symbol=None,
                    symbol_type=None,
                    symbol_size_mm=None,
                    distance_to_symbol_mm=None,
                    page_number=1,
                    confidence=0.5  # Lower confidence without symbol
                )
                
                element_occurrences.append(occurrence)
        
        return element_occurrences
    
    def _calculate_distance(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float
    ) -> float:
        """Calculate Euclidean distance between two points"""
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    
    def _generate_statistics(
        self,
        text_elements: List[Dict],
        shapes: Dict[str, List[Dict]],
        symbols: List[Dict],
        element_occurrences: List[ElementOccurrence]
    ) -> Dict[str, int]:
        """Generate pipeline statistics"""
        
        # Count element occurrences by name
        element_counts = {}
        for occ in element_occurrences:
            name = occ.element_name
            element_counts[name] = element_counts.get(name, 0) + 1
        
        # Categorize shapes
        shape_categories = ShapeClassifier.categorize_by_type(shapes)
        
        return {
            'total_text_elements': len(text_elements),
            'total_shapes': shapes['total_shapes'],
            'rectangles': len(shapes['rectangles']),
            'squares': shape_categories['squares'],
            'circles': len(shapes['circles']),
            'polygons': len(shapes['polygons']),
            'symbols_detected': len(symbols),
            'element_occurrences': len(element_occurrences),
            'occurrences_with_symbols': sum(1 for occ in element_occurrences if occ.symbol),
            'occurrences_without_symbols': sum(1 for occ in element_occurrences if not occ.symbol),
            'unique_elements': len(element_counts),
            'element_counts': element_counts
        }
    
    def filter_element_occurrences(
        self,
        occurrences: List[ElementOccurrence],
        element_names: Optional[List[str]] = None,
        min_confidence: float = 0.0,
        require_symbol: bool = False
    ) -> List[ElementOccurrence]:
        """
        Filter element occurrences by criteria
        
        Args:
            occurrences: List of element occurrences
            element_names: Filter by specific element names (e.g., ['BP1', 'BP3'])
            min_confidence: Minimum confidence threshold
            require_symbol: Only include occurrences with detected symbols
            
        Returns:
            Filtered list of element occurrences
        """
        filtered = occurrences
        
        if element_names:
            filtered = [occ for occ in filtered if occ.element_name in element_names]
        
        if min_confidence > 0:
            filtered = [occ for occ in filtered if occ.confidence >= min_confidence]
        
        if require_symbol:
            filtered = [occ for occ in filtered if occ.symbol is not None]
        
        return filtered
    
    def group_occurrences_by_element(
        self,
        occurrences: List[ElementOccurrence]
    ) -> Dict[str, List[ElementOccurrence]]:
        """
        Group element occurrences by element name
        
        Args:
            occurrences: List of element occurrences
            
        Returns:
            Dictionary mapping element names to their occurrences
        """
        grouped = {}
        for occ in occurrences:
            if occ.element_name not in grouped:
                grouped[occ.element_name] = []
            grouped[occ.element_name].append(occ)
        
        return grouped


# Convenience function for quick processing
async def process_pdf_page(
    pdf_path: str,
    page_number: int = 0,
    symbol_radius_mm: float = 17.0
) -> PipelineResults:
    """
    Convenience function to process a PDF page
    
    Args:
        pdf_path: Path to PDF file
        page_number: Page number (0-indexed)
        symbol_radius_mm: Radius to search for symbols near labels
        
    Returns:
        PipelineResults with all detected elements
    """
    pipeline = VectorElementPipeline(symbol_search_radius_mm=symbol_radius_mm)
    return await pipeline.process_page(pdf_path, page_number)
