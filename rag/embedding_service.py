#!/usr/bin/env python3
"""
Embedding service for generating semantic vectors from text.
Uses sentence-transformers for high-quality embeddings.
"""

import logging
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for generating text embeddings using sentence-transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding service with specified model.
        
        Args:
            model_name: HuggingFace model name. Default is compact 384-dim model.
        """
        self.model_name = model_name
        self.model = None
        self.dimension = None
        
    def load_model(self):
        """Load the embedding model."""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            
            # Get embedding dimension
            test_embedding = self.model.encode("test")
            self.dimension = len(test_embedding)
            
            logger.info(f"✅ Embedding model loaded successfully")
            logger.info(f"📏 Embedding dimension: {self.dimension}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            return False
    
    def encode(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for text(s).
        
        Args:
            texts: Single text string or list of text strings
            batch_size: Batch size for processing multiple texts
            
        Returns:
            numpy array of embeddings
        """
        if self.model is None:
            if not self.load_model():
                raise RuntimeError("Embedding model not loaded")
        
        try:
            # Ensure texts is a list
            if isinstance(texts, str):
                texts = [texts]
            
            # Generate embeddings
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 10,
                convert_to_numpy=True
            )
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def encode_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a single query.
        
        Args:
            query: Query text
            
        Returns:
            1D numpy array embedding
        """
        embedding = self.encode(query)
        return embedding[0] if len(embedding.shape) > 1 else embedding
    
    def encode_documents(self, documents: List[str]) -> np.ndarray:
        """
        Generate embeddings for multiple documents.
        
        Args:
            documents: List of document texts
            
        Returns:
            2D numpy array of embeddings (one per document)
        """
        return self.encode(documents)
    
    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (-1 to 1)
        """
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        # Calculate cosine similarity
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        return float(similarity)
    
    def get_dimension(self) -> int:
        """Get the embedding dimension."""
        if self.dimension is None:
            if self.model is None:
                self.load_model()
            # Dimension should be set during model loading
        return self.dimension


# Global embedding service instance
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """Get the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
        _embedding_service.load_model()
    return _embedding_service


def main():
    """Test the embedding service."""
    print("Testing Embedding Service...")
    
    # Initialize service
    service = EmbeddingService()
    if not service.load_model():
        print("❌ Failed to load model")
        return
    
    # Test single text
    test_text = "What is parliamentary procedure?"
    embedding = service.encode_query(test_text)
    print(f"[OK] Single text embedding shape: {embedding.shape}")
    print(f"[OK] Embedding dimension: {service.get_dimension()}")
    
    # Test multiple texts
    test_texts = [
        "Parliamentary procedures and rules",
        "Minister announces new policy",
        "Opposition asks questions about budget"
    ]
    
    embeddings = service.encode_documents(test_texts)
    print(f"[OK] Multiple texts embedding shape: {embeddings.shape}")
    
    # Test similarity
    sim = service.similarity(embeddings[0], embeddings[1])
    print(f"[OK] Similarity between texts 0 and 1: {sim:.3f}")
    
    print("[SUCCESS] Embedding service test completed!")


if __name__ == "__main__":
    main()