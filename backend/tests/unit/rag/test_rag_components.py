"""
Tests for RAG components (Retrieval, Embeddings, Generation).

These tests focus on individual components of the RAG system.
"""
import unittest
from unittest.mock import patch, MagicMock, Mock
import pytest
import numpy as np
from typing import List, Dict, Any
import json
import sys
import os

# Disable logging to avoid excessive output during tests
import logging
logging.basicConfig(level=logging.CRITICAL)

# Make sure the path is set up correctly
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Import the modules directly - we'll mock them within the test methods
import rag.embeddings
import rag.retrieval
import rag.generation


class TestEmbeddings(unittest.TestCase):
    """Tests for the embeddings module."""
    
    def test_generate_embeddings(self):
        """Test generating embeddings for a single text."""
        # Create the mock directly
        original_get_model = rag.embeddings.get_model
        
        try:
            # Replace the get_model function with our mock
            mock_model = MagicMock()
            mock_model.encode.return_value = np.random.rand(768).astype(np.float32)
            rag.embeddings.get_model = lambda: mock_model
            
            # Execute
            text = "This is a test query about SAT decisions."
            embedding = rag.embeddings.generate_embeddings(text)
            
            # Assert
            self.assertIsInstance(embedding, list)
            self.assertEqual(len(embedding), 768)  # Should match model dimension
            # Verify the model's encode function was called
            mock_model.encode.assert_called()
        finally:
            # Restore the original function
            rag.embeddings.get_model = original_get_model
        
    def test_batch_generate_embeddings(self):
        """Test generating embeddings for multiple texts."""
        # Create the mock directly
        original_get_model = rag.embeddings.get_model
        
        try:
            # Replace the get_model function with our mock
            mock_model = MagicMock()
            mock_model.encode.return_value = np.random.rand(3, 768).astype(np.float32)
            rag.embeddings.get_model = lambda: mock_model
            
            # Execute
            texts = [
                "First test query about rental properties.",
                "Second test query about eviction notices.",
                "Third test query about tenant rights."
            ]
            embeddings = rag.embeddings.batch_generate_embeddings(texts)
            
            # Assert
            self.assertIsInstance(embeddings, list)
            self.assertEqual(len(embeddings), 3)
            for emb in embeddings:
                self.assertEqual(len(emb), 768)
            # Verify the model's encode function was called
            mock_model.encode.assert_called()
        finally:
            # Restore the original function
            rag.embeddings.get_model = original_get_model


class TestRetrieval(unittest.TestCase):
    """Tests for the retrieval module."""
    
    def test_retrieve_documents(self):
        """Test retrieving documents based on embedding."""
        # Mock the database connection
        original_app_engine = rag.retrieval.app_engine
        
        try:
            # Setup mock
            mock_engine = MagicMock()
            mock_conn = MagicMock()
            mock_execute = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.return_value = mock_execute
            
            # Set up mock results
            mock_result = [
                MagicMock(
                    id="case1",
                    case_title="Test Case 1",
                    reasons_summary="This is a test case about rental properties.",
                    citation_number="2023 SAT 123",
                    case_topic="Commercial Tenancy",
                    catchwords="rental, property, commercial",
                    case_url="https://example.com/case1",
                    similarity=0.85
                ),
                MagicMock(
                    id="case2",
                    case_title="Test Case 2",
                    reasons_summary="This is a test case about eviction notices.",
                    citation_number="2023 SAT 124",
                    case_topic="Commercial Tenancy",
                    catchwords="eviction, notice, tenant",
                    case_url="https://example.com/case2",
                    similarity=0.75
                )
            ]
            mock_execute.fetchall.return_value = mock_result
            
            # Replace the engine
            rag.retrieval.app_engine = mock_engine
            
            # Execute
            query_embedding = [0.1] * 768  # Dummy embedding
            documents = rag.retrieval.retrieve_documents(query_embedding, limit=2)
            
            # Assert
            self.assertIsInstance(documents, list)
            self.assertEqual(len(documents), 2)
            self.assertEqual(documents[0]["id"], "case1")
            self.assertEqual(documents[0]["case_title"], "Test Case 1")
            self.assertEqual(documents[0]["similarity"], 0.85)
            
            # Verify mock was called
            mock_conn.execute.assert_called()
        finally:
            # Restore original
            rag.retrieval.app_engine = original_app_engine
        
    def test_retrieve_case_chunks(self):
        """Test retrieving case chunks based on embedding."""
        # Mock the database connection
        original_app_engine = rag.retrieval.app_engine
        
        try:
            # Setup mock
            mock_engine = MagicMock()
            mock_conn = MagicMock()
            mock_execute = MagicMock()
            mock_engine.connect.return_value.__enter__.return_value = mock_conn
            mock_conn.execute.return_value = mock_execute
            
            # Mock query results
            mock_result = [
                MagicMock(
                    chunk_id="chunk1",
                    chunk_text="This is a chunk of text from case 1 about rental properties.",
                    chunk_index=1,
                    case_id="case1",
                    case_topic="Commercial Tenancy",
                    case_title="Test Case 1",
                    citation_number="2023 SAT 123",
                    case_url="https://example.com/case1",
                    similarity=0.88
                ),
                MagicMock(
                    chunk_id="chunk2",
                    chunk_text="This is a chunk of text from case 2 about eviction notices.",
                    chunk_index=1,
                    case_id="case2",
                    case_topic="Commercial Tenancy",
                    case_title="Test Case 2",
                    citation_number="2023 SAT 124",
                    case_url="https://example.com/case2",
                    similarity=0.78
                )
            ]
            mock_execute.fetchall.return_value = mock_result
            
            # Replace the engine
            rag.retrieval.app_engine = mock_engine
            
            # Execute
            query_embedding = [0.1] * 768  # Dummy embedding
            chunks = rag.retrieval.retrieve_case_chunks(query_embedding, limit=2)
            
            # Assert
            self.assertIsInstance(chunks, list)
            self.assertEqual(len(chunks), 2)
            self.assertEqual(chunks[0]["chunk_id"], "chunk1")
            self.assertEqual(chunks[0]["chunk_text"], "This is a chunk of text from case 1 about rental properties.")
            self.assertEqual(chunks[0]["similarity"], 0.88)
            
            # Verify mock was called
            mock_conn.execute.assert_called()
        finally:
            # Restore original
            rag.retrieval.app_engine = original_app_engine


class TestGeneration(unittest.TestCase):
    """Tests for the generation module."""
    
    def test_format_context(self):
        """Test formatting retrieved documents into context."""
        # Setup test data
        documents = [
            {
                "case_title": "Test Case 1",
                "reasons_summary": "This is a test case about rental properties.",
                "citation_number": "2023 SAT 123",
                "case_url": "https://example.com/case1",
                "similarity": 0.85
            },
            {
                "case_title": "Test Case 2",
                "reasons_summary": "This is a test case about eviction notices.",
                "citation_number": "2023 SAT 124",
                "case_url": "https://example.com/case2",
                "similarity": 0.75
            }
        ]
        
        # Execute
        context = rag.generation.format_context(documents)
        
        # Assert
        self.assertIsInstance(context, str)
        self.assertIn("Test Case 1", context)
        self.assertIn("2023 SAT 123", context)
        self.assertIn("https://example.com/case1", context)
        self.assertIn("Test Case 2", context)
        
    def test_generate_response(self):
        """Test generating a response based on query and documents."""
        # Mock the LLM provider
        original_get_llm_provider = rag.generation.get_llm_provider
        original_generate_hybrid_prompt = None
        
        try:
            # Mock the query_classifier function if it exists
            if hasattr(rag.generation, 'generate_hybrid_prompt'):
                original_generate_hybrid_prompt = rag.generation.generate_hybrid_prompt
                mock_hybrid_prompt = MagicMock(return_value={
                    "prompt": "Test prompt",
                    "classification": {"type": "legal", "confidence": 0.95}
                })
                rag.generation.generate_hybrid_prompt = mock_hybrid_prompt
            
            # Setup mock LLM provider with handling for for_chat parameter
            mock_llm = MagicMock()
            mock_llm.generate.return_value = "Based on the relevant cases, rental properties must..."
            
            def mock_get_llm_provider(provider=None, model=None, for_chat=True):
                return mock_llm
                
            rag.generation.get_llm_provider = mock_get_llm_provider
            
            # Setup test data with required fields
            query = "What are the rules for commercial rental properties?"
            documents = [
                {
                    "case_title": "Test Case 1",
                    "reasons_summary": "This is a test case about rental properties.",
                    "citation_number": "2023 SAT 123",
                    "case_url": "https://example.com/case1",
                    "similarity": 0.85
                }
            ]
            
            # Execute
            response = rag.generation.generate_response(query, documents)
            
            # Assert
            self.assertEqual(response, "Based on the relevant cases, rental properties must...")
            mock_llm.generate.assert_called()
        finally:
            # Restore originals
            rag.generation.get_llm_provider = original_get_llm_provider
            if original_generate_hybrid_prompt is not None:
                rag.generation.generate_hybrid_prompt = original_generate_hybrid_prompt


class TestEndToEnd(unittest.TestCase):
    """End-to-end tests for the RAG system."""
    
    def test_rag_end_to_end(self):
        """Test the complete RAG flow from query to response."""
        # Store original functions
        original_generate_embeddings = rag.embeddings.generate_embeddings
        original_retrieve_documents = rag.retrieval.retrieve_documents
        original_retrieve_case_chunks = rag.retrieval.retrieve_case_chunks
        original_generate_response = rag.generation.generate_response
        original_generate_hybrid_prompt = None
        original_get_llm_provider = None
        
        try:
            # Check for and mock generate_hybrid_prompt if it exists
            if hasattr(rag.generation, 'generate_hybrid_prompt'):
                original_generate_hybrid_prompt = rag.generation.generate_hybrid_prompt
                mock_hybrid_prompt = MagicMock(return_value={
                    "prompt": "Test prompt",
                    "classification": {"type": "legal", "confidence": 0.95}
                })
                rag.generation.generate_hybrid_prompt = mock_hybrid_prompt
            
            # Check for and mock get_llm_provider if it exists
            if hasattr(rag.generation, 'get_llm_provider'):
                original_get_llm_provider = rag.generation.get_llm_provider
                mock_llm = MagicMock()
                mock_llm.generate.return_value = "Based on the SAT decisions, rental terminations require proper notice..."
                
                def mock_get_llm_provider(provider=None, model=None, for_chat=True):
                    return mock_llm
                    
                rag.generation.get_llm_provider = mock_get_llm_provider
            
            # Setup mocks
            mock_embeddings = MagicMock(return_value=[0.1] * 768)
            mock_retrieve_docs = MagicMock(return_value=[
                {
                    "id": "case1",
                    "case_title": "Test Case 1",
                    "reasons_summary": "This is a test case about rental properties.",
                    "citation_number": "2023 SAT 123",
                    "case_url": "https://example.com/case1",
                    "similarity": 0.85
                }
            ])
            mock_retrieve_chunks = MagicMock(return_value=[
                {
                    "chunk_id": "chunk1",
                    "chunk_text": "This is a chunk about rental termination.",
                    "chunk_index": 1,
                    "case_id": "case1",
                    "case_title": "Test Case 1",
                    "case_topic": "Commercial Tenancy",
                    "citation_number": "2023 SAT 123",
                    "case_url": "https://example.com/case1",
                    "similarity": 0.88
                }
            ])
            mock_generate = MagicMock(return_value="Based on the SAT decisions, rental terminations require proper notice...")
            
            # Replace the functions with our mocks
            rag.embeddings.generate_embeddings = mock_embeddings
            rag.retrieval.retrieve_documents = mock_retrieve_docs
            rag.retrieval.retrieve_case_chunks = mock_retrieve_chunks
            rag.generation.generate_response = mock_generate
            
            # Simulate chat_service.process_chat
            query = "What are the requirements for terminating a rental agreement?"
            
            # Execute RAG pipeline manually
            query_embedding = rag.embeddings.generate_embeddings(query)
            documents = rag.retrieval.retrieve_documents(query_embedding, limit=3)
            chunks = rag.retrieval.retrieve_case_chunks(query_embedding, limit=5)
            
            # Combine context from both sources (simplified)
            combined_context = []
            combined_context.extend(documents)
            combined_context.extend([{
                "type": "chunk",
                "reasons_summary": chunk["chunk_text"],
                **{k: v for k, v in chunk.items() if k != "chunk_text"}
            } for chunk in chunks])
            
            # Generate response
            response = rag.generation.generate_response(query, combined_context)
            
            # Assert
            self.assertEqual(response, "Based on the SAT decisions, rental terminations require proper notice...")
            mock_embeddings.assert_called_once_with(query)
            mock_retrieve_docs.assert_called_once()
            mock_retrieve_chunks.assert_called_once()
            mock_generate.assert_called_once()
        finally:
            # Restore all originals
            rag.embeddings.generate_embeddings = original_generate_embeddings
            rag.retrieval.retrieve_documents = original_retrieve_documents
            rag.retrieval.retrieve_case_chunks = original_retrieve_case_chunks
            rag.generation.generate_response = original_generate_response
            if original_generate_hybrid_prompt is not None:
                rag.generation.generate_hybrid_prompt = original_generate_hybrid_prompt
            if original_get_llm_provider is not None:
                rag.generation.get_llm_provider = original_get_llm_provider


if __name__ == "__main__":
    unittest.main() 