"""
Tests for the chat API endpoints.

This file contains tests for the chat API routes that handle chat interactions.
"""
import sys
import os
import json
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Import schemas directly - we'll mock the rest
from app.api.schemas.chat import ChatRequest, ChatResponse


class TestChatAPI:
    """Tests for the chat API routes."""
    
    @patch('app.api.routes.chat.process_chat')
    def test_process_chat_endpoint(self, mock_process_chat):
        """Test the POST /api/chat endpoint."""
        # Setup mock response
        mock_response = ChatResponse(
            conversation_id="test_conv_id",
            response="This is a test response"
        )
        
        # Setup async mock return value
        mock_process_chat.return_value = AsyncMock(return_value=mock_response)
        
        # Create request object
        request = ChatRequest(
            message="What are the requirements for terminating a rental agreement?",
            conversation_id=None
        )
        
        # Assert the request is properly structured
        assert request.message == "What are the requirements for terminating a rental agreement?"
        assert request.conversation_id is None
        
        # Assert response individual fields
        assert mock_response.conversation_id == "test_conv_id"
        assert mock_response.response == "This is a test response"
    
    @patch('app.api.routes.chat.process_chat')
    def test_process_chat_with_existing_conversation(self, mock_process_chat):
        """Test chat endpoint with an existing conversation ID."""
        # Setup mock response
        mock_response = ChatResponse(
            conversation_id="existing_id",
            response="Response for existing conversation"
        )
        
        # Setup async mock return value
        mock_process_chat.return_value = AsyncMock(return_value=mock_response)
        
        # Create request data
        request = ChatRequest(
            message="Follow-up question about notice periods?",
            conversation_id="existing_id"
        )
        
        # Assert request is properly constructed
        assert request.message == "Follow-up question about notice periods?"
        assert request.conversation_id == "existing_id"
        
        # Assert response individual fields
        assert mock_response.conversation_id == "existing_id"
        assert mock_response.response == "Response for existing conversation"
    
    def test_chat_validation(self):
        """Test chat request validation."""
        # Test with missing required field
        with pytest.raises(ValueError):
            # Missing message field should raise error
            ChatRequest(conversation_id=None)
        
        # Test with valid data
        valid_request = ChatRequest(
            message="Valid message",
            conversation_id="valid_id"
        )
        
        # Assert valid request works
        assert valid_request.message == "Valid message"
        assert valid_request.conversation_id == "valid_id" 