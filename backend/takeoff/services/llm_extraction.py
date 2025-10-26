"""
LLM Extraction Service

This module provides functionality to extract structured data from engineering drawings
using LLM models via the modelhub. It handles:
1. Preparing prompts with appropriate rules and context
2. Calling the LLM via modelhub
3. Processing and validating the extraction results
4. Storing the results in the database
"""

import json
import logging
import time
import os
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime

from django.db import transaction
from django.utils import timezone
from asgiref.sync import sync_to_async

from modelhub.services.llm_router import EnhancedLLMRouter
from modelhub.services.routing.types import RequestContext, EntityType, OptimizationStrategy

from takeoff.models import Drawing, TakeoffExtraction, TakeoffElement
from takeoff.prompts.trades.concrete import ConcreteExtractionPrompt
from takeoff.prompts.components.rules import get_combined_rules

logger = logging.getLogger(__name__)


class LLMExtractionService:
    """
    Service for extracting structured data from engineering drawings using LLMs
    """
    
    def __init__(self):
        self.llm_router = EnhancedLLMRouter()
        self.extraction_prompts = {
            'concrete': ConcreteExtractionPrompt()
        }
    
    async def extract_elements(
        self,
        drawing_id: str,
        trade: str = 'concrete',
        pages: List[int] = None,
        model_name: str = None,
        user_id: str = None,
        extraction_method: str = 'ai_assisted'
    ) -> Dict[str, Any]:
        """
        Extract elements from a drawing using LLM
        
        Args:
            drawing_id: ID of the drawing to extract from
            trade: Trade type (concrete, steel, etc.)
            pages: List of page numbers to extract from (None for all)
            model_name: Specific model to use (None for auto-selection)
            user_id: ID of the user initiating the extraction
            extraction_method: Method used for extraction
            
        Returns:
            Dictionary with extraction results and metadata
        """
        start_time = time.time()
        
        # Get the drawing
        drawing = await self._get_drawing(drawing_id)
        if not drawing:
            return {
                'success': False,
                'error': f"Drawing with ID {drawing_id} not found",
                'extraction_id': None
            }
        
        # Get text content from drawing
        drawing_text = await self._get_drawing_text(drawing, pages)
        
        # Process the document in chunks if it's too large
        max_chunk_size = 120000  # Approximately 30,000 tokens per chunk (Claude-3.5-Sonnet can handle 200k tokens)
        
        if len(drawing_text) > max_chunk_size:
            logger.info(f"Drawing text is large ({len(drawing_text)} chars), processing in chunks")
            
            # Split the text into pages
            page_texts = drawing_text.split("--- Page ")
            
            # Remove empty first element if it exists
            if page_texts and not page_texts[0].strip():
                page_texts = page_texts[1:]
            
            # Add the page prefix back
            page_texts = [f"--- Page {text}" for text in page_texts]
            
            # Group pages into chunks that fit within max_chunk_size
            chunks = []
            current_chunk = ""
            
            for page_text in page_texts:
                if len(current_chunk) + len(page_text) > max_chunk_size:
                    # Current chunk is full, start a new one
                    chunks.append(current_chunk)
                    current_chunk = page_text
                else:
                    # Add page to current chunk
                    current_chunk += "\n\n" + page_text if current_chunk else page_text
            
            # Add the last chunk if it's not empty
            if current_chunk:
                chunks.append(current_chunk)
            
            logger.info(f"Split document into {len(chunks)} chunks for processing")
            
            # Process each chunk and combine results
            all_results = []
            
            for i, chunk in enumerate(chunks):
                logger.info(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
                
                # Process this chunk
                chunk_results = await self._process_text_chunk(chunk, drawing, trade, model_name, user_id, extraction_method)
                
                if chunk_results.get('success'):
                    # Get the extraction ID from the first successful chunk
                    extraction_id = chunk_results.get('extraction_id')
                    
                    # Add elements from this chunk
                    if 'elements' in chunk_results:
                        all_results.extend(chunk_results['elements'])
                else:
                    # If any chunk fails, return the error
                    return chunk_results
            
            # Return combined results
            return {
                'success': True,
                'extraction_id': extraction_id,
                'element_count': len(all_results),
                'elements': all_results,
                'processing_time_ms': int((time.time() - start_time) * 1000)
            }
        if not drawing_text:
            return {
                'success': False,
                'error': "No text content found in drawing",
                'extraction_id': None
            }
        
        # For smaller documents, process directly
        return await self._process_text_chunk(
            chunk_text=drawing_text,
            drawing=drawing,
            trade=trade,
            model_name=model_name,
            user_id=user_id,
            extraction_method=extraction_method
        )
    
    def _generate_extraction_prompt(
        self,
        trade: str,
        input_text: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Generate extraction prompt for the specified trade
        
        Args:
            trade: Trade type (concrete, steel, etc.)
            input_text: Text content from drawing
            context: Additional context for extraction
            
        Returns:
            Formatted prompt string
        """
        if trade not in self.extraction_prompts:
            raise ValueError(f"Unsupported trade: {trade}")
        
        # Get trade-specific prompt
        prompt_template = self.extraction_prompts[trade]
        
        # Get combined rules (universal + trade-specific)
        rules = get_combined_rules(trade)
        
        # Render prompt with input text, context, and rules
        return prompt_template.render(
            input_data=input_text,
            context=context,
            universal_rules=rules
        )
    
    async def _call_llm(
        self,
        prompt: str,
        model_name: str = None,
        trade: str = 'concrete'
    ) -> Dict[str, Any]:
        """
        Call LLM via modelhub
        
        Args:
            prompt: Formatted prompt string
            model_name: Specific model to use (None for auto-selection)
            trade: Trade type for context
            
        Returns:
            LLM response with extracted data
        """
        # Prepare request context for the LLM router
        request_context = RequestContext(
            entity_type=EntityType.WORKSPACE_CHAT.value,
            entity_id=f"takeoff_{trade}_extraction",
            user_id="system",  # System-initiated extraction
            # Note: quality_critical=True is used instead of optimization_strategy
            quality_critical=True,  # Use high-quality models for extraction
            max_tokens=30000  # Balanced limit to ensure all elements can be extracted
        )
        
        # Add metadata for additional context
        request_context.metadata = {
            "complexity_score": 0.8,  # Engineering drawings are complex
            "expected_output_tokens": 12000,  # Increased to accommodate all elements
            "model_name": model_name,  # Specific model if provided
            "temperature": 0.1,  # Low temperature for deterministic extraction
            "timeout_seconds": 180  # Allow up to 3 minutes for extraction
        }
        
        # Call the LLM via the router
        response, metadata = await self.llm_router.execute_with_cost_optimization(
            organization=None,  # No specific organization
            model_type="TEXT",
            request_context=request_context,
            prompt=prompt,
            messages=None  # Using prompt format, not messages
        )
        
        # Extract the response text and metadata
        return {
            'text': response.content if hasattr(response, 'content') else '',
            'model_used': metadata.get('selected_model', ''),
            'provider_used': metadata.get('provider', ''),
            'cost_usd': float(metadata.get('total_cost', 0.0)),
            'processing_time_ms': metadata.get('performance', {}).get('total_time_ms', 0)
        }
    
    def _process_extraction_results(self, llm_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process and validate extraction results from LLM
        
        Args:
            llm_response: Raw LLM response
            
        Returns:
            List of extracted elements
        """
        # Handle empty or invalid responses
        if not llm_response or not isinstance(llm_response, dict):
            logger.warning("Empty or invalid LLM response")
            return []
            
        response_text = llm_response.get('text', '')
        if not response_text:
            logger.warning("Empty text in LLM response")
            return []
        
        # Log the raw response for debugging
        logger.info(f"Raw LLM response length: {len(response_text)} characters")
        logger.info(f"First 500 characters: {response_text[:500]}")
        logger.info(f"Last 500 characters: {response_text[-500:]}")
        
        # Save raw response to file for analysis
        try:
            import os
            from datetime import datetime
            output_dir = "/app/backend/takeoff/tests/output"
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_file = os.path.join(output_dir, f"raw_llm_response_{timestamp}.txt")
            with open(raw_file, 'w') as f:
                f.write(response_text)
            logger.info(f"Saved raw LLM response to: {raw_file}")
        except Exception as e:
            logger.warning(f"Failed to save raw response: {e}")
        
        # Extract data from response
        try:
            # Remove markdown code fences if present
            # LLMs often wrap content in ```json ... ``` or ``` ... ```
            if response_text.strip().startswith('```'):
                # Find the first newline after the opening fence
                first_newline = response_text.find('\n')
                if first_newline != -1:
                    response_text = response_text[first_newline + 1:]
                
                # Remove the closing fence
                if response_text.strip().endswith('```'):
                    response_text = response_text[:response_text.rfind('```')]
                
                logger.info("Removed markdown code fences from response")
            
            # Check if response is in table format (pipe-delimited)
            if '|' in response_text and 'ID|TYPE' in response_text:
                logger.info("Detected table format response, parsing...")
                extraction_results = self._parse_table_to_json(response_text)
                logger.info(f"Successfully parsed table with {len(extraction_results)} elements")
                return extraction_results
            
            # Otherwise, try JSON format
            # Find JSON array in the response
            json_start = response_text.find('[')
            
            if json_start == -1:
                logger.warning("No JSON array or table found in LLM response")
                logger.warning(f"Response text preview: {response_text[:1000]}")
                return []
            
            # Try to parse the JSON array
            try:
                # First try to parse the whole array
                json_str = response_text[json_start:]
                extraction_results = json.loads(json_str)
                logger.info(f"Successfully parsed complete JSON array with {len(extraction_results)} elements")
            except json.JSONDecodeError as e:
                # If that fails, try to parse individual elements
                logger.warning(f"Complete JSON array parsing failed: {str(e)}")
                logger.warning(f"JSON parse error at position {e.pos}: {e.msg}")
                logger.warning(f"JSON string around error (chars {max(0, e.pos-100)}:{e.pos+100}): {json_str[max(0, e.pos-100):e.pos+100]}")
                logger.warning("Trying to parse individual elements")
                
                # Extract complete elements one by one
                elements = []
                element_start = json_start + 1  # Skip the opening [
                depth = 0
                in_element = False
                element_json = ""
                
                for i, char in enumerate(response_text[element_start:]):
                    if char == '{' and not in_element:
                        in_element = True
                        depth = 1
                        element_json = '{'
                    elif in_element:
                        element_json += char
                        if char == '{':
                            depth += 1
                        elif char == '}':
                            depth -= 1
                            if depth == 0:
                                # End of element
                                try:
                                    element = json.loads(element_json)
                                    elements.append(element)
                                    logger.info(f"Successfully parsed element {len(elements)}")
                                    in_element = False
                                    element_json = ""
                                except json.JSONDecodeError as e:
                                    logger.warning(f"Failed to parse element: {e}")
                                    in_element = False
                                    element_json = ""
                
                extraction_results = elements
                logger.info(f"Parsed {len(extraction_results)} individual elements from partial JSON")
                
                if not extraction_results:
                    logger.warning("Failed to parse any elements from the response")
                    return []
            
            # Validate results
            if not isinstance(extraction_results, list):
                logger.warning("Extraction results is not a list")
                return []
            
            # Filter out items with confidence < 0.7
            valid_results = [
                item for item in extraction_results 
                if isinstance(item, dict) and item.get('confidence_score', 0) >= 0.7
            ]
            
            # Log filtering results
            filtered_count = len(extraction_results) - len(valid_results)
            if filtered_count > 0:
                logger.info(f"Filtered out {filtered_count} elements with confidence < 0.7")
            
            logger.info(f"Final extraction result count: {len(valid_results)} elements")
            
            return valid_results
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM response: {e}")
            return []
        except Exception as e:
            logger.error(f"Error processing extraction results: {e}")
            return []
    
    @sync_to_async
    def _get_drawing(self, drawing_id: str) -> Optional[Drawing]:
        """Get drawing by ID"""
        try:
            return Drawing.objects.get(id=drawing_id)
        except Drawing.DoesNotExist:
            logger.error(f"Drawing with ID {drawing_id} not found")
            return None
    
    @sync_to_async
    def _get_drawing_text(self, drawing: Drawing, pages: List[int] = None) -> str:
        """Get text content from drawing's RAG document"""
        if not drawing.rag_document:
            logger.warning(f"Drawing {drawing.id} has no associated RAG document")
            return ""
        
        # Get all pages from the document
        document_pages = drawing.rag_document.pages.all()
        
        # Filter by page numbers if specified
        if pages:
            document_pages = document_pages.filter(page_number__in=pages)
        
        # Combine text from all pages
        text_parts = []
        for page in document_pages:
            text_parts.append(f"--- Page {page.page_number} ---\n{page.page_text}")
        
        return "\n\n".join(text_parts)
    
    @sync_to_async
    def _create_extraction_record(
        self,
        drawing: Drawing,
        trade: str,
        user_id: str = None,
        extraction_method: str = 'ai_assisted'
    ) -> TakeoffExtraction:
        """Create extraction record in database"""
        return TakeoffExtraction.objects.create(
            drawing=drawing,
            created_by_id=user_id,
            extraction_method=extraction_method,
            status='processing',
            elements={'trade': trade, 'items': []}
        )
    
    @sync_to_async
    def _update_extraction_record(
        self,
        extraction: TakeoffExtraction,
        results: List[Dict[str, Any]],
        processing_time_ms: int,
        cost_usd: float
    ) -> None:
        """Update extraction record with results"""
        with transaction.atomic():
            # Update extraction record
            extraction.status = 'completed'
            extraction.processing_time_ms = processing_time_ms
            extraction.extraction_cost_usd = Decimal(str(cost_usd))
            extraction.elements = {
                'trade': extraction.elements.get('trade', 'concrete'),
                'items': results
            }
            extraction.element_count = len(results)
            
            # Calculate average confidence score
            if results:
                confidence_scores = [item.get('confidence_score', 0) for item in results]
                extraction.confidence_score = sum(confidence_scores) / len(confidence_scores)
            
            extraction.save()
    
    @sync_to_async
    def _update_extraction_with_error(
        self,
        extraction: TakeoffExtraction,
        error: str,
        processing_time_ms: int
    ) -> None:
        """Update extraction record with error"""
        extraction.status = 'failed'
        extraction.processing_error = error
        extraction.processing_time_ms = processing_time_ms
        extraction.save()
    
    async def _process_text_chunk(
        self,
        chunk_text: str,
        drawing: Drawing,
        trade: str,
        model_name: str = None,
        user_id: str = None,
        extraction_method: str = 'ai_assisted'
    ) -> Dict[str, Any]:
        """
        Process a single chunk of text from the drawing
        
        Args:
            chunk_text: Text content for this chunk
            drawing: Drawing object
            trade: Trade type
            model_name: Model name to use
            user_id: User ID
            extraction_method: Extraction method
            
        Returns:
            Dictionary with extraction results
        """
        start_time = time.time()
        
        # Create extraction record
        extraction = await self._create_extraction_record(
            drawing=drawing,
            trade=trade,
            user_id=user_id,
            extraction_method=extraction_method
        )
        
        try:
            # Prepare extraction context
            context = {
                'drawing_type': drawing.metadata.get('drawing_type', 'Unknown'),
                'discipline': drawing.metadata.get('discipline', trade.capitalize()),
                'expected_elements': drawing.metadata.get('expected_elements', [])
            }
            
            # Generate prompt
            prompt = self._generate_extraction_prompt(trade, chunk_text, context)
            
            # Call LLM via modelhub
            llm_response = await self._call_llm(prompt, model_name, trade)
            
            # Log the raw LLM response
            response_text = llm_response.get('text', '')
            logger.info(f"Raw LLM response length: {len(response_text)} chars")
            
            # Save the raw response to a file for inspection
            import os
            from datetime import datetime
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests', 'output')
            os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            response_file = os.path.join(output_dir, f'raw_llm_response_{timestamp}.txt')
            
            with open(response_file, 'w') as f:
                f.write(response_text)
            
            logger.info(f"Raw LLM response saved to: {response_file}")
            
            # Process extraction results
            extraction_results = self._process_extraction_results(llm_response)
            
            # Update extraction record with results
            await self._update_extraction_record(
                extraction=extraction,
                results=extraction_results,
                processing_time_ms=int((time.time() - start_time) * 1000),
                cost_usd=llm_response.get('cost_usd', 0)
            )
            
            # Normalize compact format (add defaults for omitted fields)
            normalized_results = [self._normalize_compact_format(elem) for elem in extraction_results]
            
            # Create element objects
            await self._create_element_objects(extraction, normalized_results)
            
            return {
                'success': True,
                'extraction_id': str(extraction.id),
                'element_count': len(extraction_results),
                'elements': extraction_results,
                'processing_time_ms': int((time.time() - start_time) * 1000)
            }
            
        except Exception as e:
            logger.error(f"Error processing chunk: {str(e)}", exc_info=True)
            
            # Update extraction record with error
            await self._update_extraction_with_error(
                extraction=extraction,
                error=str(e),
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
            
            return {
                'success': False,
                'error': str(e),
                'extraction_id': str(extraction.id)
            }
    
    def _parse_table_to_json(self, table_text: str) -> List[Dict]:
        """
        Parse pipe-delimited table format to JSON.
        
        Expected format:
        ID|TYPE|PAGE|WIDTH|LENGTH|DEPTH|TOP_REINF|BOT_REINF|GRADE|COVER|NOTES
        PF.1|IsolatedFooting|1|900|900|600|SL92|-|N32|40|Pad footing
        """
        lines = table_text.strip().split('\n')
        if len(lines) < 2:
            logger.warning("Table has no data rows")
            return []
        
        # Parse header
        header = [col.strip() for col in lines[0].split('|')]
        logger.info(f"Table header: {header}")
        
        # Parse data rows
        results = []
        for i, line in enumerate(lines[1:], start=1):
            if not line.strip():
                continue
                
            values = [val.strip() for val in line.split('|')]
            if len(values) != len(header):
                logger.warning(f"Row {i} has {len(values)} columns, expected {len(header)}: {line}")
                continue
            
            # Create element dict
            row_dict = dict(zip(header, values))
            
            # Convert to standard JSON format
            element = {
                "element_id": row_dict.get('ID', ''),
                "element_type": row_dict.get('TYPE', ''),
                "page_number": int(row_dict.get('PAGE', 1)) if row_dict.get('PAGE', '').isdigit() else 1,
                "confidence_score": 1.0,  # Table format doesn't include confidence
                "specifications": {
                    "dimensions": {},
                    "reinforcement": {},
                    "concrete": {},
                    "quantity": {},
                    "location": {},
                    "finish": {}
                },
                "extraction_notes": {
                    "source_references": [f"Page {row_dict.get('PAGE', 1)}"],
                    "missing_fields": [],
                    "assumptions_made": [],
                    "validation_warnings": [],
                    "typical": row_dict.get('TYPICAL', '-') if row_dict.get('TYPICAL') != '-' else None
                }
            }
            
            # Parse dimensions
            if row_dict.get('WIDTH') and row_dict['WIDTH'] != '-':
                element['specifications']['dimensions']['width_mm'] = int(row_dict['WIDTH'])
            if row_dict.get('LENGTH') and row_dict['LENGTH'] != '-':
                element['specifications']['dimensions']['length_mm'] = int(row_dict['LENGTH'])
            if row_dict.get('DEPTH') and row_dict['DEPTH'] != '-':
                element['specifications']['dimensions']['depth_mm'] = int(row_dict['DEPTH'])
            
            # Parse quantity
            if row_dict.get('QTY') and row_dict['QTY'] != '-':
                qty_str = row_dict['QTY']
                # Check if it's a length (e.g., "15m")
                if 'm' in qty_str.lower():
                    element['specifications']['quantity']['length'] = qty_str
                    element['specifications']['quantity']['unit'] = 'linear_meters'
                elif qty_str.isdigit():
                    element['specifications']['quantity']['count'] = int(qty_str)
                    element['specifications']['quantity']['unit'] = 'number'
                else:
                    element['specifications']['quantity']['value'] = qty_str
            
            # Parse reinforcement
            if row_dict.get('TOP_REINF') and row_dict['TOP_REINF'] != '-':
                element['specifications']['reinforcement']['top'] = self._parse_reinforcement(row_dict['TOP_REINF'])
            if row_dict.get('BOT_REINF') and row_dict['BOT_REINF'] != '-':
                element['specifications']['reinforcement']['bottom'] = self._parse_reinforcement(row_dict['BOT_REINF'])
            if row_dict.get('SIDE_REINF') and row_dict['SIDE_REINF'] != '-':
                element['specifications']['reinforcement']['side'] = self._parse_reinforcement(row_dict['SIDE_REINF'])
            
            # Parse concrete
            if row_dict.get('GRADE') and row_dict['GRADE'] != '-':
                element['specifications']['concrete']['grade'] = row_dict['GRADE']
            if row_dict.get('COVER') and row_dict['COVER'] != '-':
                cover_str = row_dict['COVER']
                if cover_str.isdigit():
                    element['specifications']['concrete']['cover_mm'] = int(cover_str)
                else:
                    # Handle complex cover specifications
                    element['specifications']['concrete']['cover_description'] = cover_str
            
            # Parse finish
            if row_dict.get('FINISH') and row_dict['FINISH'] != '-':
                element['specifications']['finish']['type'] = row_dict['FINISH']
            
            # Parse location details
            if row_dict.get('LOCATION') and row_dict['LOCATION'] != '-':
                element['specifications']['location']['description'] = row_dict['LOCATION']
            if row_dict.get('ZONE') and row_dict['ZONE'] != '-':
                element['specifications']['location']['zone'] = row_dict['ZONE']
            if row_dict.get('LEVEL') and row_dict['LEVEL'] != '-':
                element['specifications']['location']['level'] = row_dict['LEVEL']
            
            # Add notes
            if row_dict.get('NOTES') and row_dict['NOTES'] != '-':
                element['extraction_notes']['description'] = row_dict['NOTES']
            
            results.append(element)
            logger.info(f"Parsed element {i}: {element['element_id']}")
        
        return results
    
    def _parse_reinforcement(self, reinf_str: str) -> Dict:
        """Parse reinforcement string like 'N16@200' or 'SL92'"""
        if '@' in reinf_str:
            # Format: bar_size@spacing
            parts = reinf_str.split('@')
            return {
                'bar_size': parts[0],
                'spacing_mm': int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None,
                'direction': 'both_ways'
            }
        else:
            # Format: fabric type
            return {
                'fabric_type': reinf_str,
                'direction': 'both_ways'
            }
    
    def _normalize_compact_format(self, element: Dict) -> Dict:
        """
        Normalize compact format where null fields are omitted.
        Ensures all required fields exist with proper defaults.
        """
        # Ensure top-level fields exist
        element.setdefault('page_number', 1)
        element.setdefault('confidence_score', 0.0)
        element.setdefault('specifications', {})
        element.setdefault('extraction_notes', {})
        
        # Normalize specifications
        specs = element['specifications']
        specs.setdefault('dimensions', {})
        specs.setdefault('reinforcement', {})
        specs.setdefault('concrete', {})
        
        # Normalize extraction_notes
        notes = element['extraction_notes']
        notes.setdefault('source_references', [])
        notes.setdefault('missing_fields', [])
        notes.setdefault('assumptions_made', [])
        notes.setdefault('validation_warnings', [])
        
        return element
    
    @sync_to_async
    def _create_element_objects(
        self,
        extraction: TakeoffExtraction,
        results: List[Dict]
    ) -> None:
        """Create TakeoffElement objects from extraction results"""
        with transaction.atomic():
            # Delete any existing elements for this extraction
            TakeoffElement.objects.filter(extraction=extraction).delete()
            
            # Create new elements
            for result in results:
                element_id = result.get('element_id', '')
                element_type = result.get('element_type', '')
                
                if not element_id or not element_type:
                    logger.warning(f"Skipping element without ID or type: {result}")
                    continue
                
                # Create element object
                TakeoffElement.objects.create(
                    extraction=extraction,
                    drawing=extraction.drawing,
                    element_id=element_id,
                    element_type=element_type,
                    page_number=result.get('page_number', 1),
                    confidence_score=result.get('confidence_score', 0.0),
                    specifications=result.get('specifications', {}),
                    extraction_notes=result.get('extraction_notes', {})
                )
