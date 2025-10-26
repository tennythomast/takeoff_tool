# takeoff/prompts/components/rules.py

"""
Universal extraction rules that apply to ALL trades
These ensure consistent, accurate extraction across different types of drawings
"""

# ============================================================================
# UNIVERSAL EXTRACTION RULES
# ============================================================================

UNIVERSAL_EXTRACTION_RULES = """
1. ACCURACY FIRST:
   - Extract ONLY explicitly visible data
   - Use null for missing/unclear fields
   - DO NOT calculate, infer, or assume values
   - Copy text exactly as shown (preserve formatting, units, notations)

2. PRECISION MATTERS:
   - Preserve ALL decimal places (2.50 ≠ 2.5)
   - Keep units with values (25mm, not 25)
   - Maintain exact spelling of grades/specs (N32, not n32)
   - Preserve alphanumeric IDs exactly (F-01, not F01 or f-01)

3. HANDLE UNCERTAINTY:
   - If ambiguous → note in assumptions_made, lower confidence
   - If illegible/cut-off → set field to null, note in extraction_notes
   - If conflicting data → use most specific source, document conflict
   - If "typical" or "similar" → extract once, note applies_to_typical

4. CONFIDENCE SCORING:
   - 1.0 = Perfect visibility, no ambiguity, all fields present
   - 0.9 = Minor issue (1-2 missing optional fields)
   - 0.8 = Some ambiguity or 3-4 missing fields
   - 0.7 = Significant gaps but core data present
   - <0.7 = Too uncertain, DO NOT INCLUDE

5. DOCUMENTATION:
   Always populate extraction_notes:
   - source_references: WHERE you found this data
   - missing_fields: Which schema fields are null
   - assumptions_made: Any interpretations you made
   - validation_warnings: Unusual values or issues
"""

# For future expansion - other trades can add their specific rules
TRADE_SPECIFIC_RULES = {
    'concrete': """
    - Extract all reinforcement layers (don't miss top bars, ties)
    - Typical bar spacing: 100-300mm
    - Common grades: N25, N32, N40
    - Set volume_m3 to null (calculated later)
    """,
    
    'steel': """
    - Note connection types (welded, bolted)
    - Extract bolt grades if specified
    - Include member orientation
    - Note if galvanized/painted
    """,
    
    # Add more as trades are implemented
}


def get_universal_rules() -> str:
    """Get universal extraction rules"""
    return UNIVERSAL_EXTRACTION_RULES


def get_trade_rules(trade: str) -> str:
    """Get trade-specific rules"""
    return TRADE_SPECIFIC_RULES.get(trade, "")


def get_combined_rules(trade: str = None) -> str:
    """Get universal + trade-specific rules"""
    rules = UNIVERSAL_EXTRACTION_RULES
    if trade and trade in TRADE_SPECIFIC_RULES:
        rules += f"\n\nTRADE-SPECIFIC RULES ({trade.upper()}):\n"
        rules += TRADE_SPECIFIC_RULES[trade]
    return rules