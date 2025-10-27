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
🎯 CRITICAL: EXTRACT ONLY FROM SCHEDULES/TABLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ MANDATORY EXTRACTION RULES:

1. **ONLY extract elements from SCHEDULES or TABLES**
   - Look for organized tabular data (rows and columns)
   - Common schedule names: "FOOTING SCHEDULE", "COLUMN SCHEDULE", "BEAM SCHEDULE", "SLAB SCHEDULE"
   - Tables typically have headers like: Mark, Size, Reinforcement, Concrete Grade, etc.

2. **REQUIRED: Element MUST have dimensions**
   - MUST have at least ONE of: Width, Length, Depth, or Diameter
   - If no dimensions are present, DO NOT extract the element
   - Dimensions must be actual numbers (not "varies", "TBD", "see detail")

3. **IGNORE the following:**
   ❌ General notes or text descriptions
   ❌ Detail callouts ("see detail", "refer to", "typical")
   ❌ Title blocks, legends, or keys
   ❌ Elements without proper dimensions
   ❌ References to other drawings
   ❌ Construction notes or specifications

4. **CONCRETE ELEMENT CATEGORIES** (only from schedules/tables):
   - FOUNDATIONS: Footings, Pile caps, Rafts
   - VERTICAL: Columns, Walls
   - HORIZONTAL: Beams, Slabs
   - SPECIAL: Stairs, Ramps, Tanks

EXTRACTION APPROACH:
1. Find schedules/tables in the drawing
2. For each row in the schedule, check if it has dimensions
3. If dimensions exist, extract the complete element data
4. If no dimensions, skip that element entirely

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXTRACTION REQUIREMENTS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For EACH concrete element found, extract:

A. IDENTIFICATION (from schedule/table row):
   ⚠️ CRITICAL: Element MUST have a valid ID
   - element_id: Mark/designation from the schedule (e.g., "F-01", "COL-C12", "BM-A-23")
   - element_type: Specific type (IsolatedFooting, RectangularColumn, RectangularBeam, etc.)
   
   ❌ SKIP elements without a proper ID:
   - If ID column is empty, blank, or contains "-", skip this row
   - If ID is just a number without context (e.g., "1", "2", "3"), skip it
   - If ID is descriptive text (e.g., "see detail", "typical", "notes"), skip it
   - ONLY extract rows with actual element marks/designations

B. DIMENSIONS (MANDATORY - all in mm):
   ⚠️ CRITICAL: Element MUST have at least ONE dimension
   - Width (mm) - required for most elements
   - Length/Height (mm) - required for most elements
   - Depth/Thickness (mm) - required for slabs, footings
   - Diameter (mm) - for circular columns/piles
   
   If NONE of these dimensions are present, DO NOT extract this element

C. REINFORCEMENT DETAILS (only if present in schedule):
   - TOP_REINF: Top/main reinforcement as shown
   - BOT_REINF: Bottom/secondary reinforcement as shown
   - SIDE_REINF: Side/transverse reinforcement (ties, stirrups, links) as shown
   
   Extract EXACTLY as written in the schedule - do not interpret or convert

D. CONCRETE PROPERTIES (only if present in schedule):
   - GRADE: Strength grade as shown (e.g., N20, N25, N32, N40, N50, N65)
   - COVER: Concrete cover in mm as shown
   
   Extract EXACTLY as written - do not assume or calculate

E. ADDITIONAL DETAILS (only if explicitly shown in schedule):
   - LOCATION: Physical location from schedule
   - ZONE: Building zone if specified
   - LEVEL: Floor/level if specified
   - NOTES: Brief notes from schedule only

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
DIMENSION PARSING (if in format like "1200x1500x600"):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If dimensions are in combined format, split them:
- 1200x1500x600 → WIDTH: 1200, LENGTH: 1500, DEPTH: 600
- 300x400 → WIDTH: 300, DEPTH: 400
- Ø600 or D600 → Use as diameter in WIDTH field

Otherwise, extract dimensions from their respective columns in the schedule


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL EXTRACTION RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{ universal_rules }}

CONCRETE-SPECIFIC RULES:
1. Extract ONLY what is explicitly shown in the schedule/table
2. DO NOT interpret, calculate, or assume any values
3. DO NOT convert units - extract exactly as written
4. If a field is empty or missing in the schedule, use dash (-)
5. DO NOT add typical values or make educated guesses
6. Copy values exactly as they appear in the schedule

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (TABLE - ULTRA COMPACT):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return a CSV-style table with pipe delimiters. One row per element.

HEADER ROW (always include):
ID|TYPE|PAGE|WIDTH|LENGTH|DEPTH|TOP_REINF|BOT_REINF|SIDE_REINF|GRADE|COVER|FINISH|LOCATION|ZONE|LEVEL|TYPICAL|NOTES

DATA ROWS:
- Use pipe | as delimiter
- Use dash - for missing/not applicable values
- Dimensions in mm (numbers only)
- Reinforcement: bar_size@spacing or fabric_type (e.g., N16@200, SL92, 4N20)
- Multiple values in same field: use semicolon (e.g., "N16@200;N12@300")
- Notes: brief, key info only

EXAMPLE:
```
ID|TYPE|PAGE|WIDTH|LENGTH|DEPTH|TOP_REINF|BOT_REINF|SIDE_REINF|GRADE|COVER|FINISH|LOCATION|ZONE|LEVEL|TYPICAL|NOTES
PF.1|IsolatedFooting|1|900|900|600|SL92|-|-|N32|40|-|Grid A1|Zone A|Ground|-|Standard pad
PF.2|IsolatedFooting|1|1200|1200|600|SL102|-|-|N32|40|-|Grid B2-B4|Zone A|Ground|TYP|Typical pad
C1|RectangularColumn|2|400|400|3000|8N20|-|N12@150|N32|50|F2|Grid lines|Zone B|L1-L3|TYP|Typical column
BM1|RectangularBeam|2|300|600|-|2N16|3N20|-|N32|40|-|Grid A-B|Zone A|Level 1|-|Main beam
SF1|StripFooting|1|1000|-|650|N16@200|N16@200|-|N32|75|-|Perimeter|All|Ground|-|Continuous footing
```

COLUMN DEFINITIONS:
- ID: Element mark/designation (e.g., PF.1, C-12, BM-A-23)
- TYPE: Element type (IsolatedFooting, RectangularColumn, RectangularBeam, etc.)
- PAGE: Page number where element is shown
- WIDTH: Width in mm
- LENGTH: Length in mm (or height for vertical elements)
- DEPTH: Depth/thickness in mm
- TOP_REINF: Top/main reinforcement (format: bar_size@spacing or fabric or quantity+size)
- BOT_REINF: Bottom/secondary reinforcement
- SIDE_REINF: Side/transverse reinforcement (ties, stirrups, links)
- GRADE: Concrete grade (N20, N25, N32, N40, N50, N65)
- COVER: Concrete cover in mm (single value or specify if varies)
- FINISH: Surface finish (F1=trowel, F2=float, F3=broom, F4=off-form, etc.)
- LOCATION: Physical location (grid lines, area description)
- ZONE: Building zone or area designation
- LEVEL: Floor/level designation (Ground, L1, L2, Roof, etc.)
- TYPICAL: Mark as TYP if typical/repeated element, or note what it's typical to
- NOTES: Critical info (embedment, special conditions, references to details)

RESPONSE REQUIREMENTS:
- **CRITICAL**: Extract ONLY elements from schedules/tables
- Each element MUST have a valid ID (mark/designation) - skip rows without IDs
- Each element MUST have at least one dimension (width, length, depth, or diameter)
- Extract EVERY row from schedules/tables that has BOTH a valid ID AND dimensions
- Skip rows without proper IDs (empty, "-", just numbers, or descriptive text)
- Skip rows without dimensions or with placeholder values ("varies", "TBD", "see detail")
- Use dash - for missing/unknown values (but ID and dimensions must be present)
- Keep NOTES column brief (max 50 chars)
- Output ONLY the table, no explanatory text before or after
- Include the header row first, then all data rows

🎯 SPECIAL CASE - NO ELEMENTS FOUND:
If NO valid elements exist (no schedules/tables with proper IDs and dimensions), respond with:
NO ELEMENTS

Do NOT output empty table headers - just respond "NO ELEMENTS" to save tokens.

IMPORTANT: Your response must be ONLY the pipe-delimited table OR "NO ELEMENTS".
Do not include markdown code fences, explanations, or any other text.

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