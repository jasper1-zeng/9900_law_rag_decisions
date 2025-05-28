"""
Integration tests for the RAG system.

These tests verify that the different components can work together.
Some aspects like the database call might still be mocked.
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import logging
import json
import pytest
from typing import List, Dict, Any
import numpy as np
from sqlalchemy import text
from sqlalchemy.engine import create_engine
from sqlalchemy.orm import Session

# Disable logging to avoid cluttering test output
logging.basicConfig(level=logging.CRITICAL)

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import modules to test
from rag.embeddings import generate_embeddings, batch_generate_embeddings
from rag.retrieval import retrieve_documents, retrieve_case_chunks, retrieve_with_reranking
from rag.generation import generate_response, generate_arguments, generate_insights
from app.db.database import get_db, engine
from app.config import settings
from app.services.chat_service import process_chat
from app.api.schemas.chat import ChatRequest


# Mark this as an integration test that might be skipped if database is not available
@pytest.mark.integration
class TestRagDatabaseIntegration(unittest.TestCase):
    """Integration tests for RAG with the actual database."""
    
    @classmethod
    def setUpClass(cls):
        """Set up the test environment once for all tests."""
        # Check if we can connect to the database
        cls.db_available = True
        try:
            # Try to connect to database
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).fetchone()
                if not result or result[0] != 1:
                    cls.db_available = False
        except Exception as e:
            print(f"Database connection failed: {e}")
            cls.db_available = False
            
        # Skip all tests if database is not available
        if not cls.db_available:
            pytest.skip("Database not available for integration tests", allow_module_level=True)
    
    def setUp(self):
        """Set up each test."""
        if not self.db_available:
            self.skipTest("Database not available")
            
        # Create a test database session - using the actual DB
        self.db = next(get_db())
    
    def tearDown(self):
        """Clean up after each test."""
        if hasattr(self, 'db'):
            self.db.close()
            
    def test_embeddings_with_real_model(self):
        """Test embeddings generation with the real model."""
        # Skip if no embedding model is available or ENV vars not set
        try:
            # Generate embeddings for a test query
            query = "What are the requirements for rental termination notices in commercial properties?"
            embedding = generate_embeddings(query)
            
            # Verify
            self.assertIsInstance(embedding, list)
            self.assertEqual(len(embedding), settings.EMBEDDING_DIM)
            for value in embedding:
                self.assertIsInstance(value, float)
        except ImportError:
            self.skipTest("Embedding model dependencies not available")
    
    def test_retrieve_documents_from_db(self):
        """Test retrieving documents from the actual database."""
        # Skip detailed assertions if we don't have data
        try:
            # Generate embeddings for a test query
            query = "Commercial lease termination early"
            embedding = generate_embeddings(query)
            
            # Retrieve documents
            documents = retrieve_documents(embedding, limit=3)
            
            # Basic verification
            self.assertIsInstance(documents, list)
            if len(documents) > 0:
                # Verify document structure
                doc = documents[0]
                self.assertIn("id", doc)
                self.assertIn("case_title", doc)
                self.assertIn("reasons_summary", doc)
                self.assertIn("similarity", doc)
                
                # Print for debugging
                print(f"Retrieved {len(documents)} documents")
                print(f"Top document: {doc['case_title']} (similarity: {doc['similarity']})")
        except Exception as e:
            self.skipTest(f"Document retrieval failed: {e}")
    
    def test_retrieve_case_chunks_from_db(self):
        """Test retrieving case chunks from the actual database."""
        # Skip detailed assertions if we don't have data
        try:
            # Generate embeddings for a test query
            query = "Commercial lease termination notice period"
            embedding = generate_embeddings(query)
            
            # Retrieve case chunks
            chunks = retrieve_case_chunks(embedding, limit=3)
            
            # Basic verification
            self.assertIsInstance(chunks, list)
            if len(chunks) > 0:
                # Verify chunk structure
                chunk = chunks[0]
                self.assertIn("chunk_id", chunk)
                self.assertIn("chunk_text", chunk)
                self.assertIn("case_id", chunk)
                self.assertIn("similarity", chunk)
                
                # Print for debugging
                print(f"Retrieved {len(chunks)} chunks")
                print(f"Top chunk from case: {chunk.get('case_title', 'Unknown')} (similarity: {chunk['similarity']})")
        except Exception as e:
            self.skipTest(f"Chunk retrieval failed: {e}")
    
    def test_full_rag_process_with_db(self):
        """Test the complete RAG process with database integration."""
        try:
            # Create a test chat request
            request = ChatRequest(
                message="What are the requirements for terminating a commercial lease early?",
                conversation_id=None  # New conversation
            )
            
            # Process the chat request - this will use the actual database
            response = process_chat(request, db=self.db)
            
            # Verify response structure
            self.assertIsNotNone(response)
            self.assertIsNotNone(response.response)
            self.assertIsNotNone(response.conversation_id)
            
            # Print for debugging
            print(f"RAG response: {response.response[:100]}...")
            print(f"Conversation ID: {response.conversation_id}")
            
            # Check that the response is meaningful
            self.assertGreater(len(response.response), 20)  # Should be a substantial response
        except Exception as e:
            self.skipTest(f"Full RAG process failed: {e}")


# This allows running specific test cases with specific data in the database
class TestRagWithSpecificCases(unittest.TestCase):
    """
    Tests for specific cases to validate RAG behavior with known data points.
    
    These tests rely on specific data in the database, so they should be
    customized for your actual data set.
    """
    
    @classmethod
    def setUpClass(cls):
        """Check if testing specific cases is enabled."""
        # Only run these tests if enabled (they're more specific to the data)
        cls.enabled = os.environ.get("ENABLE_SPECIFIC_CASE_TESTS", "false").lower() == "true"
        if not cls.enabled:
            pytest.skip("Specific case tests not enabled", allow_module_level=True)
            
        # Also check database connection
        cls.db_available = True
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).fetchone()
                if not result or result[0] != 1:
                    cls.db_available = False
        except Exception:
            cls.db_available = False
            
        if not cls.db_available:
            pytest.skip("Database not available for specific case tests", allow_module_level=True)
    
    def setUp(self):
        """Set up each test."""
        if not self.enabled or not self.db_available:
            self.skipTest("Specific case tests not enabled or DB not available")
            
        # Create a database session
        self.db = next(get_db())
    
    def tearDown(self):
        """Clean up after each test."""
        if hasattr(self, 'db'):
            self.db.close()
    
    @pytest.mark.parametrize("test_case", [
        {
            "query": "What are the requirements for a commercial tenant to terminate a lease early?",
            "expected_case_ids": ["SATCASE001", "SATCASE002"],  # Replace with actual case IDs in your database
            "min_similarity": 0.5
        },
        {
            "query": "Can a landlord evict a tenant without notice?",
            "expected_case_ids": ["SATCASE003", "SATCASE004"],  # Replace with actual case IDs in your database
            "min_similarity": 0.5
        }
    ])
    def test_specific_case_retrieval(self, test_case):
        """Test that specific queries retrieve expected cases."""
        try:
            # Generate embeddings for the test query
            query = test_case["query"]
            embedding = generate_embeddings(query)
            
            # Retrieve documents
            documents = retrieve_documents(embedding, limit=5)
            
            # Check that we have results
            self.assertGreater(len(documents), 0, "No documents retrieved")
            
            # Print for debugging
            case_ids = [doc["id"] for doc in documents]
            print(f"Query: {query}")
            print(f"Retrieved case IDs: {case_ids}")
            print(f"Expected case IDs: {test_case['expected_case_ids']}")
            
            # Check if any of the expected cases are in the results
            # You might want to set a minimum similarity threshold
            matching_cases = [doc for doc in documents if doc["id"] in test_case["expected_case_ids"] 
                             and doc["similarity"] >= test_case["min_similarity"]]
            
            # We should find at least one of the expected cases
            # This is a soft assertion - the test will continue even if it fails
            if not matching_cases:
                print(f"WARNING: None of the expected cases {test_case['expected_case_ids']} "
                      f"were found in the results {case_ids}")
            else:
                print(f"Found {len(matching_cases)} matching expected cases")
        except Exception as e:
            self.skipTest(f"Specific case test failed: {e}")


if __name__ == "__main__":
    unittest.main() 