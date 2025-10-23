"""
Integration test for the text extraction service with RAG pipeline.

This script demonstrates how to integrate the text extraction service with a RAG pipeline:
1. Extract text from documents
2. Process the text for RAG
3. Simulate chunking and embedding
4. Demonstrate retrieval
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path to import the modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from rag_service.services.extraction import DocumentProcessor, create_document_processor


class SimpleChunker:
    """Simple text chunker for demonstration purposes."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the chunker.
        
        Args:
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks.
        
        Args:
            text: Text to split into chunks
            
        Returns:
            List of dictionaries containing chunk text and metadata
        """
        if not text:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            # Calculate end position
            end = min(start + self.chunk_size, len(text))
            
            # Find a good break point (end of sentence or paragraph)
            if end < len(text):
                # Try to find sentence end
                for break_char in ['. ', '! ', '? ', '\n\n']:
                    last_break = text.rfind(break_char, start, end)
                    if last_break != -1:
                        end = last_break + len(break_char)
                        break
            
            # Create chunk
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "text": chunk_text,
                    "start": start,
                    "end": end,
                    "length": len(chunk_text)
                })
            
            # Move start position for next chunk
            start = end - self.chunk_overlap if end < len(text) else len(text)
        
        return chunks


class MockEmbedder:
    """Mock embedder for demonstration purposes."""
    
    def embed_text(self, text: str) -> List[float]:
        """
        Create a mock embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding
        """
        # This is just a mock - in a real system, you would use a proper embedding model
        import hashlib
        
        # Create a deterministic "embedding" based on text hash
        hash_obj = hashlib.md5(text.encode('utf-8'))
        hash_bytes = hash_obj.digest()
        
        # Convert hash bytes to a list of floats between -1 and 1
        embedding = [(b / 128.0) - 1.0 for b in hash_bytes]
        
        # Pad to 16 dimensions
        while len(embedding) < 16:
            embedding.append(0.0)
        
        return embedding[:16]  # Return 16-dimensional embedding


class SimpleRAGPipeline:
    """Simple RAG pipeline for demonstration purposes."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the RAG pipeline.
        
        Args:
            chunk_size: Maximum size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.document_processor = create_document_processor()
        self.chunker = SimpleChunker(chunk_size, chunk_overlap)
        self.embedder = MockEmbedder()
        self.document_store = {}  # Simple in-memory document store
        self.chunk_store = []  # Simple in-memory chunk store
    
    def process_document(self, file_path: str) -> str:
        """
        Process a document and add it to the document store.
        
        Args:
            file_path: Path to the document to process
            
        Returns:
            Document ID
        """
        logger.info(f"Processing document: {file_path}")
        
        # Extract text
        rag_result = self.document_processor.extract_text_for_rag(file_path)
        
        # Generate document ID
        import uuid
        doc_id = str(uuid.uuid4())
        
        # Store document
        self.document_store[doc_id] = {
            "document_id": doc_id,
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "metadata": rag_result["metadata"],
            "text": rag_result["text"]
        }
        
        # Chunk document
        chunks = self.chunker.chunk_text(rag_result["text"])
        
        # Embed and store chunks
        for i, chunk in enumerate(chunks):
            embedding = self.embedder.embed_text(chunk["text"])
            
            self.chunk_store.append({
                "chunk_id": f"{doc_id}_{i}",
                "document_id": doc_id,
                "text": chunk["text"],
                "embedding": embedding,
                "metadata": {
                    "start": chunk["start"],
                    "end": chunk["end"],
                    "length": chunk["length"],
                    "file_name": os.path.basename(file_path)
                }
            })
        
        logger.info(f"Document processed: {doc_id} with {len(chunks)} chunks")
        return doc_id
    
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks for a query.
        
        Args:
            query: Query text
            top_k: Number of chunks to retrieve
            
        Returns:
            List of relevant chunks
        """
        logger.info(f"Retrieving for query: {query}")
        
        # Embed query
        query_embedding = self.embedder.embed_text(query)
        
        # Calculate similarity with all chunks (cosine similarity)
        results = []
        for chunk in self.chunk_store:
            similarity = self._cosine_similarity(query_embedding, chunk["embedding"])
            results.append({
                "chunk_id": chunk["chunk_id"],
                "document_id": chunk["document_id"],
                "text": chunk["text"],
                "similarity": similarity,
                "metadata": chunk["metadata"]
            })
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Return top-k results
        return results[:top_k]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First vector
            vec2: Second vector
            
        Returns:
            Cosine similarity
        """
        import math
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0
        
        return dot_product / (norm1 * norm2)


def main():
    """Main function to demonstrate the RAG pipeline."""
    if len(sys.argv) < 2:
        print("Usage: python integration_test.py <file_or_directory_path>")
        sys.exit(1)
    
    path = sys.argv[1]
    
    # Create RAG pipeline
    rag_pipeline = SimpleRAGPipeline(chunk_size=1000, chunk_overlap=200)
    
    # Process document(s)
    if os.path.isfile(path):
        doc_id = rag_pipeline.process_document(path)
        print(f"\nProcessed document: {os.path.basename(path)} (ID: {doc_id})")
        
        # Demonstrate retrieval
        print("\n=== Retrieval Demo ===")
        queries = [
            "What is this document about?",
            "What are the main topics discussed?",
            "Can you summarize the key points?"
        ]
        
        for query in queries:
            print(f"\nQuery: {query}")
            results = rag_pipeline.retrieve(query, top_k=2)
            
            print(f"Top {len(results)} results:")
            for i, result in enumerate(results):
                print(f"\n{i+1}. Similarity: {result['similarity']:.4f}")
                print(f"   Document: {result['metadata']['file_name']}")
                print(f"   Text: {result['text'][:200]}...")
        
    elif os.path.isdir(path):
        # Process all files in directory
        processed_docs = []
        for root, _, files in os.walk(path):
            for file in files:
                if file.lower().endswith(('.pdf', '.docx', '.txt', '.md', '.csv')):
                    file_path = os.path.join(root, file)
                    try:
                        doc_id = rag_pipeline.process_document(file_path)
                        processed_docs.append((doc_id, file))
                    except Exception as e:
                        logger.error(f"Error processing {file}: {str(e)}")
        
        print(f"\nProcessed {len(processed_docs)} documents:")
        for doc_id, file in processed_docs:
            print(f"- {file} (ID: {doc_id})")
        
        # Demonstrate retrieval
        if processed_docs:
            print("\n=== Retrieval Demo ===")
            query = "What are these documents about?"
            print(f"\nQuery: {query}")
            results = rag_pipeline.retrieve(query, top_k=5)
            
            print(f"Top {len(results)} results:")
            for i, result in enumerate(results):
                print(f"\n{i+1}. Similarity: {result['similarity']:.4f}")
                print(f"   Document: {result['metadata']['file_name']}")
                print(f"   Text: {result['text'][:200]}...")
    
    else:
        print(f"Error: {path} is not a valid file or directory")
        sys.exit(1)


if __name__ == "__main__":
    main()
