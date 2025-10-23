# services/embedding_service.py

import logging
import time
import voyageai
import numpy as np
from typing import Optional, Tuple
from decimal import Decimal
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class VoyageEmbeddingService:
    """
    Voyage AI embedding service integrated with ModelHub.
    Retrieves API keys from ModelHub's APIKey model and tracks usage via ModelMetrics.
    """
    
    def __init__(self, organization=None, model_name: str = 'voyage-3.5-lite'):
        """
        Initialize the embedding service.
        
        Args:
            organization: Organization instance for API key retrieval
            model_name: Name of the Voyage model to use (voyage-3-lite, voyage-3.5-lite, voyage-3.5)
        """
        self.organization = organization
        self.model_name = model_name
        self._api_key = None
        self._api_key_source = None
        self._model_obj = None
        self._provider = None
    
    async def _ensure_initialized(self):
        """Ensure API key and model configuration are loaded"""
        if self._api_key and self._model_obj:
            return
        
        # Get API key from ModelHub
        api_key, source = await self._get_api_key()
        if not api_key:
            raise ValueError("No Voyage AI API key available. Please configure an API key in ModelHub.")
        
        self._api_key = api_key
        self._api_key_source = source
        
        # Get model configuration from ModelHub
        model_obj = await self._get_model()
        if not model_obj:
            raise ValueError(f"Model {self.model_name} not found in ModelHub. Please run setup_embedding_models command.")
        
        self._model_obj = model_obj
        self._provider = model_obj.provider
        
        logger.info(f"Initialized Voyage embedding service: model={self.model_name}, source={source}")
    
    @database_sync_to_async
    def _get_api_key(self) -> Tuple[Optional[str], str]:
        """Get API key from ModelHub's APIKey model"""
        from modelhub.models import APIKey
        
        try:
            # Try to get embedding-specific API key
            api_key_obj = None
            
            if self.organization:
                # Try organization key first
                api_key_obj = APIKey.objects.filter(
                    organization=self.organization,
                    provider__slug='voyage',
                    is_active=True
                ).first()
                
                if api_key_obj:
                    return api_key_obj.key, 'organization'
            
            # Fallback to system key
            api_key_obj = APIKey.objects.filter(
                organization__isnull=True,
                provider__slug='voyage',
                is_active=True
            ).first()
            
            if api_key_obj:
                return api_key_obj.key, 'system'
            
            return None, None
            
        except Exception as e:
            logger.error(f"Error getting Voyage AI API key: {e}")
            return None, None
    
    @database_sync_to_async
    def _get_model(self):
        """Get model configuration from ModelHub"""
        from modelhub.models import Model
        
        try:
            return Model.objects.select_related('provider').get(
                provider__slug='voyage',
                name=self.model_name,
                status='ACTIVE'
            )
        except Model.DoesNotExist:
            logger.error(f"Model {self.model_name} not found in ModelHub")
            return None
    
    async def embed_chunks(self, texts: list[str], input_type: str = "document") -> Tuple[np.ndarray, Decimal, int]:
        """
        Embed document chunks using Voyage AI.
        
        Args:
            texts: List of text chunks to embed
            input_type: Type of input ('document' or 'query')
        
        Returns:
            Tuple of (embeddings array, cost in USD, latency in ms)
        """
        await self._ensure_initialized()
        
        start_time = time.time()
        
        try:
            # Initialize Voyage client
            client = voyageai.Client(api_key=self._api_key)
            
            # Call Voyage API
            result = client.embed(
                texts=texts,
                model=self.model_name,
                input_type=input_type
            )
            
            embeddings = np.array(result.embeddings)
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Calculate cost using ModelHub pricing
            total_tokens = result.total_tokens if hasattr(result, 'total_tokens') else len(texts) * 100
            cost = (Decimal(str(total_tokens)) / 1000) * self._model_obj.cost_input
            
            # Log usage to ModelMetrics
            await self._log_usage(total_tokens, cost, latency_ms)
            
            logger.info(
                f"Embedded {len(texts)} chunks: "
                f"tokens={total_tokens}, cost=${cost:.6f}, latency={latency_ms}ms"
            )
            
            return embeddings, cost, latency_ms
            
        except Exception as e:
            logger.error(f"Error embedding chunks with Voyage AI: {e}")
            raise
    
    async def embed_query(self, query: str) -> Tuple[np.ndarray, Decimal, int]:
        """
        Embed a search query using Voyage AI.
        
        Args:
            query: Query text to embed
        
        Returns:
            Tuple of (embedding vector, cost in USD, latency in ms)
        """
        await self._ensure_initialized()
        
        start_time = time.time()
        
        try:
            # Initialize Voyage client
            client = voyageai.Client(api_key=self._api_key)
            
            # Call Voyage API
            result = client.embed(
                texts=[query],
                model=self.model_name,
                input_type="query"
            )
            
            embedding = np.array(result.embeddings[0])
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Calculate cost using ModelHub pricing
            total_tokens = result.total_tokens if hasattr(result, 'total_tokens') else 50
            cost = (Decimal(str(total_tokens)) / 1000) * self._model_obj.cost_input
            
            # Log usage to ModelMetrics
            await self._log_usage(total_tokens, cost, latency_ms)
            
            logger.debug(
                f"Embedded query: tokens={total_tokens}, cost=${cost:.6f}, latency={latency_ms}ms"
            )
            
            return embedding, cost, latency_ms
            
        except Exception as e:
            logger.error(f"Error embedding query with Voyage AI: {e}")
            raise
    
    @database_sync_to_async
    def _log_usage(self, tokens_processed: int, cost: Decimal, latency_ms: int):
        """Log embedding usage to ModelMetrics"""
        from modelhub.models import ModelMetrics, APIKey
        
        try:
            # Get the API key object for tracking
            api_key_obj = None
            if self._api_key_source == 'organization' and self.organization:
                api_key_obj = APIKey.objects.filter(
                    organization=self.organization,
                    provider__slug='voyage',
                    is_active=True
                ).first()
            elif self._api_key_source == 'system':
                api_key_obj = APIKey.objects.filter(
                    organization__isnull=True,
                    provider__slug='voyage',
                    is_active=True
                ).first()
            
            # Create metrics record
            ModelMetrics.objects.create(
                model=self._model_obj,
                organization=self.organization,
                api_key=api_key_obj,
                latency_ms=latency_ms,
                tokens_input=tokens_processed,
                tokens_output=0,  # Embeddings don't have output tokens
                cost=cost,
                status='SUCCESS',
                optimization_metadata={
                    'operation_type': 'embedding',
                    'model_name': self.model_name,
                    'api_key_source': self._api_key_source,
                    'tokens_per_second': int(tokens_processed / (latency_ms / 1000)) if latency_ms > 0 else 0,
                }
            )
            
        except Exception as e:
            logger.error(f"Error logging embedding usage: {e}")
    
    @property
    def dimensions(self) -> int:
        """Get the embedding dimensions for the current model"""
        if self._model_obj:
            return self._model_obj.embedding_dimensions or 2048
        # Default dimensions by model name
        if 'voyage-3-lite' in self.model_name:
            return 512
        return 2048
    
    @classmethod
    async def create_for_knowledge_base(cls, knowledge_base):
        """
        Create an embedding service instance for a knowledge base.
        Uses the knowledge base's configured embedding model.
        
        Args:
            knowledge_base: KnowledgeBase instance
        
        Returns:
            VoyageEmbeddingService instance
        """
        # Get the embedding model from the knowledge base
        embedding_model = knowledge_base.embedding_model
        
        if not embedding_model:
            # Default to voyage-3.5-lite if no model specified
            model_name = 'voyage-3.5-lite'
            logger.warning(
                f"No embedding model specified for knowledge base {knowledge_base.id}, "
                f"using default: {model_name}"
            )
        else:
            model_name = embedding_model.name
        
        # Create service instance with organization context
        service = cls(
            organization=knowledge_base.organization,
            model_name=model_name
        )
        
        return service


# Synchronous wrapper for backward compatibility
class SimpleVoyageEmbeddings:
    """
    Simple synchronous wrapper for Voyage AI embeddings.
    For use in synchronous contexts or quick testing.
    """
    
    def __init__(self, api_key: str, model_name: str = 'voyage-3.5-lite'):
        self.client = voyageai.Client(api_key=api_key)
        self.model_name = model_name
    
    def embed_chunks(self, texts: list[str]) -> np.ndarray:
        """Embed document chunks"""
        result = self.client.embed(
            texts=texts,
            model=self.model_name,
            input_type="document"
        )
        return np.array(result.embeddings)
    
    def embed_query(self, query: str) -> np.ndarray:
        """Embed search query"""
        result = self.client.embed(
            texts=[query],
            model=self.model_name,
            input_type="query"
        )
        return np.array(result.embeddings[0])

