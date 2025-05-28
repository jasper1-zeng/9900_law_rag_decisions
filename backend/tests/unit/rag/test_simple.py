"""
A simple test to verify the testing environment and RAG modules.
"""
import pytest
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import numpy as np

# Make sure the path is set up correctly
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import modules directly
import rag.embeddings
import rag.retrieval
import rag.generation

def test_simple():
    """A simple test that always passes."""
    assert True


class TestRagModules(unittest.TestCase):
    """Test basic functionality of RAG modules."""
    
    def test_embeddings_module(self):
        """Test that we can use the embeddings module."""
        # Store original functions
        original_get_model = rag.embeddings.get_model
        
        try:
            # Setup mock
            mock_model = MagicMock()
            mock_model.encode.return_value = np.array([0.1] * 768)
            rag.embeddings.get_model = lambda: mock_model
            
            # Execute
            embedding = rag.embeddings.generate_embeddings("Test query")
            
            # Assert
            self.assertEqual(len(embedding), 768)
            mock_model.encode.assert_called()
        finally:
            # Restore original
            rag.embeddings.get_model = original_get_model
    
    def test_retrieval_module(self):
        """Test that we can use the retrieval module."""
        # Store original functions
        original_app_engine = rag.retrieval.app_engine
        
        try:
            # Setup mock
            mock_engine = MagicMock()
            mock_conn = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.return_value.fetchall.return_value = []
            
            # Replace the engine
            rag.retrieval.app_engine = mock_engine
            
            # Execute
            documents = rag.retrieval.retrieve_documents([0.1] * 768, limit=5)
            
            # Assert
            self.assertIsInstance(documents, list)
            mock_conn.execute.assert_called()
        finally:
            # Restore original
            rag.retrieval.app_engine = original_app_engine
    
    def test_generation_module(self):
        """Test that we can use the generation module."""
        # Store original functions
        original_get_llm_provider = rag.generation.get_llm_provider
        original_generate_hybrid_prompt = None
        
        try:
            # Mock the query_classifier function
            if hasattr(rag.generation, 'generate_hybrid_prompt'):
                original_generate_hybrid_prompt = rag.generation.generate_hybrid_prompt
                mock_hybrid_prompt = MagicMock(return_value={
                    "prompt": "Test prompt",
                    "classification": {"type": "legal", "confidence": 0.95}
                })
                rag.generation.generate_hybrid_prompt = mock_hybrid_prompt
            
            # Setup the LLM provider mock - handle for_chat parameter
            mock_llm = MagicMock()
            mock_llm.generate.return_value = "Test response"
            
            # Use a proper function to handle the for_chat argument
            def mock_get_llm_provider(provider=None, model=None, for_chat=True):
                return mock_llm
                
            rag.generation.get_llm_provider = mock_get_llm_provider
            
            # Create a simple test document with required fields
            test_doc = {
                "case_title": "Test case", 
                "similarity": 0.9, 
                "reasons_summary": "Test summary",
                "citation_number": "2023 TEST 123",
                "case_url": "https://example.com/test"
            }
            
            # Execute
            response = rag.generation.generate_response(
                "Test query", 
                [test_doc]
            )
            
            # Assert
            self.assertEqual(response, "Test response")
            mock_llm.generate.assert_called()
        finally:
            # Restore originals
            rag.generation.get_llm_provider = original_get_llm_provider
            if original_generate_hybrid_prompt is not None:
                rag.generation.generate_hybrid_prompt = original_generate_hybrid_prompt 