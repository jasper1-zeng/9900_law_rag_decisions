"""
End-to-end system tests for the chat functionality.

These tests verify the complete flow of chat requests through the system.
"""
import sys
import os
import pytest
from fastapi.testclient import TestClient
import httpx
import uuid

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Try to import the app - but don't fail the whole test file if it's not available
try:
    # Store original method before app import might patch it
    original_client_init = httpx.Client.__init__
    
    from app import app
    
    # Create test client with the proper initialization
    client = TestClient(app)
    APP_AVAILABLE = True
except ImportError:
    APP_AVAILABLE = False
    client = None


# Mark this as a system test
@pytest.mark.system
class TestChatSystemE2E:
    """System tests for the chat functionality."""
    
    def setup_method(self):
        """Setup before each test."""
        if not APP_AVAILABLE:
            pytest.skip("App not available for system testing")
        
        # Create a unique session ID for each test
        self.session_id = str(uuid.uuid4())
    
    def test_new_chat_conversation(self):
        """Test starting a new chat conversation."""
        # Create a chat request
        request_data = {
            "message_content": "What are the key legal rights of tenants in NSW?",
            "conversation_id": None,
            "llm_model": "gpt-4o",
            "use_rag": True
        }
        
        # Send the request
        response = client.post("/api/chat", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] is not None
        assert "response" in data
        assert len(data["response"]) > 0
        
        # Store conversation ID for follow-up test
        self.conversation_id = data["conversation_id"]
        
        # The response should reference tenant rights or NSW-specific information
        response_content = data["response"].lower()
        assert any(term in response_content for term in ["tenant", "right", "nsw", "housing", "rental"])
    
    def test_chat_conversation_follow_up(self):
        """Test following up on an existing chat conversation."""
        # First create a new conversation
        initial_request = {
            "message_content": "What are the remedies available if a landlord refuses to make repairs?",
            "conversation_id": None,
            "llm_model": "gpt-4o",
            "use_rag": True
        }
        
        initial_response = client.post("/api/chat", json=initial_request)
        assert initial_response.status_code == 200
        conversation_id = initial_response.json()["conversation_id"]
        
        # Now send a follow-up question
        follow_up_request = {
            "message_content": "How much notice do I need to give before terminating my lease early?",
            "conversation_id": conversation_id,
            "llm_model": "gpt-4o",
            "use_rag": True
        }
        
        follow_up_response = client.post("/api/chat", json=follow_up_request)
        
        # Verify follow-up response
        assert follow_up_response.status_code == 200
        data = follow_up_response.json()
        assert data["conversation_id"] == conversation_id
        assert "response" in data
        assert len(data["response"]) > 0
        
        # The response should reference notice periods or termination
        response_content = data["response"].lower()
        assert any(term in response_content for term in ["notice", "termination", "lease", "period", "early"])
    
    def test_chat_with_no_rag(self):
        """Test chat functionality without RAG, using only the language model."""
        request_data = {
            "message_content": "Explain the difference between common law and statutory law",
            "conversation_id": None,
            "llm_model": "gpt-4o",
            "use_rag": False
        }
        
        response = client.post("/api/chat", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] is not None
        assert "response" in data
        assert len(data["response"]) > 0
        
        # The response should reference the legal concepts asked about
        response_content = data["response"].lower()
        assert all(term in response_content for term in ["common law", "statutory"])


if __name__ == "__main__":
    pytest.main(["-v", __file__]) 