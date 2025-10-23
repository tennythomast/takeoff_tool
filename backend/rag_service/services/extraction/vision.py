# File: backend/rag_service/services/extraction/vision.py

"""
Vision-based extraction using ModelHub infrastructure.

Integrates with:
- UnifiedLLMClient: API execution
- ModelRouter: Model selection
- ModelMetrics: Cost tracking
- APIKey: Key management
"""

import base64
import json
import asyncio
import time
import logging
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from .base import BaseExtractor, ExtractionResult
from modelhub.services.routing import EnhancedModelRouter
from modelhub.services.routing.types import RequestContext
from modelhub.services.unified_llm_client import UnifiedLLMClient
from modelhub.models import Model, APIKey, ModelMetrics
from file_storage.models import FileUpload

logger = logging.getLogger(__name__)

@dataclass
class VisionConfig:
    """Configuration for vision extraction"""
    priority: str = 'cost'  # 'cost', 'quality', 'balanced'
    max_cost_per_document: float = 1.0
    max_cost_per_page: float = 0.10
    image_dpi: int = 300
    max_pages: int = 100
    expected_output_tokens: int = 2000
    structured_output: bool = True
    max_retries: int = 3
    retry_delay_seconds: float = 2.0


class ImageProcessor:
    """Helper class for image processing"""
    
    def __init__(self, dpi: int = 300):
        self.dpi = dpi
        
    async def convert_file_to_images(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Convert a file (PDF, image) to a list of images.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of image dictionaries with data and metadata
        """
        try:
            # Import libraries here to avoid dependencies if not used
            import fitz  # PyMuPDF
            from PIL import Image
            
            file_ext = Path(file_path).suffix.lower()
            images = []
            
            # Handle PDF files
            if file_ext == '.pdf':
                doc = fitz.open(file_path)
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    pix = page.get_pixmap(dpi=self.dpi)
                    img_data = pix.tobytes("jpeg")
                    
                    images.append({
                        'data': img_data,
                        'format': 'jpeg',
                        'page_number': page_num + 1,
                        'width': pix.width,
                        'height': pix.height,
                        'dpi': self.dpi
                    })
                doc.close()
                
            # Handle image files
            elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.webp']:
                with Image.open(file_path) as img:
                    # Convert to RGB if needed
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Save to bytes
                    img_byte_arr = BytesIO()
                    img.save(img_byte_arr, format='JPEG')
                    img_data = img_byte_arr.getvalue()
                    
                    images.append({
                        'data': img_data,
                        'format': 'jpeg',
                        'page_number': 1,
                        'width': img.width,
                        'height': img.height,
                        'dpi': self.dpi
                    })
            else:
                raise ValueError(f"Unsupported file format: {file_ext}")
                
            return images
            
        except Exception as e:
            logger.error(f"Error converting file to images: {e}")
            return []


class VisionExtractor(BaseExtractor):
    """
    Vision extraction using existing ModelHub infrastructure.
    
    Key integrations:
    - UnifiedLLMClient: Handles all API calls
    - ModelRouter: Selects optimal model
    - ModelMetrics: Tracks usage and costs
    - APIKey: Manages provider keys
    """
    
    def __init__(self, config: VisionConfig = None):
        self.config = config or VisionConfig()
        self.image_processor = ImageProcessor(dpi=self.config.image_dpi)
        self.llm_client = UnifiedLLMClient()
        
    async def extract(self, file_upload: FileUpload) -> ExtractionResult:
        """
        Extract content from images/PDFs using vision models.
        
        Pipeline:
        1. Convert file to images
        2. Select model via ModelRouter (no hardcoding)
        3. Get API key for selected provider
        4. Build vision prompt
        5. Execute via UnifiedLLMClient (with retry)
        6. Parse and validate response
        7. Track metrics via ModelMetrics
        8. Return ExtractionResult
        """
        start_time = time.time()
        
        try:
            # Step 1: Convert to images
            images = await self._convert_to_images(file_upload)
            
            if not images:
                return self._error_result("No images to process")
            
            # Step 2: Select model via routing
            model = await self._select_vision_model(
                file_upload=file_upload,
                image_count=len(images)
            )
            
            if not model:
                return self._error_result("No vision model available")
            
            logger.info(f"Selected model: {model.name} (provider: {model.provider.slug})")
            
            # Step 3: Get API key
            api_key = await APIKey.get_vision_key_async(
                provider_slug=model.provider.slug,
                organization=file_upload.organization
            )
            
            if not api_key:
                return self._error_result(f"No API key for {model.provider.slug}")
            
            # Step 4: Build prompt
            prompt = self._build_prompt(file_upload.document_type)
            
            # Step 5: Process images (with retry)
            results = []
            for i, image in enumerate(images[:self.config.max_pages]):
                result = await self._extract_from_image_with_retry(
                    image=image,
                    model=model,
                    api_key=api_key,
                    prompt=prompt,
                    page_number=i + 1
                )
                results.append(result)
            
            # Step 6: Combine results
            combined = self._combine_results(results)
            
            # Step 7: Track metrics
            await self._log_metrics(
                model=model,
                organization=file_upload.organization,
                api_key=api_key,
                results=results,
                duration=time.time() - start_time
            )
            
            # Step 8: Return result
            return ExtractionResult(
                success=True,
                extracted_text=combined['text'],
                structured_data=combined['structured'],
                metadata=combined['metadata'],
                extraction_method='vision',
                model_used=model.name,
                provider_used=model.provider.slug,
                tokens_used_input=combined['tokens_input'],
                tokens_used_output=combined['tokens_output'],
                image_count=len(images),
                cost_usd=combined['cost'],
                processing_time=time.time() - start_time,
                confidence_score=combined['confidence'],
                warnings=combined['warnings']
            )
            
        except Exception as e:
            logger.error(f"Vision extraction failed: {e}")
            return self._error_result(str(e))
    
    async def _convert_to_images(self, file_upload: FileUpload) -> List[Dict]:
        """Convert file upload to list of images"""
        # Get file path from FileUpload
        file_path = file_upload.file.path
        
        # Use image processor to convert to images
        return await self.image_processor.convert_file_to_images(file_path)
    
    async def _select_vision_model(
        self, 
        file_upload: FileUpload, 
        image_count: int
    ) -> Optional[Model]:
        """
        Select vision model using ModelRouter.
        NO HARDCODED MODEL NAMES.
        """
        context = RequestContext(
            entity_type='vision_extraction',
            session_id=str(file_upload.id),
            organization_id=str(file_upload.organization_id),
            max_tokens=self.config.expected_output_tokens,
            metadata={
                'file_type': file_upload.document_type,
                'priority': self.config.priority,
                'image_count': image_count,
                'budget': self.config.max_cost_per_document
            }
        )
        
        # Model router
        self.model_router = EnhancedModelRouter()
        decision = await self.model_router.get_model_for_request(
            model_type='VISION',
            organization=file_upload.organization,
            request_context=context.__dict__
        )
        
        if not decision:
            logger.error("Router returned no model")
            return None
        
        # Get the Model instance
        model = await Model.get_model_async(
            provider_slug=decision[0],  # provider_slug
            model_name=decision[1]      # model_name
        )
        
        return model
    
    async def _extract_from_image_with_retry(
        self,
        image: Dict,
        model: Model,
        api_key: APIKey,
        prompt: str,
        page_number: int
    ) -> Dict:
        """
        Extract from single image with retry logic.
        Uses UnifiedLLMClient for actual execution.
        """
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                result = await self._extract_from_image(
                    image=image,
                    model=model,
                    api_key=api_key,
                    prompt=prompt,
                    page_number=page_number
                )
                
                if result['success']:
                    return result
                
                # If not successful but no exception, log and retry
                logger.warning(f"Extraction failed on attempt {attempt + 1}")
                last_error = result.get('error', 'Unknown error')
                
            except Exception as e:
                last_error = str(e)
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                
                # Don't retry on auth errors
                if 'authentication' in str(e).lower():
                    break
            
            # Wait before retry
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1))
        
        # All retries failed
        return {
            'success': False,
            'error': last_error,
            'page_number': page_number,
            'text': '',
            'structured': {},
            'tokens_input': 0,
            'tokens_output': 0,
            'cost': 0,
            'latency_ms': 0,
            'confidence': 0
        }
    
    async def _extract_from_image(
        self,
        image: Dict,
        model: Model,
        api_key: APIKey,
        prompt: str,
        page_number: int
    ) -> Dict:
        """
        Extract from single image using UnifiedLLMClient.
        """
        # Get image data from dict
        image_data = image['data']
        
        # Encode image to base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # Build vision message format
        messages = self._build_vision_messages(
            prompt=prompt,
            base64_image=base64_image,
            provider_slug=model.provider.slug
        )
        
        # Execute via UnifiedLLMClient (handles all API details)
        response = await self.llm_client.call_llm(
            provider_slug=model.provider.slug,
            model_name=model.name,
            api_key=api_key.key,
            messages=messages,
            stream=False,
            max_tokens=self.config.expected_output_tokens,
            temperature=0.1
        )
        
        # Check for errors
        if response.raw_response.get('error'):
            return {
                'success': False,
                'error': response.content,
                'page_number': page_number,
                'text': '',
                'structured': {},
                'tokens_input': response.tokens_input,
                'tokens_output': response.tokens_output,
                'cost': float(response.cost),
                'latency_ms': response.latency_ms,
                'confidence': 0
            }
        
        # Parse response
        try:
            if self.config.structured_output:
                # Try to parse as JSON if structured output is requested
                try:
                    structured = json.loads(response.content)
                except json.JSONDecodeError:
                    # If JSON parsing fails, try to extract JSON from text
                    structured = self._extract_json_from_text(response.content)
            else:
                structured = {'text': response.content}
            
            return {
                'success': True,
                'page_number': page_number,
                'text': structured.get('text_content', response.content),
                'structured': structured,
                'tokens_input': response.tokens_input,
                'tokens_output': response.tokens_output,
                'cost': float(response.cost),
                'latency_ms': response.latency_ms,
                'confidence': structured.get('confidence', 0.85)  # Extract from response if available
            }
            
        except Exception as e:
            # If JSON parsing fails, use raw text
            logger.warning(f"Error parsing response: {e}")
            return {
                'success': True,
                'page_number': page_number,
                'text': response.content,
                'structured': {},
                'tokens_input': response.tokens_input,
                'tokens_output': response.tokens_output,
                'cost': float(response.cost),
                'latency_ms': response.latency_ms,
                'confidence': 0.70  # Lower confidence for non-JSON
            }
    
    def _build_vision_messages(
        self,
        prompt: str,
        base64_image: str,
        provider_slug: str
    ) -> List[Dict]:
        """
        Build provider-specific message format for vision.
        """
        if provider_slug == 'anthropic':
            # Anthropic format
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
            # OpenAI format (also works for Qwen, local models)
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
    
    def _build_prompt(self, document_type: str) -> str:
        """
        Build prompt based on document type.
        """
        base_prompt = (
            "Extract all text content from this image. "
            "Maintain the original structure and formatting as much as possible. "
            "Include all visible text, tables, headers, footers, and any other textual information."
        )
        
        if document_type == 'engineering_drawing':
            return (
                f"{base_prompt} "
                "This is an engineering drawing. Pay special attention to:"
                "\n- Dimensions and measurements"
                "\n- Part numbers and specifications"
                "\n- Notes and annotations"
                "\n- Tables with specifications"
                "\n- Title block information"
                "\nFormat your response as JSON with the following structure:"
                "\n```json"
                "\n{"
                "\n  \"text_content\": \"Full extracted text\","
                "\n  \"title\": \"Drawing title\","
                "\n  \"drawing_number\": \"Number if available\","
                "\n  \"dimensions\": [\"List of key dimensions\"],"
                "\n  \"notes\": [\"List of important notes\"],"
                "\n  \"confidence\": 0.95"
                "\n}"
                "\n```"
            )
        elif document_type == 'invoice':
            return (
                f"{base_prompt} "
                "This is an invoice. Pay special attention to:"
                "\n- Invoice number and date"
                "\n- Vendor and customer information"
                "\n- Line items and their descriptions"
                "\n- Prices, quantities, and totals"
                "\n- Tax information"
                "\n- Payment terms"
                "\nFormat your response as JSON with the following structure:"
                "\n```json"
                "\n{"
                "\n  \"text_content\": \"Full extracted text\","
                "\n  \"invoice_number\": \"Number\","
                "\n  \"date\": \"Date\","
                "\n  \"vendor\": \"Vendor name\","
                "\n  \"customer\": \"Customer name\","
                "\n  \"line_items\": [{\"description\": \"Item\", \"quantity\": 1, \"price\": 0.00}],"
                "\n  \"total\": 0.00,"
                "\n  \"confidence\": 0.95"
                "\n}"
                "\n```"
            )
        else:
            # Generic document
            return (
                f"{base_prompt} "
                "Format your response as JSON with the following structure:"
                "\n```json"
                "\n{"
                "\n  \"text_content\": \"Full extracted text\","
                "\n  \"title\": \"Document title if available\","
                "\n  \"sections\": [\"List of main sections\"],"
                "\n  \"key_points\": [\"List of key information\"],"
                "\n  \"confidence\": 0.95"
                "\n}"
                "\n```"
            )
    
    def _extract_json_from_text(self, text: str) -> Dict:
        """
        Extract JSON from text that might contain markdown code blocks.
        """
        # Look for JSON in code blocks
        import re
        json_pattern = r'```(?:json)?\s*({[\s\S]*?})\s*```'
        matches = re.findall(json_pattern, text)
        
        if matches:
            # Try each match until one parses
            for match in matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        
        # If no valid JSON in code blocks, look for JSON-like structure
        try:
            # Find anything that looks like a JSON object
            obj_pattern = r'{[\s\S]*?}'
            obj_matches = re.findall(obj_pattern, text)
            
            for match in obj_matches:
                try:
                    return json.loads(match)
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass
        
        # Fallback to raw text
        return {"text_content": text}
    
    def _combine_results(self, results: List[Dict]) -> Dict:
        """
        Combine results from multiple images.
        """
        # Filter out failed results
        successful_results = [r for r in results if r.get('success', False)]
        
        if not successful_results:
            return {
                'text': '',
                'structured': {},
                'metadata': {
                    'page_count': 0,
                    'successful_pages': 0,
                    'failed_pages': len(results)
                },
                'tokens_input': 0,
                'tokens_output': 0,
                'cost': 0,
                'confidence': 0,
                'warnings': ['All extraction attempts failed']
            }
        
        # Combine text with page numbers
        combined_text = []
        combined_structured = {
            'pages': []
        }
        
        # Track totals
        total_tokens_input = 0
        total_tokens_output = 0
        total_cost = 0
        total_confidence = 0
        warnings = []
        
        for result in successful_results:
            page_num = result.get('page_number', 0)
            page_text = result.get('text', '')
            
            # Add page header
            combined_text.append(f"\n--- Page {page_num} ---\n")
            combined_text.append(page_text)
            
            # Add to structured data
            combined_structured['pages'].append({
                'page_number': page_num,
                'content': result.get('text', ''),
                'structured': result.get('structured', {})
            })
            
            # Track totals
            total_tokens_input += result.get('tokens_input', 0)
            total_tokens_output += result.get('tokens_output', 0)
            total_cost += result.get('cost', 0)
            total_confidence += result.get('confidence', 0)
            
            # Track warnings
            if 'error' in result and result['error']:
                warnings.append(f"Page {page_num}: {result['error']}")
        
        # Calculate average confidence
        avg_confidence = total_confidence / len(successful_results) if successful_results else 0
        
        # Add metadata
        metadata = {
            'page_count': len(results),
            'successful_pages': len(successful_results),
            'failed_pages': len(results) - len(successful_results),
            'average_confidence': avg_confidence
        }
        
        # Add document-level fields if available
        if successful_results and 'structured' in successful_results[0]:
            for key, value in successful_results[0]['structured'].items():
                if key not in ['text_content', 'confidence'] and isinstance(value, (str, int, float, bool)):
                    combined_structured[key] = value
        
        return {
            'text': '\n'.join(combined_text),
            'structured': combined_structured,
            'metadata': metadata,
            'tokens_input': total_tokens_input,
            'tokens_output': total_tokens_output,
            'cost': total_cost,
            'confidence': avg_confidence,
            'warnings': warnings
        }
    
    async def _log_metrics(
        self,
        model: Model,
        organization,
        api_key: APIKey,
        results: List[Dict],
        duration: float
    ) -> None:
        """
        Log metrics for vision extraction.
        """
        # Filter out failed results
        successful_results = [r for r in results if r.get('success', False)]
        
        if not successful_results:
            return
        
        # Calculate totals
        total_tokens_input = sum(r.get('tokens_input', 0) for r in successful_results)
        total_tokens_output = sum(r.get('tokens_output', 0) for r in successful_results)
        total_cost = sum(r.get('cost', 0) for r in successful_results)
        total_latency = sum(r.get('latency_ms', 0) for r in successful_results)
        image_count = len(successful_results)
        
        # Additional metadata
        metadata = {
            'extraction_type': 'vision',
            'page_count': len(results),
            'successful_pages': len(successful_results),
            'failed_pages': len(results) - len(successful_results),
            'total_duration_ms': int(duration * 1000),
            'avg_page_duration_ms': int((duration * 1000) / len(results)) if results else 0
        }
        
        # Log metrics
        await ModelMetrics.log_vision_usage_async(
            model=model,
            organization=organization,
            tokens_input=total_tokens_input,
            tokens_output=total_tokens_output,
            image_count=image_count,
            cost=Decimal(str(total_cost)),
            latency_ms=total_latency,
            api_key=api_key,
            metadata=metadata
        )
    
    def _error_result(self, error_message: str) -> ExtractionResult:
        """
        Create an error result.
        """
        return ExtractionResult(
            success=False,
            extracted_text='',
            structured_data={},
            metadata={},
            extraction_method='vision',
            model_used='',
            provider_used='',
            tokens_used_input=0,
            tokens_used_output=0,
            image_count=0,
            cost_usd=0,
            processing_time=0,
            confidence_score=0,
            warnings=[error_message]
        )
