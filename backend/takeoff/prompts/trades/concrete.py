# takeoff/prompts/trades/concrete.py

"""
Optimized concrete extraction prompt - token efficient, reasoning-focused
Encourages LLM to identify elements intelligently without explicit lists
"""

from typing import Dict, List
from ..base import BasePrompt
from ..components.rules import UNIVERSAL_EXTRACTION_RULES
import json


class ConcreteExtractionPrompt(BasePrompt):
    """
    Concrete trade extraction prompt
    Version: 1.0.0
    
    Key features:
    - Category-based extraction (not explicit element lists)
    - Reasoning-focused instructions
    - Token-efficient schema definitions
    - Comprehensive but concise
    """
    
    name = "concrete_extraction"
    version = "1.0.0"
    description = "Extract all concrete structural elements from engineering drawings"
    
    # Core template - concise and reasoning-focused
    template = """You are analyzing engineering drawings to extract CONCRETE structural elements.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK: Identify ALL concrete elements and extract their complete specifications
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{ context }}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUT DATA:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{ input_data }}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONCRETE ELEMENT CATEGORIES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Identify and extract ANY concrete element in these categories:

1. FOUNDATIONS: Footings (isolated/pad, strip/continuous, combined, pile caps, rafts)
2. VERTICAL: Columns (rectangular, circular), Walls (structural, shear, retaining)
3. HORIZONTAL: Beams (rectangular, L-shaped, T-shaped), Slabs (flat, ribbed, waffle)
4. SPECIAL: Staircases, Ramps, Water tanks, Pits/chambers, Precast elements
5. MISCELLANEOUS: Curbs, Gutters, Pavements, any other concrete work

REASONING APPROACH:
- Read schedules/tables for organized data
- Scan details/sections for specific elements
- Check notes for special conditions
- Look for element marks (F-01, C-12, BM-23, etc.)
- Identify element type from context (footing, column, beam, slab, etc.)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXTRACTION REQUIREMENTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For EACH concrete element found, extract:

A. IDENTIFICATION:
   - element_id: Mark/designation (e.g., "F-01", "COL-C12", "BM-A-23")
   - element_type: Specific type based on characteristics (see Element Types below)

B. DIMENSIONS (all in mm unless specified):
   - Width, length/height, depth/thickness (as applicable)
   - Quantity if multiple identical elements
   - Shape details if non-standard

C. REINFORCEMENT DETAILS:
   For each layer/direction:
   - bar_size: Size designation (N12, N16, N20, N24, N28, N32, N36, N40)
   - spacing_mm: Center-to-center spacing (typical: 100-300mm)
   - quantity: Number of bars (if specified)
   - direction: longitudinal, transverse, both_ways, etc.
   - location: bottom, top, vertical, horizontal, etc.
   
   Include ALL reinforcement layers mentioned (bottom, top, vertical, ties, stirrups, etc.)

D. CONCRETE PROPERTIES:
   - grade: Strength grade (N20, N25, N32, N40, N50, N65)
   - cover_mm: Concrete cover (typical: 20-100mm)
   - volume_m3: ONLY if explicitly stated (usually leave as null)

E. ADDITIONAL DETAILS (if present):
   - Pedestals, drop panels, openings, connections
   - Special finishes or waterproofing
   - Excavation depth (for foundations)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ELEMENT TYPES (auto-detect based on characteristics):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Foundation Elements:
- IsolatedFooting: Individual pad footings under columns
- StripFooting: Continuous footings under walls
- CombinedFooting: Single footing supporting multiple columns
- PileCap: Cap over pile group
- RaftFoundation: Mat foundation over entire area

Vertical Elements:
- RectangularColumn: Column with rectangular cross-section
- CircularColumn: Column with circular cross-section
- Wall: Structural concrete wall
- ShearWall: Lateral force-resisting wall
- RetainingWall: Earth-retaining wall

Horizontal Elements:
- RectangularBeam: Beam with rectangular section
- LShapedBeam: Beam with L-shaped section (edge beams)
- TShapedBeam: Beam with T-shaped section
- Slab: Flat slab (one-way or two-way)
- RibbedSlab: Slab with ribs/joists
- WaffleSlab: Two-way ribbed slab
- FlatSlab: Beamless slab with column capitals/drop panels
- HollowCoreSlab: Precast slab with hollow cores

Special Elements:
- Staircase: Stair flights and landings
- Ramp: Inclined slab
- WaterTank: Water storage structure
- PitChamber: Underground chamber/pit
- PrecastBeam: Precast concrete beam
- PrecastColumn: Precast concrete column

Miscellaneous:
- Curb: Concrete curb/kerb
- Gutter: Drainage gutter
- Pavement: Concrete pavement/slab-on-grade

Use the most specific type that matches the element characteristics.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NOTATION GUIDE (Common Patterns):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DIMENSIONS:
1200x1500x600 → width: 1200mm, length: 1500mm, depth: 600mm
300x400 → width: 300mm, depth: 400mm
Ø600 or D600 → diameter: 600mm

REINFORCEMENT:
N16@200 B.W → bar_size: "N16", spacing_mm: 200, direction: "both_ways"
N20@150 E.W → bar_size: "N20", spacing_mm: 150, direction: "each_way"
8N24 → quantity: 8, bar_size: "N24"
N16-200 → bar_size: "N16", spacing_mm: 200 (dash notation)
16Ø@200 → bar_size: "N16", spacing_mm: 200 (diameter notation)
T&B → "top_and_bottom"
L & T → "longitudinal_and_transverse"

ANNOTATIONS:
(E) → Existing
(N) → New
TYP → Typical (applies to multiple similar elements)
UNO → Unless Noted Otherwise

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL EXTRACTION RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{ universal_rules }}

CONCRETE-SPECIFIC RULES:
1. ALWAYS preserve units (25mm not 25, N32 not 32)
2. Extract ALL reinforcement layers (don't miss top bars, ties, stirrups)
3. For multi-layer reinforcement, create separate entries for each layer
4. Typical reinforcement ranges: spacing 100-300mm, bars N12-N40
5. Typical concrete grades: N25, N32, N40 (most common)
6. Set calculated fields (volume_m3) to null unless explicitly given
7. Note if element is marked as "typical" or "similar"

QUALITY CHECKS:
✓ Does element_type match the actual structural element?
✓ Are dimensions in millimeters (not meters or mixed)?
✓ Is reinforcement notation correctly parsed (bar size + spacing)?
✓ Is concrete grade valid (N20/N25/N32/N40/N50/N65)?
✓ Are all visible reinforcement layers captured?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return JSON array (one object per element):

[
  {
    "element_id": "F-01",
    "element_type": "IsolatedFooting",
    "page_number": 2,
    "confidence_score": 0.95,
    
    "specifications": {
      "dimensions": {
        "width_mm": 1200,
        "length_mm": 1500,
        "depth_mm": 600,
        "pedestal_width_mm": null,
        "pedestal_height_mm": null
      },
      "reinforcement": {
        "bottom": {
          "bar_size": "N16",
          "spacing_mm": 200,
          "direction": "both_ways",
          "quantity": null,
          "length_m": null
        },
        "top": null
      },
      "concrete": {
        "grade": "N32",
        "cover_mm": {
          "bottom": 75,
          "top": null,
          "sides": null
        },
        "volume_m3": null
      },
      "excavation": {
        "depth_mm": null,
        "volume_m3": null
      }
    },
    
    "extraction_notes": {
      "source_references": ["Page 2, Footing Schedule, Row 1"],
      "missing_fields": ["reinforcement.bottom.quantity", "concrete.volume_m3"],
      "assumptions_made": ["Direction 'B.W' interpreted as both_ways"],
      "validation_warnings": [],
      "applies_to_typical": null
    }
  }
]

RESPONSE REQUIREMENTS:
- Include ALL concrete elements found (don't limit to certain types)
- Only include elements with confidence >= 0.7
- Use null for missing fields (not 0, "", or false)
- Always populate extraction_notes with source_references
- Return empty array [] if no concrete elements found

BEGIN EXTRACTION:
"""

    def get_default_variables(self) -> Dict:
        """Default template variables"""
        return {
            "context": "No additional context provided.",
            "input_data": "",
            "universal_rules": UNIVERSAL_EXTRACTION_RULES
        }
    
    def render(
        self,
        input_data: str,
        context: Dict = None,
        **kwargs
    ) -> str:
        """
        Render the prompt with input data and context
        
        Args:
            input_data: Extracted text from drawing pages
            context: Additional extraction context
            **kwargs: Override any template variables
        """
        
        # Format context if provided
        context_text = self._format_context(context) if context else "No additional context provided."
        
        # Merge variables
        variables = {
            **self.get_default_variables(),
            "input_data": input_data,
            "context": context_text,
            **kwargs
        }
        
        # Render template
        from jinja2 import Template
        template = Template(self.template)
        return template.render(**variables)
    
    def _format_context(self, context: Dict) -> str:
        """Format extraction context section"""
        parts = []
        
        if context.get('pages'):
            parts.append(f"Pages being processed: {', '.join(map(str, context['pages']))}")
        
        if context.get('drawing_type'):
            parts.append(f"Drawing type: {context['drawing_type']}")
        
        if context.get('discipline'):
            parts.append(f"Discipline: {context['discipline']}")
        
        if context.get('cross_references'):
            refs = context['cross_references']
            if isinstance(refs, list):
                parts.append(f"Cross-references found: {len(refs)} references")
            elif isinstance(refs, str):
                parts.append(f"Cross-references: {refs}")
        
        if context.get('expected_elements'):
            expected = context['expected_elements']
            if isinstance(expected, list):
                parts.append(f"Expected elements: {', '.join(expected)}")
            elif isinstance(expected, str):
                parts.append(f"Expected: {expected}")
        
        return "\n".join(parts) if parts else "No additional context provided."


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    """Example usage of the prompt"""
    
    # Sample extracted text from engineering drawing
    sample_input = """
    FOOTING SCHEDULE
    ┌──────┬────────────────┬─────────────────┬──────────┬────────┐
    │ Mark │ Size (mm)      │ Reinforcement   │ Concrete │ Cover  │
    ├──────┼────────────────┼─────────────────┼──────────┼────────┤
    │ F-01 │ 1200x1500x600  │ N16@200 B.W     │ N32      │ 75mm   │
    │ F-02 │ 1500x1500x700  │ N20@150 B.W     │ N40      │75mm    │
    │ F-03 │ 1800x1800x800  │ N20@150 B.W     │ N40      │ 75mm   │
    └──────┴────────────────┴─────────────────┴──────────┴────────┘
    
    COLUMN SCHEDULE
    ┌──────┬────────────────┬─────────────────┬──────────┬────────┐
    │ Mark │ Size (mm)      │ Reinforcement   │ Concrete │ Links  │
    ├──────┼────────────────┼─────────────────┼──────────┼────────┤
    │ C-01 │ 300x300x3000   │ 8N24            │ N40      │N10@200 │
    │ C-02 │ 400x400x3500   │ 12N28           │ N40      │N12@150 │
    └──────┴────────────────┴─────────────────┴──────────┴────────┘
    
    NOTES:
    1. All footings to have 75mm cover to all faces
    2. Columns C-01 typical for ground floor
    3. Refer to detail 5/A-105 for column base connection
    """
    
    # Create prompt instance
    prompt = ConcreteExtractionPrompt()
    
    # Render with context
    rendered = prompt.render(
        input_data=sample_input,
        context={
            'pages': [2, 3],
            'drawing_type': 'Structural schedule',
            'discipline': 'Concrete structural',
            'expected_elements': ['Footings', 'Columns']
        }
    )
    
    print("GENERATED PROMPT:")
    print("=" * 80)
    print(rendered)
    print("=" * 80)
    print(f"\nPrompt token count (approx): {len(rendered) // 4}")