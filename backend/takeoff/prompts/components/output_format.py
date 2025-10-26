# takeoff/prompts/components/output_format.py

def get_output_format() -> str:
    """Standard output format for all trades"""
    return """
Return JSON array with this structure:

[
  {
    "element_id": "F-01",
    "element_type": "IsolatedFooting",
    "trade": "concrete",
    "page_number": 2,
    "confidence_score": 0.95,
    
    "specifications": {
      "dimensions": {
        "width_mm": 1200,
        "length_mm": 1500,
        "depth_mm": 600
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
      }
    },
    
    "extraction_notes": {
      "source_references": [
        "Page 2, Footing Schedule, Row 1"
      ],
      "missing_fields": [
        "reinforcement.bottom.quantity",
        "reinforcement.bottom.length_m",
        "concrete.volume_m3"
      ],
      "assumptions_made": [
        "Assumed 'B.W' means both_ways direction"
      ],
      "validation_warnings": [],
      "requires_cross_page_validation": false
    }
  }
]

CRITICAL RULES:
- Only include elements with confidence >= 0.7
- Return empty array [] if no elements found
- Use null for missing fields (not empty string or 0)
- Always include extraction_notes with at least source_references
"""