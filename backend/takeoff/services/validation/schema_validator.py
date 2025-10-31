# takeoff/services/schema_validator.py

from typing import Tuple, List
import logging
from takeoff.schemas import ELEMENT_SCHEMAS

logger = logging.getLogger(__name__)

class SchemaValidator:
    """Validates LLM output against defined schemas"""
    
    @staticmethod
    def validate_extraction_output(
        element_type: str,
        extracted_specs: dict
    ) -> Tuple[bool, List[str]]:
        """
        Verify extracted data conforms to schema
        
        Returns:
            (is_valid, list_of_errors)
        """
        
        schema = ELEMENT_SCHEMAS.get(element_type)
        if not schema:
            return False, [f"Unknown element type: {element_type}"]
        
        errors = []
        
        # Validate all schema groups are present (or null)
        for group_name in schema.keys():
            if group_name not in extracted_specs:
                # Missing group is acceptable if data doesn't exist
                logger.debug(f"Missing group {group_name} in extraction")
                continue
            
            # Validate group structure
            group_errors = SchemaValidator._validate_group(
                group_name,
                schema[group_name],
                extracted_specs[group_name]
            )
            errors.extend(group_errors)
        
        # Check for unexpected extra fields
        extra_groups = set(extracted_specs.keys()) - set(schema.keys())
        if extra_groups:
            errors.append(f"Unexpected groups in output: {extra_groups}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def _validate_group(
        group_name: str,
        schema_def,
        extracted_data
    ) -> List[str]:
        """Validate a single group matches schema"""
        
        errors = []
        
        # Null data is acceptable (missing information)
        if extracted_data is None:
            return errors
        
        if isinstance(schema_def, list):
            # Schema: ['field1', 'field2', ...]
            # Expected: {"field1": value, "field2": value, ...}
            
            if not isinstance(extracted_data, dict):
                errors.append(
                    f"{group_name} should be object, got {type(extracted_data).__name__}"
                )
                return errors
            
            # Check for extra fields not in schema
            extra_fields = set(extracted_data.keys()) - set(schema_def)
            if extra_fields:
                errors.append(f"{group_name} has unexpected fields: {extra_fields}")
        
        elif isinstance(schema_def, dict):
            # Schema: {'section1': [...], 'section2': [...]}
            # Expected: {"section1": {...}, "section2": {...}}
            
            if not isinstance(extracted_data, dict):
                errors.append(
                    f"{group_name} should be object, got {type(extracted_data).__name__}"
                )
                return errors
            
            # Validate each section
            for section_name, section_schema in schema_def.items():
                if section_name not in extracted_data:
                    # Missing section is OK (data might not exist)
                    continue
                
                section_data = extracted_data[section_name]
                
                if section_data is None:
                    # Explicitly null = OK
                    continue
                
                # Validate section structure
                if isinstance(section_schema, list):
                    if not isinstance(section_data, dict):
                        errors.append(
                            f"{group_name}.{section_name} should be object, "
                            f"got {type(section_data).__name__}"
                        )
                        continue
                    
                    extra_fields = set(section_data.keys()) - set(section_schema)
                    if extra_fields:
                        errors.append(
                            f"{group_name}.{section_name} has unexpected fields: "
                            f"{extra_fields}"
                        )
                
                elif isinstance(section_schema, dict):
                    # Nested dict (like cover_mm with bottom/top/sides)
                    if not isinstance(section_data, dict):
                        errors.append(
                            f"{group_name}.{section_name} should be object, "
                            f"got {type(section_data).__name__}"
                        )
                        continue
                    
                    extra_fields = set(section_data.keys()) - set(section_schema.keys())
                    if extra_fields:
                        errors.append(
                            f"{group_name}.{section_name} has unexpected fields: "
                            f"{extra_fields}"
                        )
        
        return errors
    
    @staticmethod
    def sanitize_output(
        element_type: str,
        extracted_specs: dict
    ) -> dict:
        """
        Remove fields not in schema (defensive cleanup)
        Keeps only schema-defined fields
        """
        
        schema = ELEMENT_SCHEMAS.get(element_type, {})
        sanitized = {}
        
        for group_name in schema.keys():
            if group_name not in extracted_specs:
                sanitized[group_name] = None
                continue
            
            group_data = extracted_specs[group_name]
            sanitized[group_name] = SchemaValidator._sanitize_group(
                schema[group_name],
                group_data
            )
        
        return sanitized
    
    @staticmethod
    def _sanitize_group(schema_def, extracted_data):
        """Remove extra fields from a group"""
        
        if extracted_data is None:
            return None
        
        if isinstance(schema_def, list):
            # Keep only schema-defined fields
            if not isinstance(extracted_data, dict):
                return None
            
            return {
                field: extracted_data.get(field)
                for field in schema_def
                if field in extracted_data
            }
        
        elif isinstance(schema_def, dict):
            # Sanitize each section
            if not isinstance(extracted_data, dict):
                return None
            
            sanitized = {}
            for section_name, section_schema in schema_def.items():
                if section_name not in extracted_data:
                    sanitized[section_name] = None
                    continue
                
                section_data = extracted_data[section_name]
                
                if section_data is None:
                    sanitized[section_name] = None
                elif isinstance(section_schema, list):
                    if isinstance(section_data, dict):
                        sanitized[section_name] = {
                            field: section_data.get(field)
                            for field in section_schema
                            if field in section_data
                        }
                    else:
                        sanitized[section_name] = None
                elif isinstance(section_schema, dict):
                    if isinstance(section_data, dict):
                        sanitized[section_name] = {
                            field: section_data.get(field)
                            for field in section_schema.keys()
                            if field in section_data
                        }
                    else:
                        sanitized[section_name] = None
                else:
                    sanitized[section_name] = section_data
            
            return sanitized
        
        return extracted_data
    
    @staticmethod
    def get_completeness_score(
        element_type: str,
        extracted_specs: dict
    ) -> float:
        """
        Calculate completeness: percentage of schema fields filled
        
        Returns: 0.0 - 1.0
        """
        
        schema = ELEMENT_SCHEMAS.get(element_type, {})
        if not schema:
            return 0.0
        
        total_fields = 0
        filled_fields = 0
        
        def count_fields(schema_part, data_part):
            nonlocal total_fields, filled_fields
            
            if isinstance(schema_part, list):
                for field in schema_part:
                    total_fields += 1
                    if data_part and isinstance(data_part, dict):
                        if field in data_part and data_part[field] is not None:
                            filled_fields += 1
            
            elif isinstance(schema_part, dict):
                for section_name, section_schema in schema_part.items():
                    section_data = data_part.get(section_name) if data_part else None
                    count_fields(section_schema, section_data)
        
        for group_name, group_schema in schema.items():
            group_data = extracted_specs.get(group_name)
            count_fields(group_schema, group_data)
        
        return filled_fields / total_fields if total_fields > 0 else 0.0