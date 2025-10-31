"""
LLM Extraction Service with Chunked Output

This module provides functionality to extract structured data from engineering drawings
using LLM models with chunked output to avoid token limits. Key features:
1. Full context is provided to the LLM (all pages)
2. Output is requested in chunks to avoid output token limits
3. Automatic continuation requests when more elements remain
4. Results are merged from multiple chunks

Strategy:
- Send full document context to LLM
- Request output in batches (e.g., "extract first 20 elements")
- Detect when more elements remain
- Request continuation with context of already extracted elements
- Merge all chunks into final result
"""

import json
import logging
import time
import os
import re
from decimal import Decimal
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from django.db import transaction
from django.utils import timezone
from asgiref.sync import sync_to_async

from modelhub.services.llm_router import EnhancedLLMRouter
from modelhub.services.routing.types import RequestContext, EntityType

from takeoff.models import Drawing, TakeoffExtraction, TakeoffElement
from takeoff.prompts.trades.concrete_prompts import ConcreteExtractionPrompt
from takeoff.prompts.components.rules import get_combined_rules
from rag_service.models import Document

logger = logging.getLogger(__name__)


class ChunkedLLMExtractionService:
    """
    Service for extracting structured data from engineering drawings using LLMs
    with chunked output to avoid token limits
    """
    
    # Configuration
    CHUNK_BY_PAGE = True  # Extract one page at a time
    MAX_CHUNKS = 50  # Maximum number of chunks (pages) to prevent infinite loops
    MAX_OUTPUT_TOKENS = 8000  # Conservative limit per chunk
    
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
        Extract elements from a drawing using LLM with chunked output
        
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
        
        # Create extraction record
        extraction = await self._create_extraction_record(
            drawing=drawing,
            extraction_method=extraction_method,
            user_id=user_id
        )
        
        try:
            # Get document pages
            document_pages = await self._get_document_pages(drawing)
            
            if not document_pages:
                logger.warning("No pages found in document")
                return {
                    'success': False,
                    'error': 'No pages found in document',
                    'extraction_id': str(extraction.id)
                }
            
            # Filter pages if specified
            if pages:
                document_pages = [p for p in document_pages if p['page_number'] in pages]
            
            logger.info(f"Starting page-by-page extraction for drawing {drawing_id}")
            logger.info(f"Total pages to process: {len(document_pages)}")
            
            # Extract elements page by page
            all_elements = []
            total_cost = 0.0
            total_processing_time = 0
            
            for page_idx, page_data in enumerate(document_pages):
                page_num = page_data['page_number']
                page_text = page_data['text']
                
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing page {page_num} ({page_idx + 1}/{len(document_pages)})")
                logger.info(f"Page size: {len(page_text)} characters")
                logger.info(f"Already extracted: {len(all_elements)} elements")
                logger.info(f"{'='*60}\n")
                
                # Generate prompt for this page
                prompt = await self._generate_page_prompt(
                    page_text=page_text,
                    page_number=page_num,
                    trade=trade,
                    all_pages_count=len(document_pages)
                )
                
                # Call LLM
                chunk_start = time.time()
                llm_response = await self._call_llm(prompt, model_name, trade)
                chunk_time = int((time.time() - chunk_start) * 1000)
                
                # Track costs
                chunk_cost = llm_response.get('cost_usd', 0)
                total_cost += chunk_cost
                total_processing_time += chunk_time
                
                logger.info(f"Page {page_num} completed in {chunk_time}ms, cost: ${chunk_cost:.4f}")
                
                # Save raw response
                await self._save_raw_response(llm_response, page_num)
                
                # Process chunk results
                chunk_elements = self._process_extraction_results(llm_response)
                
                if not chunk_elements:
                    logger.info(f"No elements found on page {page_num}")
                    continue  # Continue to next page instead of stopping
                
                # Log extraction results for this page
                logger.info(f"Page {page_num} yielded {len(chunk_elements)} elements")
                
                # Check for duplicates before adding
                new_elements = self._filter_duplicates(chunk_elements, all_elements)
                
                if not new_elements:
                    logger.info(f"No new elements on page {page_num} (all duplicates)")
                    continue  # Continue to next page
                
                logger.info(f"Page {page_num} contributed {len(new_elements)} new elements")
                all_elements.extend(new_elements)
                
                # Add small delay between pages to avoid rate limiting
                if page_idx < len(document_pages) - 1:  # Not the last page
                    import asyncio
                    logger.info("Waiting 2 seconds before next page...")
                    await asyncio.sleep(2)
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Page-by-page extraction complete!")
            logger.info(f"Total elements extracted: {len(all_elements)}")
            logger.info(f"Total pages processed: {len(document_pages)}")
            logger.info(f"Total cost: ${total_cost:.4f}")
            logger.info(f"Total time: {total_processing_time}ms")
            logger.info(f"{'='*60}\n")
            
            # Normalize and create element objects
            normalized_elements = self._normalize_elements(all_elements)
            await self._create_element_objects(extraction, normalized_elements)
            
            # Update extraction record
            await self._update_extraction_record(
                extraction=extraction,
                results=normalized_elements,
                processing_time_ms=total_processing_time,
                cost_usd=total_cost
            )
            
            return {
                'success': True,
                'extraction_id': str(extraction.id),
                'element_count': len(normalized_elements),
                'pages_processed': len(document_pages),
                'total_cost_usd': total_cost,
                'processing_time_ms': total_processing_time
            }
            
        except Exception as e:
            logger.error(f"Error during chunked extraction: {str(e)}", exc_info=True)
            
            # Update extraction record with error
            await self._mark_extraction_failed(extraction, str(e))
            
            return {
                'success': False,
                'error': str(e),
                'extraction_id': str(extraction.id)
            }
    
    async def _generate_chunked_prompt(
        self,
        drawing_text: str,
        trade: str,
        chunk_num: int,
        already_extracted: List[Dict]
    ) -> str:
        """
        Generate a prompt for chunked extraction
        
        Args:
            drawing_text: Full document text (full context)
            trade: Trade type
            chunk_num: Current chunk number
            already_extracted: List of elements already extracted
            
        Returns:
            Formatted prompt string
        """
        prompt_template = self.extraction_prompts.get(trade)
        if not prompt_template:
            raise ValueError(f"No prompt template found for trade: {trade}")
        
        # Build context based on chunk number
        if chunk_num == 1:
            # First chunk - extract first batch
            context_text = f"""
EXTRACTION MODE: Chunked Output (Batch {chunk_num})

🚨 ABSOLUTE LIMIT: MAXIMUM {self.ELEMENTS_PER_CHUNK} ELEMENTS 🚨

You are STRICTLY LIMITED to extracting ONLY {self.ELEMENTS_PER_CHUNK} elements in this response.
If you extract more than {self.ELEMENTS_PER_CHUNK} elements, the extraction will FAIL.

INSTRUCTIONS:
1. Extract ONLY the FIRST {self.ELEMENTS_PER_CHUNK} concrete elements
2. Start from the beginning of the document
3. COUNT each element as you extract: 1, 2, 3, ... {self.ELEMENTS_PER_CHUNK}
4. STOP IMMEDIATELY when you reach element #{self.ELEMENTS_PER_CHUNK}
5. DO NOT extract element #{self.ELEMENTS_PER_CHUNK + 1} or beyond

Your table MUST have EXACTLY {self.ELEMENTS_PER_CHUNK} data rows (or fewer if document has less).

After your table, add ONE of these lines:
- "CONTINUE: YES" if there are MORE elements after the {self.ELEMENTS_PER_CHUNK} you extracted
- "CONTINUE: NO" if you extracted ALL remaining elements

REMEMBER: {self.ELEMENTS_PER_CHUNK} elements maximum. No more.
"""
        else:
            # Continuation chunk
            extracted_ids = [elem.get('element_id', '') for elem in already_extracted]
            extracted_ids_str = ', '.join(extracted_ids[:50])  # Show first 50
            if len(extracted_ids) > 50:
                extracted_ids_str += f", ... and {len(extracted_ids) - 50} more"
            
            context_text = f"""
EXTRACTION MODE: Chunked Output (Batch {chunk_num} - CONTINUATION)

🚨 ABSOLUTE LIMIT: MAXIMUM {self.ELEMENTS_PER_CHUNK} NEW ELEMENTS 🚨

You are STRICTLY LIMITED to extracting ONLY {self.ELEMENTS_PER_CHUNK} NEW elements in this response.
If you extract more than {self.ELEMENTS_PER_CHUNK} elements, the extraction will FAIL.

You have already extracted {len(already_extracted)} elements in previous batches.

PREVIOUSLY EXTRACTED ELEMENT IDs (SKIP THESE):
{extracted_ids_str}

INSTRUCTIONS:
1. Extract ONLY the NEXT {self.ELEMENTS_PER_CHUNK} concrete elements (NOT in the list above)
2. Skip any elements already extracted
3. COUNT each NEW element as you extract: 1, 2, 3, ... {self.ELEMENTS_PER_CHUNK}
4. STOP IMMEDIATELY when you reach NEW element #{self.ELEMENTS_PER_CHUNK}
5. DO NOT extract NEW element #{self.ELEMENTS_PER_CHUNK + 1} or beyond

Your table MUST have EXACTLY {self.ELEMENTS_PER_CHUNK} data rows (or fewer if no more remain).

After your table, add ONE of these lines:
- "CONTINUE: YES" if there are MORE elements after the {self.ELEMENTS_PER_CHUNK} you extracted
- "CONTINUE: NO" if you extracted ALL remaining elements

REMEMBER: {self.ELEMENTS_PER_CHUNK} NEW elements maximum. No more.
"""
        
        # Create context dict
        context = {
            'chunked_extraction': context_text,
            'chunk_number': chunk_num,
            'elements_per_chunk': self.ELEMENTS_PER_CHUNK
        }
        
        # Get combined rules
        rules = get_combined_rules(trade)
        
        # Render prompt with full document text (full context)
        return prompt_template.render(
            input_data=drawing_text,
            context=context,
            universal_rules=rules
        )
    
    async def _get_document_pages(self, drawing) -> List[Dict]:
        """Get all pages from the document"""
        @sync_to_async
        def get_pages():
            try:
                if not drawing.rag_document:
                    logger.error(f"No RAG document linked to drawing {drawing.id}")
                    return []
                
                pages = drawing.rag_document.pages.all().order_by('page_number')
                return [
                    {
                        'page_number': page.page_number,
                        'text': page.page_text or ''
                    }
                    for page in pages
                ]
            except Exception as e:
                logger.error(f"Error getting pages for drawing {drawing.id}: {e}")
                return []
        
        return await get_pages()
    
    async def _generate_page_prompt(
        self,
        page_text: str,
        page_number: int,
        trade: str,
        all_pages_count: int
    ) -> str:
        """
        Generate a prompt for extracting elements from a single page
        
        Args:
            page_text: Text content of the page
            page_number: Page number being processed
            trade: Trade type
            all_pages_count: Total number of pages in document
            
        Returns:
            Formatted prompt string
        """
        prompt_template = self.extraction_prompts.get(trade)
        if not prompt_template:
            raise ValueError(f"No prompt template found for trade: {trade}")
        
        # Build page-specific context
        context_text = f"""
EXTRACTION MODE: Page-by-Page Extraction

📄 Processing Page {page_number} of {all_pages_count}

CRITICAL INSTRUCTIONS:
1. Extract ONLY concrete elements that are CLEARLY DEFINED on this page
2. Focus ONLY on elements shown on page {page_number}
3. Include complete specifications for each element
4. If an element spans multiple pages, extract it on the page where it's primarily defined

⚠️ IMPORTANT - DO NOT FORCE EXTRACTION:
- If this page contains NO concrete elements (e.g., title page, notes, general details), return "NO ELEMENTS"
- Only extract elements that have clear specifications (dimensions, reinforcement, concrete grade, etc.)
- DO NOT extract placeholder text, labels, or non-element information
- DO NOT make up or guess element data
- It is PERFECTLY ACCEPTABLE to return zero elements if the page has none

🎯 OUTPUT FORMAT FOR EMPTY PAGES:
If NO valid concrete elements with schedules/tables/dimensions exist on this page, respond with ONLY:
NO ELEMENTS

Do NOT output table headers for empty pages - just respond "NO ELEMENTS" to save tokens.
"""
        
        # Create context dict
        context = {
            'chunked_extraction': context_text,
            'page_number': page_number,
            'total_pages': all_pages_count
        }
        
        # Get combined rules
        rules = get_combined_rules(trade)
        
        # Render prompt with page text
        return prompt_template.render(
            input_data=page_text,
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
        Call LLM via modelhub with conservative output token limit
        
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
            entity_id=f"takeoff_{trade}_extraction_chunked",
            user_id="system",
            quality_critical=True,
            max_tokens=self.MAX_OUTPUT_TOKENS  # Conservative limit per chunk
        )
        
        # Add metadata for additional context
        request_context.metadata = {
            "complexity_score": 0.8,
            "expected_output_tokens": self.MAX_OUTPUT_TOKENS - 1000,  # Leave buffer
            "temperature": 0.1,
            "timeout_seconds": 180
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
    
    def _should_continue_extraction(
        self,
        llm_response: Dict[str, Any],
        chunk_elements: List[Dict],
        total_elements: int
    ) -> bool:
        """
        Determine if we should continue extracting more chunks
        
        Args:
            llm_response: Raw LLM response
            chunk_elements: Elements from this chunk
            total_elements: Total elements extracted so far
            
        Returns:
            True if should continue, False otherwise
        """
        response_text = llm_response.get('text', '').lower()
        
        # Check for explicit continuation markers
        if 'continue: yes' in response_text or 'continue:yes' in response_text:
            logger.info("LLM indicated more elements remain (CONTINUE: YES)")
            return True
        
        if 'continue: no' in response_text or 'continue:no' in response_text:
            logger.info("LLM indicated extraction complete (CONTINUE: NO)")
            return False
        
        # If we got a full chunk, assume there might be more
        if len(chunk_elements) >= self.ELEMENTS_PER_CHUNK:
            logger.info(f"Got full chunk ({len(chunk_elements)} elements), continuing")
            return True
        
        # If we got fewer elements than requested, probably done
        if len(chunk_elements) < self.ELEMENTS_PER_CHUNK:
            logger.info(f"Got partial chunk ({len(chunk_elements)} elements), likely complete")
            return False
        
        # Default: continue if we haven't hit max chunks
        return True
    
    def _filter_duplicates(
        self,
        new_elements: List[Dict],
        existing_elements: List[Dict]
    ) -> List[Dict]:
        """
        Filter out duplicate elements based on element_id
        
        Args:
            new_elements: New elements to check
            existing_elements: Already extracted elements
            
        Returns:
            List of non-duplicate elements
        """
        existing_ids = set(elem.get('element_id', '') for elem in existing_elements)
        
        unique_elements = []
        for elem in new_elements:
            elem_id = elem.get('element_id', '')
            if elem_id and elem_id not in existing_ids:
                unique_elements.append(elem)
                existing_ids.add(elem_id)
            else:
                logger.debug(f"Skipping duplicate element: {elem_id}")
        
        return unique_elements
    
    async def _save_raw_response(self, llm_response: Dict[str, Any], chunk_num: int) -> None:
        """Save raw LLM response to file for debugging"""
        try:
            response_text = llm_response.get('text', '')
            output_dir = '/app/backend/takeoff/tests/output'
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            response_file = os.path.join(output_dir, f'raw_llm_response_chunk{chunk_num}_{timestamp}.txt')
            
            with open(response_file, 'w') as f:
                f.write(response_text)
            
            logger.info(f"Raw LLM response (chunk {chunk_num}) saved to: {response_file}")
        except Exception as e:
            logger.warning(f"Failed to save raw response: {e}")
    
    # Import helper methods from original service
    # (These would be copied from llm_extraction.py)
    
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
        
        full_text = "\n\n".join(text_parts)
        logger.info(f"Retrieved {len(text_parts)} pages, total length: {len(full_text)} characters")
        
        return full_text
    
    @sync_to_async
    def _create_extraction_record(
        self,
        drawing: Drawing,
        extraction_method: str,
        user_id: str = None
    ) -> TakeoffExtraction:
        """Create initial extraction record"""
        from core.models import User
        
        user = None
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                pass
        
        extraction = TakeoffExtraction.objects.create(
            drawing=drawing,
            extraction_method=extraction_method,
            status='processing',
            created_by=user,
            elements={'items': []}
        )
        
        logger.info(f"Created extraction record: {extraction.id}")
        return extraction
    
    def _process_extraction_results(self, llm_response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process and validate extraction results from LLM
        Parse table format and convert to JSON
        """
        if not llm_response or not isinstance(llm_response, dict):
            logger.warning("Empty or invalid LLM response")
            return []
            
        response_text = llm_response.get('text', '')
        if not response_text:
            logger.warning("Empty text in LLM response")
            return []
        
        # Check for "NO ELEMENTS" response (empty page)
        if 'NO ELEMENTS' in response_text.upper().strip():
            logger.info("Page has no elements (NO ELEMENTS response)")
            return []
        
        # Check if response is in table format
        if '|' in response_text and ('ID|TYPE' in response_text or 'id|type' in response_text.lower()):
            logger.info("Detected table format response, parsing...")
            extraction_results = self._parse_table_to_json(response_text)
            logger.info(f"Successfully parsed table with {len(extraction_results)} elements")
            return extraction_results
        
        logger.warning("No table format found in LLM response")
        return []
    
    def _parse_table_to_json(self, table_text: str) -> List[Dict[str, Any]]:
        """Parse pipe-delimited table format to JSON"""
        lines = table_text.strip().split('\n')
        
        # Find header line
        header_line = None
        header_index = 0
        for i, line in enumerate(lines):
            if 'ID|TYPE' in line or 'id|type' in line.lower():
                header_line = line
                header_index = i
                break
        
        if not header_line:
            logger.warning("No header line found in table")
            return []
        
        # Parse header
        header = [col.strip() for col in header_line.split('|')]
        
        # Parse data rows
        elements = []
        for line in lines[header_index + 1:]:
            # Skip empty lines, separator lines, and continuation markers
            if not line.strip() or line.strip().startswith('-' * 5) or 'CONTINUE:' in line.upper():
                continue
            
            # Split by pipe
            values = line.split('|')
            
            # Skip if not enough values
            if len(values) < len(header):
                continue
            
            # Create element dict
            row_dict = dict(zip(header, values))
            
            # Convert to standard JSON format
            element = self._convert_table_row_to_json(row_dict)
            
            if element:
                elements.append(element)
        
        return elements
    
    def _is_valid_element(self, element_id: str, element_type: str, row_dict: Dict[str, str]) -> bool:
        """
        Validate if an extracted element is legitimate and not junk data
        
        Returns:
            True if element appears valid, False if it's likely junk
        """
        # Reject if ID is empty or just whitespace
        if not element_id or not element_id.strip():
            return False
        
        # Reject if ID is just a dash or placeholder
        if element_id in ['-', '_', '.', 'N/A', 'n/a', 'NA']:
            return False
        
        # Reject if ID is just a plain number (1, 2, 3, etc.) without context
        if element_id.isdigit() and len(element_id) <= 3:
            return False
        
        # Reject if ID looks like placeholder or junk
        junk_patterns = [
            'example', 'sample', 'typical', 'note', 'see', 'refer',
            'drawing', 'detail', 'section', 'plan', 'elevation',
            'title', 'legend', 'key', 'schedule', 'table',
            'xxx', '???', 'tbd', 'various', 'as shown', 'as per'
        ]
        
        element_id_lower = element_id.lower()
        for pattern in junk_patterns:
            if pattern in element_id_lower:
                return False
        
        # Reject if ID is too long (likely extracted text, not an ID)
        if len(element_id) > 50:
            return False
        
        # Reject if type looks invalid
        if not element_type or element_type == '-' or len(element_type) < 3:
            return False
        
        # For concrete elements, require at least ONE meaningful specification
        has_dimension = any(
            row_dict.get(field) and row_dict[field] not in ['-', '', 'N/A', 'n/a']
            for field in ['WIDTH', 'LENGTH', 'DEPTH']
        )
        
        has_reinforcement = any(
            row_dict.get(field) and row_dict[field] not in ['-', '', 'N/A', 'n/a']
            for field in ['TOP_REINF', 'BOT_REINF', 'SIDE_REINF']
        )
        
        has_concrete = row_dict.get('GRADE') and row_dict['GRADE'] not in ['-', '', 'N/A', 'n/a']
        
        # Element must have at least dimension OR reinforcement OR concrete grade
        if not (has_dimension or has_reinforcement or has_concrete):
            return False
        
        return True
    
    def _convert_table_row_to_json(self, row_dict: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Convert a table row to JSON format with full spec parsing"""
        element_id = row_dict.get('ID', '').strip()
        element_type = row_dict.get('TYPE', '').strip()
        
        # Skip invalid elements
        if not element_id or element_id == '-' or not element_type:
            return None
        
        # Quality validation - reject junk elements
        if not self._is_valid_element(element_id, element_type, row_dict):
            logger.debug(f"Rejected low-quality element: {element_id} ({element_type})")
            return None
        
        # Convert to standard JSON format
        element = {
            "element_id": element_id,
            "element_type": element_type,
            "page_number": int(row_dict.get('PAGE', 1)) if row_dict.get('PAGE', '').isdigit() else 1,
            "confidence_score": 1.0,
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
            try:
                element['specifications']['dimensions']['width_mm'] = int(row_dict['WIDTH'])
            except ValueError:
                pass
        if row_dict.get('LENGTH') and row_dict['LENGTH'] != '-':
            try:
                element['specifications']['dimensions']['length_mm'] = int(row_dict['LENGTH'])
            except ValueError:
                pass
        if row_dict.get('DEPTH') and row_dict['DEPTH'] != '-':
            try:
                element['specifications']['dimensions']['depth_mm'] = int(row_dict['DEPTH'])
            except ValueError:
                pass
        
        # Parse quantity
        if row_dict.get('QTY') and row_dict['QTY'] != '-':
            qty_str = row_dict['QTY']
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
        
        return element
    
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
    
    def _normalize_elements(self, elements: List[Dict]) -> List[Dict]:
        """Normalize element data"""
        # Add any missing default fields
        for element in elements:
            if 'specifications' not in element:
                element['specifications'] = {}
            if 'extraction_notes' not in element:
                element['extraction_notes'] = {}
        
        return elements
    
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
                element_id = result.get('element_id', '').strip()
                element_type = result.get('element_type', '').strip()
                
                # Skip elements with invalid IDs
                if not element_id or element_id == '-' or not element_type:
                    logger.warning(f"Skipping element with invalid ID or type: ID='{element_id}', Type='{element_type}'")
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
    
    @sync_to_async
    def _update_extraction_record(
        self,
        extraction: TakeoffExtraction,
        results: List[Dict],
        processing_time_ms: int,
        cost_usd: float
    ) -> None:
        """Update extraction record with results"""
        extraction.status = 'completed'
        extraction.elements = {'items': results}
        extraction.processing_time_ms = processing_time_ms
        extraction.extraction_cost_usd = Decimal(str(cost_usd))
        extraction.save()
        
        logger.info(f"Updated extraction record {extraction.id}: {len(results)} elements")
    
    @sync_to_async
    def _mark_extraction_failed(self, extraction: TakeoffExtraction, error: str) -> None:
        """Mark extraction as failed"""
        extraction.status = 'failed'
        extraction.processing_error = error
        extraction.save()
        
        logger.error(f"Marked extraction {extraction.id} as failed: {error}")
