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
from takeoff.prompts.components.output_format import get_output_format

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
            max_tokens=8000  # Allow for more detailed extraction with more elements
        )
        
        # Add metadata for additional context
        request_context.metadata = {
            "complexity_score": 0.8,  # Engineering drawings are complex
            "expected_output_tokens": 6000,  # Increased for larger extraction responses
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
            List of validated extraction items
        """
        response_text = llm_response.get('text', '')
        
        # Extract JSON from response
        try:
            # Find JSON array in the response
            json_start = response_text.find('[')
            
            if json_start == -1:
                logger.warning("No JSON array found in LLM response")
                return []
            
            # Try to parse the JSON array
            try:
                # First try to parse the whole array
                json_str = response_text[json_start:]
                extraction_results = json.loads(json_str)
                logger.info(f"Successfully parsed complete JSON array with {len(extraction_results)} elements")
            except json.JSONDecodeError:
                # If that fails, try to parse individual elements
                logger.warning("Complete JSON array parsing failed, trying to parse individual elements")
                
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
            
            # Create element objects
            await self._create_element_objects(extraction, extraction_results)
            
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
    
    @sync_to_async
    def _create_element_objects(
        self,
        extraction: TakeoffExtraction,
        results: List[Dict[str, Any]]
    ) -> None:
        """Create TakeoffElement objects from extraction results"""
        with transaction.atomic():
            for item in results:
                element_id = item.get('element_id')
                element_type = item.get('element_type')
                
                if not element_id or not element_type:
                    continue
                
                # Create or update element
                TakeoffElement.objects.update_or_create(
                    drawing=extraction.drawing,
                    element_id=element_id,
                    defaults={
                        'extraction': extraction,
                        'element_type': element_type,
                        'specifications': item.get('specifications', {}),
                        'confidence_score': item.get('confidence_score', 0.0)
                    }
                )


# Convenience function to get the extraction service
def get_llm_extraction_service() -> LLMExtractionService:
    """Get LLM extraction service instance"""
    return LLMExtractionService()