# takeoff/schemas/concrete_schemas.py

"""
Comprehensive element schemas for concrete construction takeoff
Organized by structural category with industry-standard fields
"""

# ============================================================================
# FOUNDATION ELEMENTS
# ============================================================================

ELEMENT_SCHEMAS = {
    
    # FOOTINGS
    'IsolatedFooting': {
        'dimensions': [
            'width_mm',           # Footing width
            'length_mm',          # Footing length
            'depth_mm',           # Footing thickness
            'pedestal_width_mm',  # Pedestal dimension (if present)
            'pedestal_height_mm'
        ],
        'reinforcement': { # Will have a multiple reinforcement for bottom and top
            'bottom': [
                'bar_size',       # e.g., "N16", "N20"
                'spacing_mm',     # e.g., 200
                'direction',      # "longitudinal", "transverse", "both"
                'quantity',       # number of bars
                'length_m'        # per bar
            ],
            'top': [
                'bar_size',
                'spacing_mm',
                'quantity',
                'length_m'
            ]
        },
        'concrete': {
            'grade': str,         # e.g., "N25", "N32", "N40"
            'cover_mm': {
                'bottom': int,    # not needed typically 75mm for footings 
                'top': int,
                'sides': int
            },
            'volume_m3': float    # calculated volume
        },
        'excavation': {
            'depth_mm': int,      # dig depth
            'volume_m3': float    # excavation volume will be calculated consider excluding from schema
        }
    },
    
    'StripFooting': {
        'dimensions': [
            'width_mm',           # Footing width
            'depth_mm',           # Footing thickness
            'length_m',           # Total length (may be calculated)
        ],
        'reinforcement': {
            'longitudinal': [
                'bar_size',
                'quantity',       # number of bars
                'continuous',     # boolean
                'lap_length_mm'   # if spliced
            ],
            'transverse': [
                'bar_size',
                'spacing_mm',
                'length_m'        # per bar
            ]
        },
        'concrete': {
            'grade': str,
            'cover_mm': {
                'bottom': int,
                'sides': int
            },
            'volume_m3': float
        }
    },
    
    'CombinedFooting': {
        'dimensions': [
            'width_mm',
            'length_mm',
            'depth_mm',
            'shape'               # "rectangular", "trapezoidal", "strap"
        ],
        'reinforcement': {
            'bottom_longitudinal': ['bar_size', 'spacing_mm', 'quantity', 'length_m'],
            'bottom_transverse': ['bar_size', 'spacing_mm', 'quantity', 'length_m'],
            'top': ['bar_size', 'spacing_mm', 'quantity', 'length_m']
        },
        'concrete': {
            'grade': str,
            'cover_mm': {'bottom': int, 'top': int, 'sides': int},
            'volume_m3': float
        }
    },
    
    'PileCap': {
        'dimensions': [
            'width_mm',
            'length_mm',
            'depth_mm',
            'pile_diameter_mm',
            'pile_count',
            'pile_spacing_mm'
        ],
        'reinforcement': {
            'bottom_main': ['bar_size', 'spacing_mm', 'quantity'],
            'bottom_distribution': ['bar_size', 'spacing_mm', 'quantity'],
            'top': ['bar_size', 'spacing_mm', 'quantity'],
            'stirrups': ['bar_size', 'spacing_mm', 'legs']
        },
        'concrete': {
            'grade': str,
            'cover_mm': {'bottom': int, 'top': int, 'sides': int},
            'volume_m3': float
        },
        'piles': {
            'type': str,          # "bored", "driven", "CFA"
            'diameter_mm': int,
            'length_m': float,
            'quantity': int
        }
    },
    
    'RaftFoundation': {
        'dimensions': [
            'length_m',
            'width_m',
            'thickness_mm',
            'area_m2'
        ],
        'reinforcement': {
            'bottom_layer_x': ['bar_size', 'spacing_mm', 'length_m'],
            'bottom_layer_y': ['bar_size', 'spacing_mm', 'length_m'],
            'top_layer_x': ['bar_size', 'spacing_mm', 'length_m'],
            'top_layer_y': ['bar_size', 'spacing_mm', 'length_m']
        },
        'concrete': {
            'grade': str,
            'cover_mm': {'bottom': int, 'top': int},
            'volume_m3': float
        },
        'additional': {
            'edge_beams': bool,
            'drop_panels': bool
        }
    },

    # ============================================================================
    # VERTICAL ELEMENTS
    # ============================================================================
    
    'RectangularColumn': {
        'dimensions': [
            'width_mm',           # Cross-section width
            'depth_mm',           # Cross-section depth
            'height_mm',          # Column height
            'quantity'            # Number of identical columns
        ],
        'reinforcement': {
            'vertical': [
                'bar_size',       # e.g., "N20", "N24"
                'quantity',       # e.g., 8 (for corner + intermediate)
                'length_m',       # per bar
                'lap_length_mm'   # if spliced
            ],
            'ties': [
                'bar_size',       # e.g., "N10", "N12"
                'spacing_mm',     # e.g., 200
                'type',           # "rectangular", "cross"
                'legs'            # number of legs (e.g., 4)
            ]
        },
        'concrete': {
            'grade': str,
            'cover_mm': int,      # typically 40-50mm for columns
            'volume_m3': float
        }
    },
    
    'CircularColumn': {
        'dimensions': [
            'diameter_mm',
            'height_mm',
            'quantity'
        ],
        'reinforcement': {
            'vertical': [
                'bar_size',
                'quantity',       # e.g., 12 bars around perimeter
                'length_m',
                'lap_length_mm'
            ],
            'spiral': [          # or 'ties' for circular ties
                'bar_size',
                'pitch_mm',       # vertical spacing
                'type'            # "spiral", "circular_ties"
            ]
        },
        'concrete': {
            'grade': str,
            'cover_mm': int,
            'volume_m3': float
        }
    },
    
    'Wall': {
        'dimensions': [
            'length_m',
            'height_m',
            'thickness_mm',
            'area_m2'
        ],
        'reinforcement': {
            'vertical_internal': ['bar_size', 'spacing_mm', 'length_m'],
            'vertical_external': ['bar_size', 'spacing_mm', 'length_m'],
            'horizontal_internal': ['bar_size', 'spacing_mm', 'length_m'],
            'horizontal_external': ['bar_size', 'spacing_mm', 'length_m']
        },
        'concrete': {
            'grade': str,
            'cover_mm': {'internal': int, 'external': int},
            'volume_m3': float
        },
        'openings': [          # Array of openings
            {
                'type': str,    # "door", "window"
                'width_mm': int,
                'height_mm': int,
                'quantity': int
            }
        ]
    },
    
    'ShearWall': {
        'dimensions': [
            'length_m',
            'height_m',
            'thickness_mm'
        ],
        'reinforcement': {
            'vertical_curtain': ['bar_size', 'spacing_mm', 'layers'],  # 2 layers
            'horizontal_curtain': ['bar_size', 'spacing_mm', 'layers'],
            'boundary_elements': {
                'vertical': ['bar_size', 'quantity', 'length_m'],
                'ties': ['bar_size', 'spacing_mm', 'type']
            }
        },
        'concrete': {
            'grade': str,
            'cover_mm': int,
            'volume_m3': float
        }
    },
    
    'RetainingWall': {
        'dimensions': [
            'length_m',
            'height_m',
            'base_width_mm',
            'top_width_mm',      # if tapered
            'toe_width_mm',
            'heel_width_mm',
            'base_thickness_mm'
        ],
        'reinforcement': {
            'stem_vertical_internal': ['bar_size', 'spacing_mm'],
            'stem_vertical_external': ['bar_size', 'spacing_mm'],
            'stem_horizontal': ['bar_size', 'spacing_mm'],
            'base_longitudinal': ['bar_size', 'spacing_mm'],
            'base_transverse': ['bar_size', 'spacing_mm']
        },
        'concrete': {
            'grade': str,
            'cover_mm': {'stem': int, 'base': int},
            'volume_m3': float
        },
        'drainage': {
            'weep_holes': bool,
            'weep_hole_spacing_mm': int,
            'drainage_layer': str
        }
    },

    # ============================================================================
    # HORIZONTAL ELEMENTS
    # ============================================================================
    
    'RectangularBeam': {
        'dimensions': [
            'width_mm',
            'depth_mm',
            'length_m',
            'quantity'            # Number of identical beams
        ],
        'reinforcement': {
            'top': [
                'bar_size',
                'quantity',       # number of bars
                'length_m',
                'location'        # "support", "midspan", "continuous"
            ],
            'bottom': [
                'bar_size',
                'quantity',
                'length_m',
                'location'
            ],
            'stirrups': [
                'bar_size',
                'spacing_mm',     # can vary: "100/200" means 100mm at ends, 200mm at center
                'type',           # "closed", "open"
                'legs'            # 2-leg, 4-leg
            ],
            'hanger_bars': [     # if present
                'bar_size',
                'quantity'
            ]
        },
        'concrete': {
            'grade': str,
            'cover_mm': {'bottom': int, 'sides': int, 'top': int},
            'volume_m3': float
        }
    },
    
    'TBeam': {
        'dimensions': [
            'flange_width_mm',
            'flange_thickness_mm',
            'web_width_mm',
            'total_depth_mm',
            'length_m'
        ],
        'reinforcement': {
            'top_flange': ['bar_size', 'spacing_mm', 'quantity'],
            'top_web': ['bar_size', 'quantity'],
            'bottom': ['bar_size', 'quantity'],
            'stirrups': ['bar_size', 'spacing_mm', 'type']
        },
        'concrete': {
            'grade': str,
            'cover_mm': int,
            'volume_m3': float
        }
    },
    
    'LintelsBeam': {
        'dimensions': [
            'width_mm',
            'depth_mm',
            'length_mm',          # span over opening
            'quantity'
        ],
        'reinforcement': {
            'main_bottom': ['bar_size', 'quantity'],
            'main_top': ['bar_size', 'quantity'],
            'stirrups': ['bar_size', 'spacing_mm']
        },
        'concrete': {
            'grade': str,
            'cover_mm': int,
            'volume_m3': float
        }
    },
    
    # ============================================================================
    # SLAB ELEMENTS
    # ============================================================================
    
    'SolidSlab': {
        'dimensions': [
            'thickness_mm',
            'area_m2',
            'length_m',           # if rectangular
            'width_m'
        ],
        'reinforcement': {
            'bottom_main': [
                'bar_size',
                'spacing_mm',
                'direction',      # "longitudinal", "x-direction"
                'length_m'
            ],
            'bottom_distribution': [
                'bar_size',
                'spacing_mm',
                'direction',      # "transverse", "y-direction"
                'length_m'
            ],
            'top_main': [
                'bar_size',
                'spacing_mm',
                'direction',
                'length_m',
                'location'        # "over supports", "continuous"
            ],
            'top_distribution': [
                'bar_size',
                'spacing_mm',
                'direction',
                'length_m'
            ]
        },
        'concrete': {
            'grade': str,
            'cover_mm': {'bottom': int, 'top': int},
            'volume_m3': float,
            'finish': str         # "troweled", "exposed", "screed"
        },
        'mesh': {                # Alternative to individual bars
            'type': str,          # e.g., "SL72", "SL92"
            'area_m2': float
        }
    },
    
    'RibbedSlab': {
        'dimensions': [
            'rib_width_mm',
            'rib_depth_mm',
            'rib_spacing_mm',
            'topping_thickness_mm',
            'area_m2'
        ],
        'reinforcement': {
            'rib_bottom': ['bar_size', 'quantity_per_rib'],
            'rib_top': ['bar_size', 'quantity_per_rib', 'location'],
            'stirrups': ['bar_size', 'spacing_mm'],
            'topping_mesh': ['type', 'area_m2']
        },
        'concrete': {
            'grade': str,
            'cover_mm': int,
            'volume_m3': float
        },
        'void_formers': {
            'type': str,          # "permanent", "removable", "EPS"
            'size_mm': int
        }
    },
    
    'WaffleSlab': {
        'dimensions': [
            'rib_width_mm',
            'rib_depth_mm',
            'rib_spacing_mm',
            'topping_thickness_mm',
            'area_m2',
            'drop_panel_size_mm'  # if present
        ],
        'reinforcement': {
            'ribs_x_direction': ['bar_size', 'quantity_per_rib'],
            'ribs_y_direction': ['bar_size', 'quantity_per_rib'],
            'topping': ['bar_size', 'spacing_mm', 'direction'],
            'drop_panel': ['bar_size', 'spacing_mm']  # if present
        },
        'concrete': {
            'grade': str,
            'cover_mm': int,
            'volume_m3': float
        }
    },
    
    'FlatSlab': {
        'dimensions': [
            'thickness_mm',
            'area_m2',
            'column_strip_width_mm',
            'middle_strip_width_mm'
        ],
        'reinforcement': {
            'column_strip_bottom': ['bar_size', 'spacing_mm'],
            'column_strip_top': ['bar_size', 'spacing_mm'],
            'middle_strip_bottom': ['bar_size', 'spacing_mm'],
            'middle_strip_top': ['bar_size', 'spacing_mm']
        },
        'concrete': {
            'grade': str,
            'cover_mm': {'bottom': int, 'top': int},
            'volume_m3': float
        },
        'drop_panels': {       # if present
            'dimensions': ['width_mm', 'length_mm', 'thickness_mm'],
            'quantity': int
        }
    },
    
    'HollowCoreSlab': {
        'dimensions': [
            'width_mm',           # typically 1200mm
            'depth_mm',           # 150, 200, 250, 300mm
            'length_m',
            'quantity',           # number of slabs
            'area_m2'
        ],
        'reinforcement': {
            'prestressed_strands': [
                'diameter_mm',    # e.g., 12.7mm
                'quantity',       # per slab
                'type'            # "7-wire strand"
            ],
            'topping_mesh': [    # if structural topping
                'type',
                'area_m2'
            ]
        },
        'concrete': {
            'grade': str,
            'cover_mm': int,
            'volume_m3': float
        },
        'topping': {
            'required': bool,
            'thickness_mm': int,
            'grade': str
        }
    },

    # ============================================================================
    # STAIRCASE & SPECIAL ELEMENTS
    # ============================================================================
    
    'Staircase': {
        'dimensions': [
            'flight_width_mm',
            'flight_length_mm',
            'waist_thickness_mm',
            'tread_mm',           # horizontal step dimension
            'riser_mm',           # vertical step dimension
            'number_of_steps',
            'number_of_flights'
        ],
        'reinforcement': {
            'waist_main': ['bar_size', 'spacing_mm'],
            'waist_distribution': ['bar_size', 'spacing_mm'],
            'landing_main': ['bar_size', 'spacing_mm'],
            'landing_distribution': ['bar_size', 'spacing_mm']
        },
        'concrete': {
            'grade': str,
            'cover_mm': int,
            'volume_m3': float
        },
        'landings': [
            {
                'type': str,      # "top", "bottom", "intermediate"
                'length_mm': int,
                'width_mm': int,
                'thickness_mm': int
            }
        ]
    },
    
    'Ramp': {
        'dimensions': [
            'width_mm',
            'length_mm',
            'slope',              # e.g., "1:12", "8.3%"
            'thickness_mm'
        ],
        'reinforcement': {
            'longitudinal': ['bar_size', 'spacing_mm'],
            'transverse': ['bar_size', 'spacing_mm']
        },
        'concrete': {
            'grade': str,
            'cover_mm': int,
            'volume_m3': float,
            'finish': str         # "broom", "exposed aggregate"
        }
    },
    
    'WaterTank': {
        'dimensions': [
            'type',               # "rectangular", "circular"
            'length_mm',          # if rectangular
            'width_mm',           # if rectangular
            'diameter_mm',        # if circular
            'height_mm',
            'wall_thickness_mm',
            'base_thickness_mm',
            'capacity_liters'
        ],
        'reinforcement': {
            'base': ['bar_size', 'spacing_mm', 'layers'],
            'walls_vertical': ['bar_size', 'spacing_mm', 'layers'],
            'walls_horizontal': ['bar_size', 'spacing_mm', 'layers'],
            'roof': ['bar_size', 'spacing_mm']  # if covered
        },
        'concrete': {
            'grade': str,
            'cover_mm': {'internal': int, 'external': int},
            'volume_m3': float,
            'waterproofing': str  # "integral", "applied"
        }
    },
    
    'PitChamber': {
        'dimensions': [
            'length_mm',
            'width_mm',
            'depth_mm',
            'wall_thickness_mm',
            'base_thickness_mm'
        ],
        'reinforcement': {
            'base': ['bar_size', 'spacing_mm'],
            'walls': ['bar_size', 'spacing_mm', 'layers']
        },
        'concrete': {
            'grade': str,
            'cover_mm': int,
            'volume_m3': float
        }
    },
    
    # ============================================================================
    # PRECAST ELEMENTS
    # ============================================================================
    
    'PrecastBeam': {
        'dimensions': [
            'width_mm',
            'depth_mm',
            'length_m',
            'quantity'
        ],
        'reinforcement': {
            'prestressed': [
                'strand_diameter_mm',
                'quantity',
                'type'            # "7-wire", "single"
            ],
            'mild_steel': [
                'bar_size',
                'location',       # "top", "shear"
                'quantity'
            ]
        },
        'concrete': {
            'grade': str,
            'cover_mm': int,
            'volume_m3': float
        },
        'connections': {
            'type': str,          # "welded", "bolted", "grouted"
            'quantity': int
        }
    },
    
    'PrecastColumn': {
        'dimensions': [
            'width_mm',
            'depth_mm',
            'height_mm',
            'quantity'
        ],
        'reinforcement': {
            'vertical': ['bar_size', 'quantity', 'projection_mm'],
            'ties': ['bar_size', 'spacing_mm']
        },
        'concrete': {
            'grade': str,
            'cover_mm': int,
            'volume_m3': float
        },
        'connections': {
            'base_type': str,     # "pocket", "grouted", "baseplate"
            'top_type': str
        }
    },

    # ============================================================================
    # MISCELLANEOUS
    # ============================================================================
    
    'Curb': {
        'dimensions': [
            'height_mm',
            'width_mm',
            'length_m'
        ],
        'reinforcement': {
            'main': ['bar_size', 'spacing_mm'],
            'distribution': ['bar_size', 'spacing_mm']
        },
        'concrete': {
            'grade': str,
            'cover_mm': int,
            'volume_m3': float
        }
    },
    
    'Gutter': {
        'dimensions': [
            'width_mm',
            'depth_mm',
            'length_m',
            'thickness_mm'
        ],
        'reinforcement': {
            'mesh': ['type', 'length_m']
        },
        'concrete': {
            'grade': str,
            'cover_mm': int,
            'volume_m3': float
        }
    },
    
    'Pavement': {
        'dimensions': [
            'thickness_mm',
            'area_m2',
            'length_m',
            'width_m'
        ],
        'reinforcement': {
            'mesh': ['type', 'area_m2'],  # if reinforced
            'joints': ['type', 'spacing_m']  # "expansion", "contraction"
        },
        'concrete': {
            'grade': str,
            'cover_mm': int,
            'volume_m3': float,
            'finish': str         # "broom", "troweled"
        },
        'base': {
            'type': str,          # "crushed rock", "compacted fill"
            'thickness_mm': int
        }
    }
}