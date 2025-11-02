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
    Version: 1.3.1
    
    Updates:
    v1.3.1:
    - Added ligature leg count extraction (4-legged, 6-legged)
    - Format: XL-bar@spacing (e.g., 4L-N12@200)
    
    v1.3.0 - CRITICAL FIXES:
    - Fixed dimension duplication bug (e.g., 600x600 incorrectly extracting length)
    - Fixed reinforcement location parsing (TOP vs BOTTOM vs T&B)
    - Removed "both ways" default assumption - extract only explicit directions
    - Added clear rules for "REFER PLAN" dimensions
    - Enhanced ligature extraction from "LEGGED" notation
    
    v1.2.0:
    - Removed PileCap and RetainingWall element types (not needed)
    - Removed LOCATION and ZONE columns (simplified output)
    
    v1.1.0:
    - Added T&B (Top & Bottom) notation handling
    - Added direction parsing (E.W vs both ways default)
    - Added ligature support for strip footings/ground beams
    
    Key features:
    - Category-based extraction (not explicit element lists)
    - Reasoning-focused instructions
    - Token-efficient schema definitions
    - Comprehensive but concise
    """
    
    name = "concrete_extraction"
    version = "1.3.1"
    description = "Extract all concrete structural elements from engineering drawings"
    
    # Core template - concise and reasoning-focused
    # Note: Version info is in docstring above, NOT in template (saves tokens)
    template = """You are analyzing engineering drawings to extract CONCRETE structural elements.

------------------------------------------
TASK: Identify ALL concrete elements and extract their complete specifications
------------------------------------------

{{ context }}

------------------------------------------
INPUT DATA:
------------------------------------------

{{ input_data }}

------------------------------------------
🎯 CRITICAL: EXTRACT ONLY FROM SCHEDULES/TABLES
------------------------------------------

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

------------------------------------------
EXTRACTION REQUIREMENTS:
------------------------------------------

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
   - TOP_REINF: Top/main reinforcement
   - BOT_REINF: Bottom/secondary reinforcement
   - SIDE_REINF: Side/transverse reinforcement (ties, stirrups, links, ligatures)
   
   ⚠️ REINFORCEMENT PARSING RULES:
   
   1. DIRECTION - Extract EXACTLY as written:
      - ⚠️ DO NOT assume "both ways" as default
      - Extract ONLY what is explicitly stated in the schedule
      - If NO direction specified → use dash - (not "both ways")
      - If "E.W" or "Each Way" stated → append "-EW" suffix
      - If "B.W" or "Both Ways" stated → append "-BW" suffix
      - Examples:
        * "N16@200" (no direction) → "N16@200" (extract as-is, no assumption)
        * "N16@200 E.W" → "N16@200-EW"
        * "N16@200 B.W" → "N16@200-BW"
   
   2. TOP vs BOTTOM - Extract from correct location:
      - ⚠️ CRITICAL: Read carefully if schedule says "TOP", "BOTTOM", or "TOP&BOTTOM"
      - "TOP" only → extract to TOP_REINF, BOT_REINF is dash -
      - "BOTTOM" only → extract to BOT_REINF, TOP_REINF is dash -
      - "TOP&BOTTOM" or "T&B" → same value in BOTH fields
      - Examples:
        * "N24-200 BOTTOM, E.W." → TOP_REINF: -, BOT_REINF: N24@200-EW
        * "N24-200 TOP, E.W." → TOP_REINF: N24@200-EW, BOT_REINF: -
        * "N16@200 T&B" → TOP_REINF: N16@200, BOT_REINF: N16@200
   
   3. T&B NOTATION (Top & Bottom):
      - "T&B" or "TOP&BOTTOM" means same reinforcement in top AND bottom
      - Split into BOTH fields with same value
      - Apply direction rules to the value
      - Examples:
        * "N16@200 T&B" → TOP_REINF: N16@200, BOT_REINF: N16@200
        * "N20@150 T&B E.W" → TOP_REINF: N20@150-EW, BOT_REINF: N20@150-EW
        * "6-N24 T&B" → TOP_REINF: 6-N24, BOT_REINF: 6-N24
   
   4. LIGATURES (for strip footings/ground beams):
      - Extract ligature/link details to SIDE_REINF field
      - ⚠️ INCLUDE the number of legs if specified (e.g., "4 LEGGED", "6 LEGGED")
      - Common terms: "LEGGED", "LIGS", "LINKS", "TIES"
      - Format: Keep leg count + bar size + spacing
      - Examples:
        * "4 LEGGED N12-200 LIGS" → SIDE_REINF: 4L-N12@200
        * "6 LEGGED N10-200" → SIDE_REINF: 6L-N10@200
        * "N10-200 LIGS" (no leg count) → SIDE_REINF: N10@200
        * "4-N12@200" → SIDE_REINF: 4L-N12@200

D. CONCRETE PROPERTIES (only if present in schedule):
   - GRADE: Strength grade as shown (e.g., N20, N25, N32, N40, N50, N65)
   - COVER: Concrete cover in mm as shown
   
   Extract EXACTLY as written - do not assume or calculate

E. ADDITIONAL DETAILS (only if explicitly shown in schedule):
   - LEVEL: Floor/level if specified
   - NOTES: Brief notes from schedule only

------------------------------------------
ELEMENT TYPES (auto-detect based on characteristics):
------------------------------------------

Foundation Elements:
- IsolatedFooting: Individual pad footings under columns
- StripFooting: Continuous footings under walls (may have ligatures in SIDE_REINF)
- CombinedFooting: Single footing supporting multiple columns
- RaftFoundation: Mat foundation over entire area
- GroundBeam: Grade beam connecting footings (may have ligatures in SIDE_REINF)

Vertical Elements:
- RectangularColumn: Column with rectangular cross-section
- CircularColumn: Column with circular cross-section
- Wall: Structural concrete wall
- ShearWall: Lateral force-resisting wall

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

------------------------------------------
DIMENSION PARSING (if in format like "1200x1500x600"):
------------------------------------------

⚠️ CRITICAL: Extract ONLY dimensions explicitly shown in the schedule

If dimensions are in combined format, split them:
- 1200x1500x600 → WIDTH: 1200, LENGTH: 1500, DEPTH: 600
- 300x400 → WIDTH: 300, DEPTH: 400 (LENGTH is dash -)
- 900Wx600D → WIDTH: 900, DEPTH: 600 (LENGTH is dash -)
- Ø600 or D600 → WIDTH: 600 (diameter), LENGTH: dash -, DEPTH: dash -

⚠️ DO NOT DUPLICATE OR ASSUME:
- If format is 900x600 (only 2 dimensions), DO NOT copy one as length
- Extract exactly what is shown: WIDTH: 900, LENGTH: -, DEPTH: 600
- If "REFER PLAN" is shown for dimension, use dash -
- Missing dimension = dash - (do not guess or duplicate)

Examples:
✓ "900Wx600D" → WIDTH: 900, LENGTH: -, DEPTH: 600
✓ "1200x1200x650" → WIDTH: 1200, LENGTH: 1200, DEPTH: 650
✗ "600x600" → WIDTH: 600, LENGTH: 600, DEPTH: 600 (WRONG - duplicating)
✓ "600x600" → WIDTH: 600, LENGTH: -, DEPTH: 600 (CORRECT)
✓ "REFER PLAN x 750D" → WIDTH: -, LENGTH: -, DEPTH: 750


------------------------------------------
CRITICAL EXTRACTION RULES:
------------------------------------------

{{ universal_rules }}

CONCRETE-SPECIFIC RULES:
1. ⚠️ Extract ONLY what is explicitly shown - NO ASSUMPTIONS
2. ⚠️ DO NOT duplicate dimensions (e.g., if 600x600, don't copy to length if not shown)
3. ⚠️ DO NOT assume "both ways" - extract direction ONLY if explicitly stated
4. ⚠️ Read carefully: "TOP" vs "BOTTOM" vs "TOP&BOTTOM" (T&B)
5. Direction markers: Add "-EW" for "E.W", "-BW" for "B.W"
6. T&B: Split same value to both TOP_REINF and BOT_REINF
7. Missing values: Use dash - (do not guess or duplicate)
8. Ligatures: Format as "XL-bar@spacing" (e.g., 4L-N12@200) - include leg count if shown
9. "REFER PLAN": Use dash - for that dimension

------------------------------------------
OUTPUT FORMAT (TABLE - ULTRA COMPACT):
------------------------------------------

Return a CSV-style table with pipe delimiters. One row per element.

HEADER ROW (always include):
ID|TYPE|PAGE|WIDTH|LENGTH|DEPTH|TOP_REINF|BOT_REINF|SIDE_REINF|GRADE|COVER|FINISH|LEVEL|TYPICAL|NOTES

DATA ROWS:
- Use pipe | as delimiter
- Use dash - for missing/not applicable values
- Dimensions in mm (numbers only)
- Reinforcement: Apply direction/T&B parsing rules
- Multiple values in same field: use semicolon (e.g., "N16@200;N12@300")
- Notes: brief, key info only

EXAMPLE:
```
ID|TYPE|PAGE|WIDTH|LENGTH|DEPTH|TOP_REINF|BOT_REINF|SIDE_REINF|GRADE|COVER|FINISH|LEVEL|TYPICAL|NOTES
GB1|GroundBeam|1|900|-|600|6-N24|6-N24|4L-N12@200|N40|-|-|Ground|-|T&B + 4 leg ligs
GB2|GroundBeam|1|825|-|500|5-N24|5-N24|4L-N12@200|N40|-|-|Ground|-|T&B + 4 leg ligs
PF1|IsolatedFooting|1|2500|2500|650|-|N24@200-EW|-|N32|-|-|Ground|-|Bottom only E.W
PF4|IsolatedFooting|1|1800|1800|650|-|N20@200-EW|-|N32|-|-|Ground|-|Bottom only E.W
SF1|StripFooting|1|600|-|600|4-N24|4-N24|4L-N12@200|N32|-|-|Ground|-|T&B + 4 leg ligs
RF1|RaftFoundation|1|-|-|750|N24@200-EW|N24@200-EW|-|N32|-|-|Ground|-|T&B E.W refer plan
C1|RectangularColumn|2|400|400|3000|8N20|-|N12@150|N32|50|F2|L1-L3|TYP|Typical column
SL1|Slab|3|-|-|200|N16@200-BW|N12@200-BW|-|N32|30|-|L1|-|Both ways explicit
```

COLUMN DEFINITIONS:
- ID: Element mark/designation (e.g., PF.1, C-12, BM-A-23)
- TYPE: Element type (IsolatedFooting, RectangularColumn, StripFooting, GroundBeam, etc.)
- PAGE: Page number where element is shown
- WIDTH: Width in mm
- LENGTH: Length in mm (or height for vertical elements)
- DEPTH: Depth/thickness in mm
- TOP_REINF: Top/main reinforcement (with direction suffix if E.W)
- BOT_REINF: Bottom/secondary reinforcement (with direction suffix if E.W)
- SIDE_REINF: Side/transverse reinforcement (ties, stirrups, links, ligatures)
  * Format for ligatures: XL-bar@spacing (e.g., 4L-N12@200 = 4-legged N12 at 200mm)
  * X = number of legs (4, 6, etc.) if specified
- GRADE: Concrete grade (N20, N25, N32, N40, N50, N65)
- COVER: Concrete cover in mm (single value or specify if varies)
- FINISH: Surface finish (F1=trowel, F2=float, F3=broom, F4=off-form, etc.)
- LEVEL: Floor/level designation (Ground, L1, L2, Roof, etc.)
- TYPICAL: Mark as TYP if typical/repeated element, or note what it's typical to
- NOTES: Critical info (embedment, special conditions, references to details)

RESPONSE REQUIREMENTS:
- **CRITICAL**: Extract ONLY elements from schedules/tables
- Each element MUST have a valid ID (mark/designation) - skip rows without IDs
- Each element MUST have at least one dimension (width, length, depth, or diameter)
- ⚠️ **DO NOT duplicate dimensions** - if 600x600, extract WIDTH: 600, LENGTH: -, DEPTH: 600
- ⚠️ **DO NOT assume "both ways"** - extract direction ONLY if explicitly stated
- ⚠️ **Read carefully**: "BOTTOM" only → BOT_REINF only (TOP_REINF is dash)
- ⚠️ **Read carefully**: "TOP" only → TOP_REINF only (BOT_REINF is dash)
- ⚠️ **T&B parsing**: Split same value to both TOP_REINF and BOT_REINF
- ⚠️ **Direction**: Add "-EW" suffix if "E.W" stated, "-BW" if "B.W" stated
- Extract EVERY row from schedules/tables that has BOTH a valid ID AND dimensions
- Skip rows without proper IDs (empty, "-", just numbers, or descriptive text)
- Skip rows without dimensions or with placeholder values ("varies", "TBD", "see detail")
- Use dash - for missing/unknown values
- "REFER PLAN" for dimension → use dash -
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
    """Example usage of the prompt - based on real extraction issues"""
    
    # Sample extracted text from the actual footing schedule
    sample_input = """
    FOOTING SCHEDULE
    ┌──────┬─────────────────────┬────────────┬──────────────────────────────────────────┐
    │ MARK │ SIZE                │ F'c (MPa)  │ COMMENTS                                 │
    ├──────┼─────────────────────┼────────────┼──────────────────────────────────────────┤
    │ GB1  │ 900Wx600D           │ 40         │ 6-N24 T&B - 4 LEGGED N12-200 LIGS       │
    │ GB2  │ 825Wx500D           │ 40         │ 5-N24 T&B - 4 LEGGED N12-200 LIGS       │
    │ PF1  │ 2500Wx2500Lx650D    │ 32         │ N24-200 BOTTOM, E.W.                     │
    │ PF2  │ 3200Wx2600Lx800D    │ 32         │ N24-150 BOTTOM, E.W.                     │
    │ PF3  │ 2700Wx2700Lx800D    │ 32         │ N24-150 BOTTOM, E.W.                     │
    │ PF4  │ 1800Wx1800Lx650D    │ 32         │ N20-200 BOTTOM, E.W.                     │
    │ RF1  │ REFER PLAN x 750D   │ 32         │ N24-200 TOP&BOTTOM, E.W.                 │
    │ RF2  │ REFER PLAN x 700D   │ 32         │ N24-200 TOP&BOTTOM, E.W.                 │
    │ RF3  │ REFER PLAN x 700D   │ 32         │ N24-200 TOP&BOTTOM, E.W.                 │
    │ SF1  │ 600Wx600D           │ 32         │ 4-N24 TOP&BOTTOM - 4 LEGGED N12-200 LIGS │
    └──────┴─────────────────────┴────────────┴──────────────────────────────────────────┘
    """
    
    # Expected correct output:
    expected_output = """
ID|TYPE|PAGE|WIDTH|LENGTH|DEPTH|TOP_REINF|BOT_REINF|SIDE_REINF|GRADE|COVER|FINISH|LEVEL|TYPICAL|NOTES
GB1|GroundBeam|1|900|-|600|6-N24|6-N24|4L-N12@200|40|-|-|-|-|T&B + 4 legged ligs
GB2|GroundBeam|1|825|-|500|5-N24|5-N24|4L-N12@200|40|-|-|-|-|T&B + 4 legged ligs
PF1|IsolatedFooting|1|2500|2500|650|-|N24@200-EW|-|32|-|-|-|-|Bottom only E.W
PF2|IsolatedFooting|1|3200|2600|800|-|N24@150-EW|-|32|-|-|-|-|Bottom only E.W
PF3|IsolatedFooting|1|2700|2700|800|-|N24@150-EW|-|32|-|-|-|-|Bottom only E.W
PF4|IsolatedFooting|1|1800|1800|650|-|N20@200-EW|-|32|-|-|-|-|Bottom only E.W
RF1|RaftFoundation|1|-|-|750|N24@200-EW|N24@200-EW|-|32|-|-|-|-|T&B E.W refer plan
RF2|RaftFoundation|1|-|-|700|N24@200-EW|N24@200-EW|-|32|-|-|-|-|T&B E.W refer plan
RF3|RaftFoundation|1|-|-|700|N24@200-EW|N24@200-EW|-|32|-|-|-|-|T&B E.W refer plan
SF1|StripFooting|1|600|-|600|4-N24|4-N24|4L-N12@200|32|-|-|-|-|T&B + 4 legged ligs
    """
    
    # Create prompt instance
    prompt = ConcreteExtractionPrompt()
    
    # Render with context
    rendered = prompt.render(
        input_data=sample_input,
        context={
            'pages': [1],
            'drawing_type': 'Footing schedule',
            'discipline': 'Concrete structural',
            'expected_elements': ['Ground beams', 'Pad footings', 'Raft foundations', 'Strip footings']
        }
    )
    
    print("GENERATED PROMPT:")
    print("=" * 80)
    print(rendered)
    print("=" * 80)
    print(f"\nPrompt token count (approx): {len(rendered) // 4}")
    print("\n" + "=" * 80)
    print("EXPECTED OUTPUT:")
    print("=" * 80)
    print(expected_output)
