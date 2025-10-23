# File: backend/rag_service/services/extraction/image_processor.py

"""
Image processing utilities for extraction services.

Provides functionality for:
- Converting documents to images
- Processing images for vision models
- Image format conversion and optimization

This module is used by the UnifiedExtractor to prepare images for LLM processing.
"""

import os
import base64
import logging
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple

logger = logging.getLogger(__name__)


class ImageProcessor:
    """
    Handles image processing for vision-based extraction.
    
    Features:
    - Convert documents (PDF, DOCX) to images
    - Optimize images for vision models
    - Format images for different provider APIs
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the image processor.
        
        Args:
            config: Configuration options
                - dpi: DPI for rendering (default: 300)
                - max_width: Maximum image width (default: 2048)
                - max_height: Maximum image height (default: 2048)
                - format: Output format (default: 'jpeg')
                - quality: JPEG quality (default: 90)
        """
        self.config = config or {}
        self.dpi = self.config.get('dpi', 300)
        self.max_width = self.config.get('max_width', 2048)
        self.max_height = self.config.get('max_height', 2048)
        self.format = self.config.get('format', 'jpeg')
        self.quality = self.config.get('quality', 90)
    
    async def convert_file_to_images(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Convert a file to a list of images.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of image dictionaries with data and metadata
        """
        try:
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext == '.pdf':
                return await self._convert_pdf_to_images(file_path)
            elif file_ext in ['.jpg', '.jpeg', '.png', '.webp', '.tiff', '.tif', '.bmp']:
                return await self._process_image_file(file_path)
            elif file_ext in ['.docx', '.doc']:
                return await self._convert_docx_to_images(file_path)
            else:
                logger.warning(f"Unsupported file format for image conversion: {file_ext}")
                return []
                
        except Exception as e:
            logger.error(f"Error converting file to images: {e}")
            return []
    
    async def _convert_pdf_to_images(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Convert PDF to images.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of image dictionaries
        """
        try:
            # Import here to avoid dependency if not used
            import fitz  # PyMuPDF
            
            images = []
            doc = fitz.open(file_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Get page dimensions
                width, height = page.rect.width, page.rect.height
                
                # Calculate zoom factor to achieve target DPI
                # 72 is the base DPI for PDF
                zoom = self.dpi / 72
                
                # Create matrix for rendering
                matrix = fitz.Matrix(zoom, zoom)
                
                # Render page to pixmap
                pix = page.get_pixmap(matrix=matrix)
                
                # Convert to desired format
                img_data = pix.tobytes(self.format)
                
                # Add to images list
                images.append({
                    'data': img_data,
                    'format': self.format,
                    'page_number': page_num + 1,
                    'width': pix.width,
                    'height': pix.height,
                    'dpi': self.dpi,
                    'original_width': width,
                    'original_height': height
                })
            
            doc.close()
            return images
            
        except ImportError:
            logger.error("PyMuPDF (fitz) not installed. Cannot convert PDF to images.")
            return []
        except Exception as e:
            logger.error(f"Error converting PDF to images: {e}")
            return []
    
    async def _process_image_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Process an image file.
        
        Args:
            file_path: Path to image file
            
        Returns:
            List containing single image dictionary
        """
        try:
            # Import here to avoid dependency if not used
            from PIL import Image
            
            with Image.open(file_path) as img:
                # Get original dimensions
                original_width, original_height = img.width, img.height
                
                # Convert to RGB if needed
                if img.mode not in ['RGB', 'RGBA']:
                    img = img.convert('RGB')
                
                # Resize if needed
                img = self._resize_image(img)
                
                # Save to bytes
                img_byte_arr = BytesIO()
                img.save(img_byte_arr, format=self.format.upper(), quality=self.quality)
                img_data = img_byte_arr.getvalue()
                
                return [{
                    'data': img_data,
                    'format': self.format,
                    'page_number': 1,
                    'width': img.width,
                    'height': img.height,
                    'dpi': self.dpi,
                    'original_width': original_width,
                    'original_height': original_height
                }]
                
        except ImportError:
            logger.error("Pillow not installed. Cannot process image file.")
            return []
        except Exception as e:
            logger.error(f"Error processing image file: {e}")
            return []
    
    async def _convert_docx_to_images(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Convert DOCX to images.
        
        Args:
            file_path: Path to DOCX file
            
        Returns:
            List of image dictionaries
        """
        try:
            # This is a placeholder for DOCX conversion
            # In a real implementation, you would:
            # 1. Convert DOCX to PDF using a library like python-docx-replace or docx2pdf
            # 2. Then convert the PDF to images using _convert_pdf_to_images
            
            logger.warning("DOCX to image conversion not fully implemented")
            
            # For now, we'll just return an empty list
            return []
            
        except Exception as e:
            logger.error(f"Error converting DOCX to images: {e}")
            return []
    
    def _resize_image(self, img):
        """
        Resize image if needed.
        
        Args:
            img: PIL Image object
            
        Returns:
            Resized PIL Image object
        """
        from PIL import Image
        
        width, height = img.width, img.height
        
        # Check if resizing is needed
        if width > self.max_width or height > self.max_height:
            # Calculate aspect ratio
            aspect_ratio = width / height
            
            if width > height:
                new_width = self.max_width
                new_height = int(new_width / aspect_ratio)
            else:
                new_height = self.max_height
                new_width = int(new_height * aspect_ratio)
            
            # Resize image
            img = img.resize((new_width, new_height), Image.LANCZOS)
        
        return img
    
    def encode_image_base64(self, image_data: bytes) -> str:
        """
        Encode image data as base64.
        
        Args:
            image_data: Raw image data
            
        Returns:
            Base64-encoded image data
        """
        return base64.b64encode(image_data).decode('utf-8')
    
    def get_data_uri(self, image_data: bytes, format: str = None) -> str:
        """
        Get data URI for image.
        
        Args:
            image_data: Raw image data
            format: Image format (default: self.format)
            
        Returns:
            Data URI string
        """
        format = format or self.format
        mime_type = f"image/{format}"
        base64_data = self.encode_image_base64(image_data)
        return f"data:{mime_type};base64,{base64_data}"
