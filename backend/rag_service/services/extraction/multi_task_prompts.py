"""
Multi-task prompts for unified extraction.

This module contains all the prompts used by the UnifiedExtractor for various extraction tasks.
Centralizing prompts here makes them easier to maintain, update, and optimize.
"""

from typing import List, Dict, Any
from enum import Enum


class ExtractionTask(str, Enum):
    """Types of extraction tasks that can be performed"""
    TEXT = 'text'                      # Basic text extraction
    LAYOUT = 'layout'                  # Document layout analysis
    TABLES = 'tables'                  # Table extraction
    ENTITIES = 'entities'              # Named entity extraction
    SUMMARY = 'summary'                # Document summarization
    VISUAL_ELEMENTS = 'visual_elements'  # Visual element extraction with coordinates
    DRAWING_METADATA = 'drawing_metadata'  # Engineering drawing metadata
    ALL = 'all'                        # Perform all extraction tasks


class MultiTaskPrompts:
    """
    Collection of prompts for multi-task document extraction.
    
    This class provides methods to generate task-specific prompts and
    combine them into comprehensive multi-task prompts for LLM extraction.
    """
    
    @staticmethod
    def get_text_extraction_prompt() -> str:
        """Get prompt for text extraction task"""
        return """
1. TEXT CONTENT:
   - Extract all visible text in the document
   - Preserve paragraph structure and reading order
   - Include headers, footers, and captions
   - Maintain hierarchical structure (headings, subheadings, etc.)
   - Preserve bullet points and numbered lists
   - DO NOT include text from within tables in this section (tables are extracted separately)
"""

    @staticmethod
    def get_layout_analysis_prompt() -> str:
        """Get prompt for layout analysis task"""
        return """
2. DOCUMENT LAYOUT:
   - Identify all content blocks in the document
   - For each block, specify:
     * Type: title, heading, paragraph, list, table, figure, caption, header, footer, title_block, drawing_area
     * Text content
     * Position: approximate location (top/middle/bottom, left/center/right)
     * Bounding box: {"x": left_px, "y": top_px, "width": width_px, "height": height_px}
     * Reading order: sequence number
   - Identify hierarchical relationships between blocks
   - Note any multi-column layouts
   - Distinguish between drawing area and annotation/specification areas
"""

    @staticmethod
    def get_table_extraction_prompt() -> str:
        """Get prompt for table extraction task - ENHANCED FOR TECHNICAL PRECISION"""
        return """
3. TABLES:
   - Extract all tables with their structure intact
   - For each table, include:
     * Table type: schedule, bill_of_materials, specifications, tolerance_table, general
     * Headers (column names) - preserve exact capitalization and spacing
     * All row data with EXACT values
     * Table caption/title if present
     * Position in document with bounding box coordinates
     * Any footnotes or annotations
   
   CRITICAL PRECISION REQUIREMENTS:
   - Maintain EXACT numerical values (2.50 ≠ 2.5, preserve all decimal places)
   - Preserve all units with values (25.4mm, 1.5 inches, 15kg - NEVER strip units)
   - Keep part numbers exactly as shown (ABC-123-XY, not abc123xy or ABC123XY)
   - Preserve empty cells vs zero values (they have different meanings)
   - Note which columns contain counts/quantities vs specifications
   - For schedule tables: identify the element types that need to be counted in the drawing
   - Preserve merged cells and complex cell structures
   - Handle nested headers and multi-level column groups
   
   ENGINEERING-SPECIFIC:
   - Bill of Materials (BOM): preserve item numbers, part numbers, quantities, descriptions, materials
   - Schedule tables: extract element types, specifications, required quantities
   - Tolerance tables: maintain precision of all numerical tolerances
   - Note if table contains reference quantities for validation against drawing elements
"""

    @staticmethod
    def get_entity_extraction_prompt() -> str:
        """Get prompt for entity extraction - ENHANCED FOR ENGINEERING"""
        return """
4. ENTITIES:
   - Identify key entities in the document
   - For each entity, include:
     * Type: person, organization, location, date, number, monetary value, 
              part_number, material_spec, measurement, standard_reference, 
              component_type, quantity, tolerance, drawing_number
     * Value: the actual entity text (preserve exactly as written)
     * Context: surrounding text or section
     * Page number if available
     * Location: bounding box coordinates if visual entity
   
   ENGINEERING-SPECIFIC ENTITIES:
   - part_number: Alphanumeric codes (e.g., "ABC-123-XY", "DWG-45678")
   - material_spec: Material descriptions (e.g., "316 stainless steel", "6061-T6 aluminum", "Grade 8.8 steel")
   - measurement: Dimensions with units (e.g., "25.4mm", "1.5 inches", "±0.05mm")
   - standard_reference: Industry standards (e.g., "ISO 9001", "ASTM F568", "DIN 912", "AS 1429")
   - component_type: Component descriptions (e.g., "M8 hex bolt", "6mm rivet", "bearing housing")
   - quantity: Extract as integer WITH context (e.g., {"value": 15, "context": "M8 bolts in zone A"})
   - tolerance: Tolerance specifications (e.g., "±0.05mm", "+0.1/-0.2", "H7/g6")
   - drawing_number: Drawing identification codes
   
   - Focus on domain-specific entities if apparent
   - Note relationships between entities when clear
   - Link quantities to their corresponding components
"""

    @staticmethod
    def get_summary_prompt() -> str:
        """Get prompt for document summarization"""
        return """
5. SUMMARY:
   - Provide a concise summary of the document (3-5 sentences)
   - Capture the main points and purpose of the document
   - Highlight key findings or conclusions
   - Note document type and intended audience
   - Include important dates, numbers, or statistics
   - For technical drawings: summarize what is being depicted, main components, and purpose
"""

    @staticmethod
    def get_visual_element_extraction_prompt() -> str:
        """Get prompt for visual element extraction with precise coordinate tracking - NEW"""
        return """
6. VISUAL ELEMENTS (For Drawings and Diagrams):
   - Identify ALL distinct visual elements (symbols, shapes, markers, annotations)
   - For each element instance, provide:
     * element_id: unique identifier for this specific element instance
     * type: bolt, rivet, fastener, weld_symbol, dimension_line, component, annotation, etc.
     * subtype: specific variant (e.g., "M8_hex_bolt", "6mm_rivet", "fillet_weld")
     * bounding_box: EXACT pixel coordinates {"x": left_px, "y": top_px, "width": width_px, "height": height_px}
     * center_point: {"x": center_x_px, "y": center_y_px} - use this for overlays
     * zone: spatial zone if grid present (e.g., "A-1", "B-3") or quadrant (e.g., "top-left", "center-right")
     * specifications: any visible specs (size, grade, material if labeled)
     * label: any text label or callout associated with this element
     * rotation: rotation angle if applicable (degrees)
   
   ELEMENT GROUPING:
   - Group identical/similar elements that are in close proximity
   - For each group, provide:
     * group_id: unique identifier for the group
     * element_type: type of elements in the group
     * count: EXACT number of elements in this group
     * elements: array of individual element instances with their coordinates
     * cluster_center: {"x": center_x_px, "y": center_y_px}
     * spatial_description: "cluster of 5 bolts in top-left corner"
   
   COUNTING RULES - CRITICAL:
   - Count ONLY elements visible in the drawing/diagram area
   - DO NOT count elements mentioned in tables, schedules, or text annotations
   - DO NOT count legend symbols or reference examples
   - Provide exact integer counts, NOT estimates or ranges
   - If an element is partially visible or unclear, mark as "uncertain" with note
   - Distinguish between identical elements at different locations
   
   SPATIAL RELATIONSHIPS:
   - Note element positions relative to major features
   - Identify patterns or arrays of elements (e.g., "linear array of 8 bolts along top edge")
   - Capture spatial relationships (e.g., "adjacent to", "parallel to", "concentric with")
   
   VALIDATION AGAINST SCHEDULES:
   - If schedule/BOM tables are present, list the element types they reference
   - These are the elements that MUST be counted in the drawing
   - Cross-reference: schedule says 15 M8 bolts, drawing shows X instances
"""

    @staticmethod
    def get_drawing_metadata_extraction_prompt() -> str:
        """Get prompt for engineering drawing metadata extraction - NEW"""
        return """
7. DRAWING METADATA (For Engineering/Technical Drawings):
   - Extract all title block information:
     * drawing_number: Drawing identification code
     * revision: Current revision/version (letter or number)
     * sheet_number: Sheet number if multi-sheet drawing (e.g., "1 of 3")
     * drawing_title: Main title of the drawing
     * project_name: Project or assembly name if present
     * scale: Drawing scale (e.g., "1:2", "1:50", "NTS")
     * units: Measurement units (mm, inches, etc.)
     * projection_type: First angle, third angle, isometric, etc.
     * date: Drawing date or revision date
     * drawn_by: Author/drafter name
     * checked_by: Checker/reviewer name
     * approved_by: Approver name
     * company: Company name or logo text
     * drawing_standard: Standard followed (e.g., "ISO 128", "ASME Y14.5")
   
   - Extract general notes and specifications:
     * material_specifications: Overall material callouts
     * finish_specifications: Surface finish requirements
     * tolerance_notes: General tolerance notes (e.g., "Unless otherwise specified: ±0.1mm")
     * assembly_notes: Assembly instructions or notes
     * reference_drawings: Links to related drawings
   
   - Document characteristics:
     * drawing_type: part, assembly, detail, section, schematic, electrical, mechanical
     * complexity: simple, moderate, complex (based on element count and detail)
     * purpose: manufacturing, assembly, installation, maintenance, etc.
"""

    @staticmethod
    def get_output_format_instructions() -> str:
        """Get instructions for output format - ENHANCED"""
        return """
OUTPUT FORMAT:
Provide a JSON response with the following structure:
{
    "text": "Full extracted text content (excluding table data)...",
    
    "layout": [
        {
            "type": "title",
            "text": "Document Title",
            "position": "top-center",
            "bounding_box": {"x": 100, "y": 50, "width": 400, "height": 60},
            "reading_order": 1
        }
    ],
    
    "tables": [
        {
            "table_type": "schedule",
            "caption": "FASTENER SCHEDULE",
            "headers": ["MARK", "TYPE", "SIZE", "QUANTITY", "MATERIAL"],
            "rows": [
                ["A", "HEX BOLT", "M8x20", "15", "Grade 8.8 Steel"],
                ["B", "RIVET", "6mm", "8", "Aluminum"]
            ],
            "position": "bottom-left",
            "bounding_box": {"x": 50, "y": 1200, "width": 600, "height": 300},
            "notes": "All fasteners to be zinc plated",
            "contains_reference_quantities": true,
            "element_types_to_count": ["HEX BOLT M8x20", "RIVET 6mm"]
        }
    ],
    
    "entities": [
        {
            "type": "part_number",
            "value": "ABC-123-XY",
            "context": "Main assembly drawing number",
            "bounding_box": {"x": 150, "y": 100, "width": 120, "height": 20}
        },
        {
            "type": "quantity",
            "value": 15,
            "context": "M8 hex bolts required per schedule",
            "linked_component": "M8x20 HEX BOLT"
        },
        {
            "type": "material_spec",
            "value": "Grade 8.8 Steel",
            "context": "Material specification for hex bolts"
        }
    ],
    
    "visual_elements": {
        "element_groups": [
            {
                "group_id": "group_001",
                "element_type": "HEX_BOLT_M8x20",
                "count": 15,
                "cluster_center": {"x": 450, "y": 620},
                "spatial_description": "Cluster of 15 hex bolts distributed across top frame section",
                "elements": [
                    {
                        "element_id": "bolt_001",
                        "type": "bolt",
                        "subtype": "M8_hex_bolt",
                        "center_point": {"x": 420, "y": 580},
                        "bounding_box": {"x": 415, "y": 575, "width": 10, "height": 10},
                        "zone": "top-left",
                        "specifications": "M8x20",
                        "label": "A",
                        "rotation": 0
                    },
                    {
                        "element_id": "bolt_002",
                        "type": "bolt",
                        "subtype": "M8_hex_bolt",
                        "center_point": {"x": 445, "y": 585},
                        "bounding_box": {"x": 440, "y": 580, "width": 10, "height": 10},
                        "zone": "top-left",
                        "specifications": "M8x20",
                        "label": "A",
                        "rotation": 0
                    }
                    // ... remaining 13 bolt instances with exact coordinates
                ]
            },
            {
                "group_id": "group_002",
                "element_type": "RIVET_6mm",
                "count": 8,
                "cluster_center": {"x": 380, "y": 920},
                "spatial_description": "Linear array of 8 rivets along bottom edge",
                "elements": [
                    // ... individual rivet instances with coordinates
                ]
            }
        ],
        
        "validation": {
            "schedule_reference": {
                "HEX_BOLT_M8x20": {
                    "required_quantity": 15,
                    "found_in_drawing": 15,
                    "match": true
                },
                "RIVET_6mm": {
                    "required_quantity": 8,
                    "found_in_drawing": 8,
                    "match": true
                }
            }
        }
    },
    
    "drawing_metadata": {
        "drawing_number": "DWG-12345-A",
        "revision": "C",
        "sheet_number": "1 of 1",
        "drawing_title": "Frame Assembly - Main Structure",
        "project_name": "Building XYZ Support Frame",
        "scale": "1:10",
        "units": "mm",
        "projection_type": "Third angle",
        "date": "2025-10-01",
        "drawn_by": "J. Smith",
        "checked_by": "M. Johnson",
        "approved_by": "R. Williams",
        "company": "Engineering Solutions Inc.",
        "drawing_standard": "ISO 128",
        "drawing_type": "assembly",
        "complexity": "moderate",
        "purpose": "manufacturing",
        "general_notes": [
            "All dimensions in millimeters unless otherwise specified",
            "General tolerance: ±0.1mm",
            "Surface finish: Ra 3.2 unless noted"
        ],
        "material_specifications": "Frame: 316 Stainless Steel, Fasteners: Grade 8.8 Steel",
        "reference_drawings": ["DWG-12345-B", "DWG-12300"]
    },
    
    "summary": "This assembly drawing depicts a support frame structure with fastening details..."
}

CRITICAL REQUIREMENTS:
- Include only the sections that were requested in the analysis
- Ensure all JSON is valid and properly formatted
- All numerical coordinates must be integers (pixel values)
- All counts must be exact integers, never estimates or ranges
- Preserve units with all measurements
- Maintain exact capitalization and formatting for part numbers
- Bounding boxes must use image pixel coordinates (0,0 = top-left of image)
- For visual elements, EVERY instance must have precise center_point coordinates for overlay visualization
"""

    @classmethod
    def build_unified_prompt(cls, tasks: List[ExtractionTask]) -> str:
        """
        Build a unified prompt that extracts all requested information.
        
        Args:
            tasks: List of extraction tasks to perform
            
        Returns:
            Comprehensive prompt for the vision model
        """
        # Base prompt
        prompt = """Analyze this document image and extract the following information.

IMPORTANT COORDINATE SYSTEM:
- All coordinates are in pixels relative to the image
- Origin (0,0) is at the top-left corner of the image
- X increases from left to right
- Y increases from top to bottom
- Provide exact integer pixel values for all coordinates

"""
        
        # Add task-specific instructions
        task_instructions = []
        
        # If ALL is specified, include all tasks
        if ExtractionTask.ALL in tasks:
            tasks = [t for t in ExtractionTask if t != ExtractionTask.ALL]
        
        # Text extraction (always included unless explicitly excluded)
        if ExtractionTask.TEXT in tasks or ExtractionTask.ALL in tasks:
            task_instructions.append(cls.get_text_extraction_prompt())
        
        # Layout analysis
        if ExtractionTask.LAYOUT in tasks:
            task_instructions.append(cls.get_layout_analysis_prompt())
        
        # Table extraction
        if ExtractionTask.TABLES in tasks:
            task_instructions.append(cls.get_table_extraction_prompt())
        
        # Entity extraction
        if ExtractionTask.ENTITIES in tasks:
            task_instructions.append(cls.get_entity_extraction_prompt())
        
        # Visual element extraction (NEW)
        if ExtractionTask.VISUAL_ELEMENTS in tasks:
            task_instructions.append(cls.get_visual_element_extraction_prompt())
        
        # Drawing metadata extraction (NEW)
        if ExtractionTask.DRAWING_METADATA in tasks:
            task_instructions.append(cls.get_drawing_metadata_extraction_prompt())
        
        # Document summarization
        if ExtractionTask.SUMMARY in tasks:
            task_instructions.append(cls.get_summary_prompt())
        
        # Add all task instructions
        prompt += "\n".join(task_instructions)
        
        # Add output format instructions
        prompt += "\n" + cls.get_output_format_instructions()
        
        return prompt


# Task-specific prompts for specialized use cases
class SpecializedPrompts:
    """Collection of specialized prompts for specific document types or domains"""
    
    @staticmethod
    def get_engineering_drawing_prompt() -> str:
        """Get comprehensive prompt specialized for engineering/technical drawings - NEW"""
        return """
Analyze this engineering drawing with comprehensive extraction.

DRAWING METADATA:
- Drawing number, revision, sheet number
- Title block information (title, project, scale, units, dates, personnel)
- Drawing standard and projection type
- General notes and specifications

ELEMENTS & COUNTS:
- Identify ALL distinct visual elements (bolts, rivets, fasteners, components, symbols)
- For EACH element instance, provide EXACT pixel coordinates (center point and bounding box)
- Count ONLY elements visible in the drawing area (NOT in tables or legends)
- Provide exact integer counts for each element type
- Note element specifications (size, grade, material) from labels or callouts
- Group similar elements by proximity and type

SPATIAL INFORMATION:
- For EVERY element, provide precise pixel coordinates
- Center point: {"x": px, "y": px} for overlay visualization
- Bounding box: {"x": left_px, "y": top_px, "width": width_px, "height": height_px}
- Zone/quadrant: spatial description or grid reference
- Spatial relationships between element groups

TABLES & SCHEDULES:
- Extract ALL tables (BOM, schedules, specifications, tolerances)
- Maintain EXACT numerical precision (2.50 ≠ 2.5)
- Preserve units with ALL values (never strip units)
- Keep part numbers exactly as written
- For schedule tables: identify which elements need to be counted in the drawing
- Link schedule quantities to actual element counts for validation

DIMENSIONS & ANNOTATIONS:
- Extract critical dimensions with tolerances
- Geometric dimensioning and tolerancing (GD&T) symbols
- Surface finish callouts
- Notes and annotations with their locations

VALIDATION:
- Cross-reference schedule/BOM quantities with actual element counts
- Flag discrepancies between specified and counted quantities
- Note any unclear or ambiguous elements

OUTPUT CRITICAL DATA:
- Element counts MUST be exact integers (not "several" or "multiple")
- Specifications MUST include units
- Coordinates MUST be exact pixels for overlay capability
- Part numbers preserved exactly
- Link elements to specifications in tables
"""
    
    @staticmethod
    def get_financial_document_prompt() -> str:
        """Get prompt specialized for financial documents"""
        return """
Analyze this financial document with special attention to:
- Financial tables with numerical data (maintain exact precision)
- Currency values and percentages
- Date ranges and fiscal periods
- Financial metrics and KPIs
- Footnotes and disclaimers

Extract all tables with exact numerical precision and maintain decimal places.
Identify financial entities such as company names, ticker symbols, and monetary values.
Note any trends, comparisons, or year-over-year changes mentioned.
Preserve currency symbols and units with all values.
"""
    
    @staticmethod
    def get_scientific_document_prompt() -> str:
        """Get prompt specialized for scientific papers"""
        return """
Analyze this scientific document with special attention to:
- Abstract and conclusions
- Methodology sections
- Results and data tables
- Figures and their captions
- Citations and references
- Technical terminology and definitions

Extract tables with precise numerical values and units.
Identify scientific entities such as chemical compounds, species names, or technical terms.
Preserve mathematical formulas and equations.
Note key findings and experimental results.
Maintain exact notation for scientific measurements and uncertainties.
"""
    
    @staticmethod
    def get_legal_document_prompt() -> str:
        """Get prompt specialized for legal documents"""
        return """
Analyze this legal document with special attention to:
- Parties involved and their roles
- Dates, deadlines, and time periods
- Defined terms (often in quotes or bold)
- Numbered sections and clauses
- Signatures and attestations
- Legal citations and references

Extract any tables containing terms, conditions, or schedules.
Identify legal entities such as people, organizations, jurisdictions, and legal concepts.
Note any conditions, obligations, rights, or remedies specified.
Preserve the hierarchical structure of sections and subsections.
Maintain exact wording for defined terms and key clauses.
"""


# Utility functions for prompt customization
class PromptUtils:
    """Utility functions for working with extraction prompts"""
    
    @staticmethod
    def get_tasks_for_document_type(doc_type: str) -> List[ExtractionTask]:
        """
        Get recommended extraction tasks for a given document type.
        
        Args:
            doc_type: Type of document (engineering_drawing, financial, scientific, legal, general)
            
        Returns:
            List of recommended extraction tasks
        """
        task_mappings = {
            'engineering_drawing': [
                ExtractionTask.DRAWING_METADATA,
                ExtractionTask.VISUAL_ELEMENTS,
                ExtractionTask.TABLES,
                ExtractionTask.ENTITIES,
                ExtractionTask.LAYOUT,
                ExtractionTask.TEXT,
                ExtractionTask.SUMMARY
            ],
            'financial': [
                ExtractionTask.TEXT,
                ExtractionTask.TABLES,
                ExtractionTask.ENTITIES,
                ExtractionTask.LAYOUT,
                ExtractionTask.SUMMARY
            ],
            'scientific': [
                ExtractionTask.TEXT,
                ExtractionTask.LAYOUT,
                ExtractionTask.TABLES,
                ExtractionTask.ENTITIES,
                ExtractionTask.SUMMARY
            ],
            'legal': [
                ExtractionTask.TEXT,
                ExtractionTask.LAYOUT,
                ExtractionTask.ENTITIES,
                ExtractionTask.SUMMARY
            ],
            'general': [
                ExtractionTask.TEXT,
                ExtractionTask.LAYOUT,
                ExtractionTask.SUMMARY
            ]
        }
        
        return task_mappings.get(doc_type, task_mappings['general'])
    
    @staticmethod
    def add_custom_instructions(base_prompt: str, custom_instructions: str) -> str:
        """
        Add custom instructions to a base prompt.
        
        Args:
            base_prompt: The base extraction prompt
            custom_instructions: Additional instructions to append
            
        Returns:
            Enhanced prompt with custom instructions
        """
        return f"{base_prompt}\n\nADDITIONAL INSTRUCTIONS:\n{custom_instructions}"
    
    @staticmethod
    def build_prompt_with_image_dimensions(base_prompt: str, width: int, height: int) -> str:
        """
        Add image dimension context to help with coordinate extraction.
        
        Args:
            base_prompt: The base extraction prompt
            width: Image width in pixels
            height: Image height in pixels
            
        Returns:
            Enhanced prompt with image dimension context
        """
        dimension_context = f"""
IMAGE DIMENSIONS:
- Width: {width} pixels
- Height: {height} pixels
- All coordinates must be within these bounds
- Ensure center_point and bounding_box coordinates are accurate relative to these dimensions
"""
        return dimension_context + base_prompt