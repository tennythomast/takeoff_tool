# storage_retrieval/vector_stores/base.py
"""
Base Vector Store Interface

Abstract base class for vector store implementations.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import numpy as np


@dataclass
class SearchResult:
    """
    Search result from vector store.
    
    Attributes:
        chunk_id: Unique chunk identifier
        score: Similarity score (higher is better)
        metadata: Chunk metadata
        content: Chunk content text
        vector: Optional embedding vector
    """
    chunk_id: str
    score: float
    metadata: Dict[str, Any]
    content: str
    vector: Optional[List[float]] = None


class BaseVectorStore(ABC):
    """
    Abstract base class for vector store implementations.
    
    All vector stores must implement these methods to be compatible
    with the storage and retrieval services.
    """
    
    @abstractmethod
    async def initialize(self, create_if_not_exists: bool = True) -> bool:
        """
        Initialize connection to vector store.
        
        Args:
            create_if_not_exists: Create index/collection if it doesn't exist
            
        Returns:
            Success status
        """
        pass
    
    @abstractmethod
    async def upsert_vectors(
        self,
        vectors: List[Dict[str, Any]],
        namespace: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Insert or update vectors in the store.
        
        Args:
            vectors: List of vector dictionaries with:
                - id: str - Unique identifier
                - values: List[float] - Embedding vector
                - metadata: Dict - Associated metadata
            namespace: Optional namespace for multi-tenancy
            
        Returns:
            Result dictionary with:
                - success: bool
                - count: int - Number of vectors upserted
                - error: Optional[str]
        """
        pass
    
    @abstractmethod
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
            filter: Metadata filter dictionary
            namespace: Optional namespace for multi-tenancy
            include_metadata: Include metadata in results
            include_values: Include vector values in results
            
        Returns:
            List of SearchResult objects
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def delete_namespace(self, namespace: str) -> bool:
        """
        Delete an entire namespace.
        
        Args:
            namespace: Namespace to delete
            
        Returns:
            Success status
        """
        pass
    
    @abstractmethod
    async def get_stats(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """
        Get vector store statistics.
        
        Args:
            namespace: Optional namespace to get stats for
            
        Returns:
            Statistics dictionary with:
                - total_vectors: int
                - dimensions: int
                - namespaces: Dict (if applicable)
        """
        pass
    
    async def update_metadata(
        self,
        id: str,
        metadata: Dict[str, Any],
        namespace: Optional[str] = None
    ) -> bool:
        """
        Update metadata for a vector (optional implementation).
        
        Args:
            id: Vector ID
            metadata: New metadata
            namespace: Optional namespace
            
        Returns:
            Success status
        """
        # Default implementation: not supported
        return False
    
    async def delete_document(
        self,
        document_id: str,
        namespace: Optional[str] = None
    ) -> bool:
        """
        Delete all vectors for a document.
        
        Args:
            document_id: Document ID
            namespace: Optional namespace
            
        Returns:
            Success status
        """
        # Default implementation using metadata filter
        try:
            # This is a helper method that can be overridden
            # Most vector stores support deletion by metadata filter
            return await self.delete_by_filter(
                filter={'document_id': document_id},
                namespace=namespace
            )
        except NotImplementedError:
            return False
    
    async def delete_by_filter(
        self,
        filter: Dict[str, Any],
        namespace: Optional[str] = None
    ) -> bool:
        """
        Delete vectors matching a filter (optional implementation).
        
        Args:
            filter: Metadata filter
            namespace: Optional namespace
            
        Returns:
            Success status
        """
        raise NotImplementedError("delete_by_filter not supported by this vector store")
