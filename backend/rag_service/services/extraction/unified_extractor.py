"""
Unified extraction service that combines multiple extraction tasks into a single LLM call.

This module provides a unified approach to document extraction that eliminates duplicate
LLM calls across different extraction components (layout analysis, table extraction, etc.)
by combining all extraction tasks into a single, comprehensive prompt.
"""

import os
import base64
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
import pandas as pd

from .multi_task_prompts import ExtractionTask, MultiTaskPrompts, SpecializedPrompts

logger = logging.getLogger(__name__)


# Using ExtractionTask from multi_task_prompts.py


@dataclass
class ExtractionRequest:
    """Request for unified extraction"""
    file_path: str
    tasks: List[ExtractionTask] = field(default_factory=lambda: [ExtractionTask.ALL])
    organization: Any = None
    page_range: Optional[List[int]] = None
    max_pages: int = 10
    quality_priority: str = 'balanced'  # 'cost', 'quality', or 'balanced'
    max_cost_usd: float = 1.0
    specialized_prompt: Optional[str] = None  # Custom specialized prompt to use


@dataclass
class ExtractionResponse:
    """Response from unified extraction"""
    text: str = ""
    layout_blocks: List[Dict] = field(default_factory=list)
    tables: List[Dict] = field(default_factory=list)
    entities: List[Dict] = field(default_factory=list)
    summary: str = ""
    visual_elements: Optional[Dict] = None 
    drawing_metadata: Optional[Dict] = None 
    metadata: Dict[str, Any] = field(default_factory=dict)
    cost_usd: float = 0.0
    processing_time_ms: int = 0
    model_used: str = ""
    provider_used: str = ""
    success: bool = True
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class UnifiedExtractor:
    """
    Unified extraction service that combines multiple extraction tasks into a single LLM call.
    
    This service eliminates duplicate LLM calls across different extraction components
    by combining all extraction tasks into a single, comprehensive prompt.
    
    Features:
    - Single LLM call for multiple extraction tasks
    - Shared ModelHub integration for all extraction tasks
    - Optimized prompts for different document types
    - Proper cost tracking and API key management
    """
    
    def __init__(self):
        """Initialize the unified extractor"""
        # We'll import these lazily to avoid circular imports
        from .image_processor import ImageProcessor
        # Use smaller max dimensions for vision APIs
        self.image_processor = ImageProcessor({
            'max_width': 4000,  # Anthropic limit is 8000
            'max_height': 4000,  # Anthropic limit is 8000
            'quality': 85  # Reduce quality to decrease file size
        })
    
    async def extract(self, request: ExtractionRequest) -> ExtractionResponse:
        """
        Perform unified extraction on a document.
        
        Args:
            request: Extraction request parameters
            
        Returns:
            ExtractionResponse with all requested extraction results
        """
        try:
            # Import ModelHub components
            from modelhub.services.routing import EnhancedModelRouter
            from modelhub.services.routing.types import RequestContext, OptimizationStrategy
            from modelhub.services.unified_llm_client import UnifiedLLMClient
            from modelhub.models import Model, APIKey, ModelMetrics
            
            # Convert file to images
            images = await self.image_processor.convert_file_to_images(request.file_path)
            
            if not images:
                return ExtractionResponse(
                    success=False,
                    error="Failed to convert file to images"
                )
            
            # Filter to specific pages if requested
            if request.page_range:
                images = [img for i, img in enumerate(images) if i in request.page_range]
            
            # Limit number of pages to process
            images = images[:request.max_pages]
            
            # Select vision model
            context = RequestContext(
                entity_type='unified_extraction',
                session_id=f'unified_{os.path.basename(request.file_path)}',
                organization_id=str(request.organization.id) if request.organization else None,
                max_tokens=4000,
                metadata={
                    'priority': request.quality_priority,
                    'image_count': len(images),
                    'tasks': [task.value for task in request.tasks],
                    'max_cost': request.max_cost_usd
                }
            )
            
            router = EnhancedModelRouter()
            decision = await router.route_request(
                organization=request.organization,
                complexity_score=0.7,
                content_type='vision',
                context=context,
                strategy=OptimizationStrategy.BALANCED
            )
            
            if not decision:
                return ExtractionResponse(
                    success=False,
                    error="No vision model available for extraction"
                )
            
            # Get model and API key
            model = await Model.get_model_async(
                provider_slug=decision.selected_provider,
                model_name=decision.selected_model
            )
            
            api_key = await APIKey.get_vision_key_async(
                provider_slug=model.provider.slug,
                organization=request.organization
            )
            
            if not api_key:
                return ExtractionResponse(
                    success=False,
                    error=f"No API key for {model.provider.slug}"
                )
            
            # Process each page
            response = ExtractionResponse(
                model_used=model.name,
                provider_used=model.provider.slug,
                metadata={
                    'file_path': request.file_path,
                    'file_name': os.path.basename(request.file_path),
                    'page_count': len(images),
                    'tasks': [task.value for task in request.tasks]
                }
            )
            
            llm_client = UnifiedLLMClient()
            total_cost = 0.0
            total_time_ms = 0
            
            for page_num, image in enumerate(images):
                # Build the unified prompt based on requested tasks and specialized prompt
                prompt = self._build_unified_prompt(request.tasks, request.specialized_prompt)
                
                # Encode image
                base64_image = base64.b64encode(image['data']).decode('utf-8')
                
                # Build vision messages
                messages = self._build_vision_messages(
                    prompt=prompt,
                    base64_image=base64_image,
                    provider_slug=model.provider.slug
                )
                
                # Call LLM
                llm_response = await llm_client.call_llm(
                    provider_slug=model.provider.slug,
                    model_name=model.name,
                    api_key=api_key.key,
                    messages=messages,
                    max_tokens=4000,
                    temperature=0.1
                )
                
                # Track metrics
                await ModelMetrics.log_vision_usage_async(
                    model=model,
                    organization=request.organization,
                    tokens_input=llm_response.tokens_input,
                    tokens_output=llm_response.tokens_output,
                    image_count=1,
                    cost=float(llm_response.cost),
                    latency_ms=llm_response.latency_ms,
                    api_key=api_key,
                    metadata={'task': 'unified_extraction', 'page': page_num + 1}
                )
                
                # Update cost and time tracking
                total_cost += float(llm_response.cost)
                total_time_ms += llm_response.latency_ms
                
                # Parse response
                if llm_response.content and not llm_response.raw_response.get('error'):
                    try:
                        page_results = json.loads(llm_response.content)
                        self._merge_page_results(response, page_results, page_num + 1)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse LLM response for page {page_num + 1}: {e}")
                        response.warnings.append(f"Failed to parse response for page {page_num + 1}")
            
            # Update final cost and time
            response.cost_usd = total_cost
            response.processing_time_ms = total_time_ms
            
            return response
            
        except Exception as e:
            logger.error(f"Error in unified extraction: {str(e)}")
            return ExtractionResponse(
                success=False,
                error=str(e)
            )
    
    def _build_unified_prompt(self, tasks: List[ExtractionTask], specialized_prompt: Optional[str] = None) -> str:
        """
        Build a unified prompt that extracts all requested information.
        
        Args:
            tasks: List of extraction tasks to perform
            specialized_prompt: Optional specialized prompt to use
            
        Returns:
            Comprehensive prompt for the vision model
        """
        # Start with the base prompt from MultiTaskPrompts
        prompt = MultiTaskPrompts.build_unified_prompt(tasks)
        
        # If a specialized prompt is provided, add it to the beginning
        if specialized_prompt:
            # Insert the specialized prompt after the initial instruction but before the task details
            lines = prompt.split('\n')
            # Find the first empty line after the initial instruction
            for i, line in enumerate(lines):
                if i > 0 and not line.strip():
                    # Insert the specialized prompt here
                    lines.insert(i, "\n" + specialized_prompt + "\n")
                    break
            prompt = "\n".join(lines)
            
        return prompt
    
    def _build_vision_messages(
        self,
        prompt: str,
        base64_image: str,
        provider_slug: str
    ) -> List[Dict]:
        """Build provider-specific vision messages"""
        if provider_slug == 'anthropic':
            return [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64_image
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }
            ]
        else:
            # OpenAI format (also for Qwen, local models)
            return [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
    
    def _merge_page_results(self, response: ExtractionResponse, page_results: Dict, page_num: int) -> None:
        """
        Merge results from a single page into the overall response.
        
        Args:
            response: Overall extraction response to update
            page_results: Results from a single page
            page_num: Page number (1-indexed)
        """
        # Merge text
        if "text" in page_results:
            if response.text:
                response.text += f"\n\n--- Page {page_num} ---\n\n"
            response.text += page_results["text"]
        
        # Merge layout blocks
        if "layout" in page_results:
            for block in page_results["layout"]:
                block["page"] = page_num
                response.layout_blocks.append(block)
        
        # Merge tables
        if "tables" in page_results:
            for table_data in page_results["tables"]:
                if not table_data.get("headers") or not table_data.get("rows"):
                    continue
                
                # Convert to DataFrame
                df = pd.DataFrame(
                    table_data["rows"],
                    columns=table_data["headers"]
                )
                
                # Add to tables list
                response.tables.append({
                    "data": df,
                    "page": page_num,
                    "caption": table_data.get("caption", ""),
                    "position": table_data.get("position", ""),
                    "markdown": df.to_markdown(index=False),
                    "text": df.to_string(index=False)
                })
        
        # Merge entities
        if "entities" in page_results:
            for entity in page_results["entities"]:
                entity["page"] = page_num
                response.entities.append(entity)
        
        # Merge summary (concatenate)
        if "summary" in page_results:
            if response.summary:
                response.summary += f"\n\nPage {page_num}: "
            else:
                response.summary = f"Page {page_num}: "
            response.summary += page_results["summary"]


async def create_unified_extractor() -> UnifiedExtractor:
    """Factory function to create a unified extractor"""
    return UnifiedExtractor()
