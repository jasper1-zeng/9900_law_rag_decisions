"""
RAG Embeddings Module

This module handles the creation and management of vector embeddings.
"""
from typing import List, Union
import numpy as np
import logging
from app.config import settings

logger = logging.getLogger(__name__)

# Dictionary to store the loaded model (singleton pattern)
_model = None

def get_model():
    """
    Get or initialize the embedding model (singleton pattern).
    
    Returns:
        The embedding model instance
    """
    global _model
    if _model is not None:
        return _model
    
    model_name = settings.EMBEDDING_MODEL

    # Handle e5-base-v2 and other model variants
    if model_name == "e5-base-v2":
        model_path = "intfloat/e5-base-v2"
    else:
        model_path = model_name
        
    logger.info(f"Loading model: {model_path}")
    
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(model_path)
        
        # Wrap original model to handle e5 model prefix requirements
        original_encode = _model.encode
        
        def wrapped_encode(texts, **kwargs):
            # Handle single text or list of texts
            is_single = not isinstance(texts, list)
            if is_single:
                texts = [texts]
                
            # Add the e5 prefix for queries, only for e5 model
            if "e5" in model_name.lower():
                texts = [f"query: {text}" if not text.startswith('query:') else text for text in texts]
                
            # Call the original encode method
            embeddings = original_encode(texts, **kwargs)
            
            # Return single result for single input
            if is_single:
                return embeddings[0]
            return embeddings
            
        _model.encode = wrapped_encode
        return _model
        
    except ImportError:
        logger.warning("SentenceTransformer not available.")
        raise
        


def generate_embeddings(text: str) -> List[float]:
    """
    Convert text to vector embeddings.
    
    Args:
        text: The text to convert to embeddings
        
    Returns:
        List[float]: The vector embedding
    """
    model = get_model()
    embedding = model.encode(text, convert_to_tensor=False)
    
    # Convert to list if numpy array
    if isinstance(embedding, np.ndarray):
        embedding = embedding.tolist()
    
    return embedding

def batch_generate_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Convert multiple texts to vector embeddings.
    
    Args:
        texts: The list of texts to convert to embeddings
        
    Returns:
        List[List[float]]: The vector embeddings
    """
    model = get_model()
    embeddings = model.encode(texts, convert_to_tensor=False)
    
    # Convert to list if numpy array
    if isinstance(embeddings, np.ndarray):
        embeddings = embeddings.tolist()
    
    return embeddings 