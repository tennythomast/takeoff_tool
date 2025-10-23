# storage_retrieval/vector_stores/pinecone_store.py
"""
Pinecone Vector Store Implementation

Integrates with ModelHub for API key management and cost tracking.
Follows Pinecone best practices for serverless deployments.
"""

import json
import logging
import time
from typing import List, Dict, Any, Optional
import numpy as np

from asgiref.sync import sync_to_async

from .base import BaseVectorStore, SearchResult

logger = logging.getLogger(__name__)


class PineconeStore(BaseVectorStore):
    """
    Pinecone vector store implementation with ModelHub integration.
    
    Features:
    - Serverless deployment (recommended by Pinecone)
    - Namespace isolation per knowledge base
    - API key management via ModelHub
    - Cost tracking integration
    - Metadata filtering
    - Batch operations for efficiency
    
    Pinecone Limits (Free Tier):
    - 100K vectors
    - 1 index
    - Serverless: pay-per-use after free tier
    
    Recommended Setup:
    - Use serverless spec (auto-scaling, pay-per-use)
    - Region: us-east-1 (AWS) or us-west-2
    - Metric: cosine (best for embeddings)
    - Namespaces: One per knowledge base for isolation
    """
    
    def __init__(
        self,
        organization=None,
        index_name: str = "dataelan-rag",
        dimension: int = 1536,  # text-embedding-3-small default
        metric: str = "cosine",
        cloud: str = "aws",
        region: str = "us-east-1"
    ):
        """
        Initialize Pinecone store.
        
        Args:
            organization: Organization instance for API key lookup
            index_name: Name of the Pinecone index
            dimension: Embedding dimension (1536 for text-embedding-3-small)
            metric: Distance metric (cosine, euclidean, dotproduct)
            cloud: Cloud provider (aws, gcp, azure)
            region: Cloud region
        """
        self.organization = organization
        self.index_name = index_name
        self.dimension = dimension
        self.metric = metric
        self.cloud = cloud
        self.region = region
        
        self.pc = None
        self.index = None
        self.api_key = None
    
    async def initialize(self, create_if_not_exists: bool = True) -> bool:
        """
        Initialize Pinecone connection and index.
        
        Uses ModelHub to retrieve API key for the organization.
        
        Args:
            create_if_not_exists: Create index if it doesn't exist
            
        Returns:
            Success status
        """
        try:
            # Import Pinecone SDK
            try:
                from pinecone import Pinecone, ServerlessSpec
            except ImportError:
                logger.error("Pinecone SDK not installed. Install with: pip install pinecone-client")
                return False
            
            # Get API key from ModelHub
            api_key = await self._get_pinecone_api_key()
            if not api_key:
                logger.error("No Pinecone API key found in ModelHub")
                return False
            
            self.api_key = api_key
            
            # Initialize Pinecone client
            self.pc = Pinecone(api_key=self.api_key)
            
            # Check if index exists
            existing_indexes = self.pc.list_indexes()
            index_names = [idx.name for idx in existing_indexes]
            
            if self.index_name not in index_names:
                if create_if_not_exists:
                    logger.info(f"Creating Pinecone index: {self.index_name}")
                    
                    # Create index with serverless spec (recommended)
                    self.pc.create_index(
                        name=self.index_name,
                        dimension=self.dimension,
                        metric=self.metric,
                        spec=ServerlessSpec(
                            cloud=self.cloud,
                            region=self.region
                        )
                    )
                    
                    # Wait for index to be ready
                    logger.info("Waiting for index to be ready...")
                    while not self.pc.describe_index(self.index_name).status['ready']:
                        time.sleep(1)
                    
                    logger.info(f"Index {self.index_name} created successfully")
                else:
                    logger.error(f"Index {self.index_name} does not exist")
                    return False
            
            # Connect to index
            self.index = self.pc.Index(self.index_name)
            
            # Get and log stats
            stats = await self.get_stats()
            logger.info(
                f"Connected to Pinecone index: {self.index_name} "
                f"(vectors: {stats['total_vectors']}, dimensions: {stats['dimensions']})"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}", exc_info=True)
            return False
    
    async def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upsert vectors to Pinecone.
        
        Args:
            vectors: List of vector dictionaries with:
                - id: str - Unique identifier
                - values: List[float] - Embedding vector
                - metadata: Dict - Associated metadata
            namespace: Optional namespace (use knowledge_base_id)
            
        Returns:
            Result dictionary with success status and count
        """
        if not self.index:
            return {
                'success': False,
                'error': 'Pinecone not initialized',
                'count': 0
            }
        
        try:
            # Clean and prepare vectors
            vectors_to_upsert = []
            for vec_data in vectors:
                # Convert numpy array to list if needed
                values = vec_data['values']
                if isinstance(values, np.ndarray):
                    values = values.tolist()
                
                # Clean metadata to comply with Pinecone limits
                clean_metadata = self._clean_metadata(vec_data.get('metadata', {}))
                
                vectors_to_upsert.append({
                    'id': vec_data['id'],
                    'values': values,
                    'metadata': clean_metadata
                })
            
            # Batch upsert (Pinecone recommends batches of 100-200)
            batch_size = 100
            total_upserted = 0
            
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i + batch_size]
                
                # Upsert batch
                response = self.index.upsert(
                    vectors=batch,
                    namespace=namespace or ""
                )
                
                total_upserted += response.get('upserted_count', len(batch))
            
            logger.info(
                f"Upserted {total_upserted} vectors to Pinecone "
                f"(namespace: {namespace or 'default'})"
            )
            
            return {
                'success': True,
                'count': total_upserted,
                'index_name': self.index_name,
                'namespace': namespace
            }
            
        except Exception as e:
            logger.error(f"Failed to upsert vectors: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'count': 0
            }
    
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
        filter: Optional[Dict] = None,
        namespace: Optional[str] = None,
        include_metadata: bool = True,
        include_values: bool = False
    ) -> List[SearchResult]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filter: Metadata filter (e.g., {"document_id": "doc123"})
            namespace: Optional namespace (knowledge_base_id)
            include_metadata: Include metadata in results
            include_values: Include vector values in results
            
        Returns:
            List of SearchResult objects
        """
        if not self.index:
            logger.error("Pinecone not initialized")
            return []
        
        try:
            # Convert numpy array to list if needed
            query_vec = query_vector
            if isinstance(query_vec, np.ndarray):
                query_vec = query_vec.tolist()
            
            # Perform search
            response = self.index.query(
                vector=query_vec,
                top_k=top_k,
                filter=filter,
                namespace=namespace or "",
                include_metadata=include_metadata,
                include_values=include_values
            )
            
            # Convert to SearchResult objects
            results = []
            for match in response.get('matches', []):
                metadata = match.get('metadata', {})
                
                results.append(SearchResult(
                    chunk_id=match['id'],
                    score=match['score'],
                    metadata=metadata,
                    content=metadata.get('content', ''),
                    vector=match.get('values') if include_values else None
                ))
            
            logger.debug(
                f"Found {len(results)} results for query "
                f"(namespace: {namespace or 'default'})"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to search vectors: {e}", exc_info=True)
            return []
    
    async def delete_vectors(
        self,
        ids: List[str],
        namespace: Optional[str] = None
    ) -> bool:
        """
        Delete vectors by ID.
        
        Args:
            ids: List of vector IDs to delete
            namespace: Optional namespace
            
        Returns:
            Success status
        """
        if not self.index:
            logger.error("Pinecone not initialized")
            return False
        
        try:
            self.index.delete(
                ids=ids,
                namespace=namespace or ""
            )
            
            logger.info(
                f"Deleted {len(ids)} vectors from Pinecone "
                f"(namespace: {namespace or 'default'})"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete vectors: {e}", exc_info=True)
            return False
    
    async def delete_namespace(self, namespace: str) -> bool:
        """
        Delete an entire namespace.
        
        Args:
            namespace: Namespace to delete
            
        Returns:
            Success status
        """
        if not self.index:
            logger.error("Pinecone not initialized")
            return False
        
        try:
            self.index.delete(
                delete_all=True,
                namespace=namespace
            )
            
            logger.info(f"Deleted namespace: {namespace}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete namespace: {e}", exc_info=True)
            return False
    
    async def delete_by_filter(
        self,
        filter: Dict[str, Any],
        namespace: Optional[str] = None
    ) -> bool:
        """
        Delete vectors matching a filter.
        
        Args:
            filter: Metadata filter
            namespace: Optional namespace
            
        Returns:
            Success status
        """
        if not self.index:
            logger.error("Pinecone not initialized")
            return False
        
        try:
            self.index.delete(
                filter=filter,
                namespace=namespace or ""
            )
            
            logger.info(
                f"Deleted vectors matching filter: {filter} "
                f"(namespace: {namespace or 'default'})"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete by filter: {e}", exc_info=True)
            return False
    
    async def get_stats(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get index statistics.
        
        Args:
            namespace: Optional namespace to get stats for
            
        Returns:
            Statistics dictionary
        """
        if not self.index:
            return {
                'total_vectors': 0,
                'dimensions': self.dimension,
                'namespaces': {}
            }
        
        try:
            stats = self.index.describe_index_stats()
            
            result = {
                'total_vectors': stats.get('total_vector_count', 0),
                'dimensions': stats.get('dimension', self.dimension),
                'index_fullness': stats.get('index_fullness', 0),
                'namespaces': {}
            }
            
            # Add namespace-specific stats
            if 'namespaces' in stats:
                for ns_name, ns_stats in stats['namespaces'].items():
                    result['namespaces'][ns_name] = {
                        'vector_count': ns_stats.get('vector_count', 0)
                    }
            
            # If specific namespace requested, filter result
            if namespace and namespace in result['namespaces']:
                result['total_vectors'] = result['namespaces'][namespace]['vector_count']
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}", exc_info=True)
            return {
                'total_vectors': 0,
                'dimensions': self.dimension,
                'namespaces': {}
            }
    
    async def update_metadata(
        self,
        id: str,
        metadata: Dict[str, Any],
        namespace: Optional[str] = None
    ) -> bool:
        """
        Update metadata for a vector.
        
        Args:
            id: Vector ID
            metadata: New metadata
            namespace: Optional namespace
            
        Returns:
            Success status
        """
        if not self.index:
            logger.error("Pinecone not initialized")
            return False
        
        try:
            clean_metadata = self._clean_metadata(metadata)
            
            self.index.update(
                id=id,
                set_metadata=clean_metadata,
                namespace=namespace or ""
            )
            
            logger.debug(f"Updated metadata for vector: {id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update metadata: {e}", exc_info=True)
            return False
    
    async def _get_pinecone_api_key(self) -> Optional[str]:
        """
        Get Pinecone API key from ModelHub.
        
        Returns:
            API key string or None
        """
        try:
            from modelhub.models import APIKey
            
            @sync_to_async
            def get_key():
                # Look for Pinecone API key in ModelHub
                # Pinecone is typically stored as a provider or service key
                api_key = APIKey.objects.filter(
                    organization=self.organization,
                    provider__slug='pinecone',
                    is_active=True
                ).first()
                
                if not api_key:
                    # Try alternative lookup (service-level key)
                    api_key = APIKey.objects.filter(
                        organization=self.organization,
                        key_type='SERVICE',
                        metadata__service='pinecone',
                        is_active=True
                    ).first()
                
                return api_key.key if api_key else None
            
            return await get_key()
            
        except Exception as e:
            logger.error(f"Failed to retrieve Pinecone API key: {e}")
            return None
    
    def _clean_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean metadata to comply with Pinecone limitations.
        
        Pinecone metadata restrictions:
        - Max 40KB per vector
        - Only string, number, boolean, list of strings
        - No nested objects (flatten or serialize)
        
        Args:
            metadata: Raw metadata dictionary
            
        Returns:
            Cleaned metadata dictionary
        """
        clean = {}
        
        for key, value in metadata.items():
            # Skip None values
            if value is None:
                continue
            
            # Direct types: string, number, boolean
            if isinstance(value, (str, int, float, bool)):
                # Limit string length to prevent exceeding 40KB
                if isinstance(value, str):
                    clean[key] = value[:2000]  # Reasonable limit
                else:
                    clean[key] = value
            
            # List of strings
            elif isinstance(value, list):
                if all(isinstance(v, str) for v in value):
                    # Limit list size
                    clean[key] = value[:100]
                else:
                    # Convert to JSON string
                    clean[key] = json.dumps(value)[:2000]
            
            # Dict: flatten or serialize
            elif isinstance(value, dict):
                # Try to flatten simple dicts
                if len(value) < 5:
                    for sub_key, sub_value in value.items():
                        flat_key = f"{key}_{sub_key}"
                        if isinstance(sub_value, (str, int, float, bool)):
                            clean[flat_key] = sub_value
                else:
                    # Serialize complex dicts
                    clean[key] = json.dumps(value)[:2000]
            
            # Other types: convert to string
            else:
                clean[key] = str(value)[:2000]
        
        return clean
