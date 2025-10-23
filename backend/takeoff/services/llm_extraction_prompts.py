# takeoff/services/llm_processor.py

from typing import Dict, List
import json
from ..schemas import ELEMENT_SCHEMAS, get_element_categories

class LLMProcessor:
    """
    Reads extracted JSON data and converts to structured takeoff elements
    """
    
    def __init__(self, modelhub):
        self.modelhub = modelhub
    
    async def process_json_to_elements(
        self, 
        raw_extraction: dict
    ) -> List[Dict]:
        """
        Main method: Takes JSON from PyMuPDF → Returns structured elements
        
        Args:
            raw_extraction: The JSON stored in DrawingPage.raw_extraction
            
        Returns:
            List of structured takeoff elements
        """
        
        # Build prompt
        prompt = self._build_extraction_prompt(raw_extraction)
        
        # Call LLM
        response = await self.modelhub.complete(
            prompt=prompt,
            response_format={"type": "json_object"},
            task_type="extraction",
            max_tokens=4000,
            temperature=0.1
        )
        
        # Parse response
        elements = self._parse_response(response)
        
        return elements
    
    def _build_extraction_prompt(self, raw_extraction: dict) -> str:
        """
        Build prompt that tells LLM to read JSON and extract takeoff elements
        """
        
        element_categories = get_element_categories()
        
        prompt = f"""You are extracting construction takeoff elements from engineering drawing data.

The data below was extracted from a PDF using text extraction. Your job is to:
1. Identify all structural elements (footings, columns, beams, slabs, etc.)
2. Extract their specifications according to the schemas provided
3. Return structured JSON data

CRITICAL RULES:
- ONLY extract data that is EXPLICITLY present in the input
- Use null for missing/unclear data
- DO NOT calculate or infer values
- Copy notations exactly as shown

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INPUT DATA (from PDF extraction):

{json.dumps(raw_extraction, indent=2)[:5000]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

AVAILABLE ELEMENT TYPES:

{json.dumps(element_categories, indent=2)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXTRACTION SCHEMAS:

For each element type, extract data according to these structures:

IsolatedFooting:
  dimensions: width_mm, length_mm, depth_mm, pedestal_width_mm, pedestal_height_mm
  reinforcement:
    bottom: bar_size, spacing_mm, direction, quantity, length_m
    top: bar_size, spacing_mm, quantity, length_m
  concrete:
    grade, cover_mm (bottom/top/sides), volume_m3

RectangularColumn:
  dimensions: width_mm, depth_mm, height_mm, quantity
  reinforcement:
    vertical: bar_size, quantity, length_m, lap_length_mm
    ties: bar_size, spacing_mm, type, legs
  concrete: grade, cover_mm, volume_m3

RectangularBeam:
  dimensions: width_mm, depth_mm, length_m, quantity
  reinforcement:
    top: bar_size, quantity, length_m, location
    bottom: bar_size, quantity, length_m, location
    stirrups: bar_size, spacing_mm, type, legs
  concrete: grade, cover_mm (bottom/sides/top), volume_m3

(Similar schemas for all 33 element types - see full schema reference)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

COMMON PATTERNS IN ENGINEERING DRAWINGS:

Tables (most common):
  Mark | Size (mm)      | Reinforcement | Concrete | Cover
  F-01 | 1200x1500x600  | N16@200 B.W  | N32      | 75mm
  
  → Extract:
    - element_id: "F-01"
    - dimensions from "1200x1500x600" (width x length x depth)
    - bar_size: "N16", spacing_mm: 200 from "N16@200"
    - direction: "both" from "B.W"
    - grade: "N32"
    - cover_mm.bottom: 75

Text format:
  "FOOTING F-01: 1200x1500x600, N16@200 B.W, N32 Concrete, 75mm cover"
  
  → Same extraction as above

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OUTPUT FORMAT:

Return JSON array:
[
  {{
    "element_id": "F-01",
    "element_type": "IsolatedFooting",
    "confidence_score": 0.95,
    "specifications": {{
      "dimensions": {{"width_mm": 1200, "length_mm": 1500, "depth_mm": 600, ...}},
      "reinforcement": {{"bottom": {{"bar_size": "N16", "spacing_mm": 200, ...}}, "top": null}},
      "concrete": {{"grade": "N32", "cover_mm": {{"bottom": 75, ...}}, ...}}
    }},
    "extraction_notes": {{
      "source_references": ["Table row 1"],
      "missing_fields": ["volume_m3"],
      "assumptions_made": []
    }}
  }}
]

Only include elements with confidence >= 0.7
Return empty array [] if no elements found
"""
        
        return prompt
    
    def _parse_response(self, response: Dict) -> List[Dict]:
        """Parse LLM response into list of elements"""
        
        parsed = response.get('parsed_json', [])
        
        # Handle wrapped response
        if isinstance(parsed, dict):
            parsed = parsed.get('elements', [])
        
        if not isinstance(parsed, list):
            return []
        
        return parsed