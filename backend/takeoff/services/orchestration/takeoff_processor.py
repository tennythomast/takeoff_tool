# takeoff/services/takeoff_processor.py (SIMPLIFIED)

import logging
from typing import Dict
from takeoff.services.validation.schema_validator import SchemaValidator
from takeoff.models import TakeoffElement

logger = logging.getLogger(__name__)


class TakeoffProcessor:
    """Single-phase extraction processor"""
    
    def __init__(self, modelhub):
        self.modelhub = modelhub
    
    async def process_drawing_page(self, drawing_page) -> Dict:
        """
        Single-phase: Extract all elements at once
        Much simpler than two-phase!
        """
        
        results = {
            'page_number': drawing_page.page_number,
            'extracted_count': 0,
            'failed_count': 0,
            'total_cost': 0.0,
            'elements': []
        }
        
        try:
            # Generate combined prompt
            prompt = TakeoffExtractionPrompts.generate_combined_extraction_prompt(
                drawing_page.raw_extraction
            )
            
            # Single LLM call for entire page
            logger.info(f"Extracting all elements from page {drawing_page.page_number}")
            
            response = await self.modelhub.complete(
                prompt=prompt,
                response_format={"type": "json_object"},
                task_type="extraction",
                max_tokens=4000,  # Larger for multiple elements
                temperature=0.1
            )
            
            # Parse response
            extracted_elements = response.get('parsed_json', [])
            
            # Handle if wrapped in object
            if isinstance(extracted_elements, dict):
                extracted_elements = extracted_elements.get('elements', [])
            
            results['total_cost'] = response.get('cost', 0)
            
            # Process each extracted element
            for element_data in extracted_elements:
                try:
                    # Validate against schema
                    is_valid, errors = SchemaValidator.validate_extraction_output(
                        element_type=element_data['element_type'],
                        extracted_specs=element_data.get('specifications', {})
                    )
                    
                    if not is_valid:
                        logger.warning(
                            f"Schema validation errors for {element_data['element_id']}: {errors}"
                        )
                        
                        # Sanitize
                        element_data['specifications'] = SchemaValidator.sanitize_output(
                            element_type=element_data['element_type'],
                            extracted_specs=element_data.get('specifications', {})
                        )
                    
                    # Calculate completeness
                    completeness = SchemaValidator.get_completeness_score(
                        element_type=element_data['element_type'],
                        extracted_specs=element_data.get('specifications', {})
                    )
                    
                    element_data['completeness_score'] = completeness
                    
                    # Quality check
                    confidence = element_data.get('confidence_score', 0)
                    
                    if confidence >= 0.7 and completeness >= 0.3:
                        # Store element
                        element = await self._store_element(
                            drawing_page.drawing,
                            drawing_page,
                            element_data,
                            response.get('model_used', 'unknown')
                        )
                        
                        results['extracted_count'] += 1
                        results['elements'].append({
                            'element_id': element.element_id,
                            'element_type': element.element_type,
                            'confidence': confidence,
                            'completeness': completeness,
                            'status': 'extracted'
                        })
                    else:
                        logger.warning(
                            f"Low quality: {element_data['element_id']} "
                            f"(confidence={confidence:.2f}, completeness={completeness:.2f})"
                        )
                        results['failed_count'] += 1
                        results['elements'].append({
                            'element_id': element_data['element_id'],
                            'element_type': element_data['element_type'],
                            'reason': 'Low quality',
                            'status': 'failed'
                        })
                
                except Exception as e:
                    logger.error(f"Failed to process element: {e}")
                    results['failed_count'] += 1
            
            logger.info(
                f"Page {drawing_page.page_number} complete: "
                f"{results['extracted_count']} elements extracted, "
                f"cost=${results['total_cost']:.4f}"
            )
            
            return results
        
        except Exception as e:
            logger.error(f"Page extraction failed: {e}")
            raise
    
    async def _store_element(
        self,
        drawing,
        drawing_page,
        element_data: Dict,
        model_used: str
    ) -> TakeoffElement:
        """Store extracted element"""
        
        element = TakeoffElement.objects.create(
            drawing=drawing,
            page=drawing_page,
            element_id=element_data['element_id'],
            element_type=element_data['element_type'],
            specifications=element_data['specifications'],
            confidence_score=element_data.get('confidence_score', 0),
            completeness_score=element_data.get('completeness_score', 0),
            extraction_notes=element_data.get('extraction_notes', {}),
            llm_model_used=model_used,
            verified=False
        )
        
        return element