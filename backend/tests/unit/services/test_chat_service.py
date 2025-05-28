"""
Tests for the chat service that uses the RAG components.

This file contains tests for the chat service that integrates with the RAG system.
"""
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os
import pytest
import asyncio
import json
import numpy as np
import uuid

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Import the modules to test
from app.services.chat_service import process_chat
from app.api.schemas.chat import ChatRequest, ChatResponse
from app.db.conversation_repository import ConversationRepository


class TestChatService(unittest.TestCase):
    """Tests for the chat service."""
    
    @patch('app.services.chat_service.generate_embeddings')
    @patch('app.services.chat_service.retrieve_documents')
    @patch('app.services.chat_service.retrieve_case_chunks')
    @patch('app.services.chat_service.generate_response')
    @patch('app.services.chat_service.ConversationRepository')
    async def test_process_chat_new_conversation(
        self, mock_repo_class, mock_generate, mock_retrieve_chunks, 
        mock_retrieve_docs, mock_embeddings
    ):
        """Test processing a chat request for a new conversation."""
        # Setup mocks
        mock_embeddings.return_value = [0.1] * 768
        mock_retrieve_docs.return_value = [
            {
                "id": "case1",
                "case_title": "Test Case 1",
                "reasons_summary": "This is a test case about rental properties.",
                "citation_number": "2023 SAT 123",
                "case_url": "https://example.com/case1",
                "similarity": 0.85
            }
        ]
        mock_retrieve_chunks.return_value = [
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
        ]
        mock_generate.return_value = "Based on the SAT decisions, rental terminations require proper notice..."
        
        # Create a mock for the repository instance
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        
        # Mock repository methods
        mock_repo.create_conversation.return_value = MagicMock(id="test_conv_id")
        mock_repo.get_conversation_history.return_value = []
        
        # Create the request
        request = ChatRequest(
            message="What are the requirements for terminating a rental agreement?",
            conversation_id=None  # New conversation
        )
        
        # Execute
        response = await process_chat(request, db=MagicMock())
        
        # Assert
        self.assertIsInstance(response, ChatResponse)
        self.assertEqual(response.response, "Based on the SAT decisions, rental terminations require proper notice...")
        self.assertEqual(response.conversation_id, "test_conv_id")
        
        # Verify mocks were called correctly
        mock_embeddings.assert_called_once_with(request.message)
        mock_retrieve_docs.assert_called_once()
        mock_retrieve_chunks.assert_called_once()
        mock_generate.assert_called_once()
        mock_repo.create_conversation.assert_called_once()
        mock_repo.add_message.assert_called()
        
    @patch('app.services.chat_service.generate_embeddings')
    @patch('app.services.chat_service.retrieve_documents')
    @patch('app.services.chat_service.retrieve_case_chunks')
    @patch('app.services.chat_service.generate_response')
    @patch('app.services.chat_service.ConversationRepository')
    async def test_process_chat_existing_conversation(
        self, mock_repo_class, mock_generate, mock_retrieve_chunks, 
        mock_retrieve_docs, mock_embeddings
    ):
        """Test processing a chat request for an existing conversation."""
        # Setup mocks
        mock_embeddings.return_value = [0.1] * 768
        mock_retrieve_docs.return_value = [
            {
                "id": "case1",
                "case_title": "Test Case 1",
                "reasons_summary": "This is a test case about rental properties.",
                "citation_number": "2023 SAT 123",
                "case_url": "https://example.com/case1",
                "similarity": 0.85
            }
        ]
        mock_retrieve_chunks.return_value = [
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
        ]
        mock_generate.return_value = "Based on the SAT decisions, rental terminations require proper notice..."
        
        # Create a mock for the repository instance
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        
        # Mock repository methods
        mock_repo.get_conversation.return_value = MagicMock(id="existing_conv_id")
        mock_repo.get_conversation_history.return_value = [
            {"role": "user", "content": "Previous question about rentals"},
            {"role": "assistant", "content": "Previous answer about rentals"}
        ]
        
        # Create the request with existing conversation ID
        request = ChatRequest(
            message="What are the requirements for terminating a rental agreement?",
            conversation_id="existing_conv_id"
        )
        
        # Execute
        response = await process_chat(request, db=MagicMock())
        
        # Assert
        self.assertIsInstance(response, ChatResponse)
        self.assertEqual(response.response, "Based on the SAT decisions, rental terminations require proper notice...")
        self.assertEqual(response.conversation_id, "existing_conv_id")
        
        # Verify mocks were called correctly
        mock_repo.get_conversation.assert_called_once_with("existing_conv_id")
        mock_repo.get_conversation_history.assert_called_once()
        mock_repo.create_conversation.assert_not_called()  # Should not create new conversation
        
    @patch('app.services.chat_service.generate_embeddings')
    @patch('app.services.chat_service.retrieve_documents')
    @patch('app.services.chat_service.retrieve_case_chunks')
    @patch('app.services.chat_service.generate_response')
    async def test_process_chat_without_db(
        self, mock_generate, mock_retrieve_chunks, 
        mock_retrieve_docs, mock_embeddings
    ):
        """Test processing a chat request without database integration."""
        # Setup mocks
        mock_embeddings.return_value = [0.1] * 768
        mock_retrieve_docs.return_value = [
            {
                "id": "case1",
                "case_title": "Test Case 1",
                "reasons_summary": "This is a test case about rental properties.",
                "citation_number": "2023 SAT 123",
                "case_url": "https://example.com/case1",
                "similarity": 0.85
            }
        ]
        mock_retrieve_chunks.return_value = [
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
        ]
        mock_generate.return_value = "Based on the SAT decisions, rental terminations require proper notice..."
        
        # Create the request
        request = ChatRequest(
            message="What are the requirements for terminating a rental agreement?",
            conversation_id=None  # New conversation
        )
        
        # Execute - no db session provided
        response = await process_chat(request, db=None)
        
        # Assert
        self.assertIsInstance(response, ChatResponse)
        self.assertEqual(response.response, "Based on the SAT decisions, rental terminations require proper notice...")
        self.assertTrue(response.conversation_id.startswith("conv_"))  # Should generate random ID
        
    @patch('app.services.chat_service.generate_embeddings')
    @patch('app.services.chat_service.retrieve_documents')
    @patch('app.services.chat_service.retrieve_case_chunks')
    async def test_process_chat_error_handling(
        self, mock_retrieve_chunks, mock_retrieve_docs, mock_embeddings
    ):
        """Test error handling during chat processing."""
        # Setup mocks
        mock_embeddings.side_effect = Exception("Embedding error")
        
        # Create the request
        request = ChatRequest(
            message="What are the requirements for terminating a rental agreement?",
            conversation_id=None  # New conversation
        )
        
        # Execute
        response = await process_chat(request, db=None)
        
        # Assert
        self.assertIsInstance(response, ChatResponse)
        self.assertIn("I'm sorry, I encountered an error", response.response)
        self.assertTrue(response.conversation_id.startswith("conv_"))
        
    @patch('app.services.chat_service.generate_embeddings')
    @patch('app.services.chat_service.retrieve_documents')
    @patch('app.services.chat_service.retrieve_case_chunks')
    @patch('app.services.chat_service.generate_response')
    async def test_process_chat_streaming(
        self, mock_generate, mock_retrieve_chunks, 
        mock_retrieve_docs, mock_embeddings
    ):
        """Test processing a chat request with streaming response."""
        # Setup mocks
        mock_embeddings.return_value = [0.1] * 768
        mock_retrieve_docs.return_value = [
            {
                "id": "case1",
                "case_title": "Test Case 1",
                "reasons_summary": "This is a test case about rental properties.",
                "citation_number": "2023 SAT 123",
                "case_url": "https://example.com/case1",
                "similarity": 0.85
            }
        ]
        mock_retrieve_chunks.return_value = [
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
        ]
        
        # For streaming, we need to define what happens when generate_response is called with streaming_callback
        def fake_streaming(query, context, conversation_history=None, streaming_callback=None):
            if streaming_callback:
                streaming_callback("Based on ")
                streaming_callback("the SAT ")
                streaming_callback("decisions, ")
                streaming_callback("rental terminations ")
                streaming_callback("require proper notice...")
                return ""  # Return empty string when streaming
            return "Based on the SAT decisions, rental terminations require proper notice..."
        
        mock_generate.side_effect = fake_streaming
        
        # Create the request
        request = ChatRequest(
            message="What are the requirements for terminating a rental agreement?",
            conversation_id=None  # New conversation
        )
        
        # Create a test streaming callback
        chunks = []
        def test_callback(chunk):
            chunks.append(chunk)
        
        # Execute with streaming callback
        response = await process_chat(request, db=None, streaming_callback=test_callback)
        
        # Assert
        self.assertIsInstance(response, ChatResponse)
        self.assertEqual(response.response, "")  # Empty string for streaming response
        self.assertTrue(response.conversation_id.startswith("conv_"))
        
        # Check that the streaming chunks were collected
        self.assertEqual(len(chunks), 5)
        self.assertEqual("".join(chunks), "Based on the SAT decisions, rental terminations require proper notice...")


if __name__ == "__main__":
    unittest.main() 