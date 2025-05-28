"""
RAG (Retrieval Augmented Generation) Package

This package contains the components for implementing RAG functionality:
- embeddings: Handling vector embeddings generation
- retrieval: Managing document retrieval from vector stores
- generation: Text generation based on retrieved documents
- models: Model loading and management
- llm_providers: LLM integration with different providers
"""

from rag.embeddings import generate_embeddings, batch_generate_embeddings, get_model
from rag.retrieval import (
    retrieve_documents, 
    retrieve_case_chunks, 
    retrieve_with_reranking, 
    retrieve_case_chunks_with_reranking,
    rerank_documents
)
from rag.generation import generate_response, generate_insights, generate_arguments, generate_with_reasoning_steps
from rag.models import load_llm_model, get_model as get_rag_model, init_models
from rag.llm_providers import get_llm_provider

__all__ = [
    # Embeddings
    'generate_embeddings',
    'batch_generate_embeddings',
    
    # Retrieval
    'retrieve_documents',
    'retrieve_case_chunks',
    'retrieve_with_reranking',
    'retrieve_case_chunks_with_reranking',
    'rerank_documents',
    
    # Generation
    'generate_response',
    'generate_insights',
    'generate_arguments',
    'generate_with_reasoning_steps',
    
    # LLM Providers
    'get_llm_provider',
]

def initialize_rag():
    """
    Initialize all RAG components.
    """
    # Import settings here to avoid circular imports
    import os
    from app.config import settings
    import logging
    logger = logging.getLogger(__name__)
    
    # Pre-load the embedding model
    embedding_model = get_model()
    
    # Initialize other models
    init_models()
    
    # Test LLM providers if in debug mode
    if settings.DEBUG:
        try:
            # Test OpenAI provider
            if settings.OPENAI_API_KEY:
                from rag.llm_providers import OpenAIProvider
                OpenAIProvider()
                logger.info("Successfully initialized OpenAI provider")
                
            # Test DeepSeek provider
            if settings.DEEPSEEK_API_KEY:
                from rag.llm_providers import DeepSeekProvider
                DeepSeekProvider()
                logger.info("Successfully initialized DeepSeek provider")
        except Exception as e:
            logger.warning(f"Error testing LLM providers: {e}")
    
    # Log initialization status
    logger.info("RAG components initialized successfully")
