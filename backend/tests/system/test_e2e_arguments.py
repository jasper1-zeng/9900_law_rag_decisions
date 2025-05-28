"""
End-to-end system tests for the arguments functionality.

These tests verify the complete flow of arguments requests through the system.
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
class TestArgumentsSystemE2E:
    """System tests for the arguments functionality."""
    
    def setup_method(self):
        """Setup before each test."""
        if not APP_AVAILABLE:
            pytest.skip("App not available for system testing")
        
        # Create a unique session ID for each test
        self.session_id = str(uuid.uuid4())
    
    def test_build_arguments(self):
        """Test building legal arguments for a case."""
        # Create an arguments request
        request_data = {
            "case_content": """
            I'm a tenant and my landlord has refused to fix the broken heating system for months. 
            It's winter now and the temperature in my apartment is dropping below safe levels.
            I've sent multiple written requests but received no response. What are my legal rights?
            """,
            "case_title": "Landlord refusing to make repairs",
            "case_topic": "Tenancy Law",
            "llm_model": "gpt-4o"
        }
        
        # Send the request
        response = client.post("/api/arguments", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Verify basic structure
        assert "conversation_id" in data
        assert data["conversation_id"] is not None
        assert "disclaimer" in data
        assert len(data["disclaimer"]) > 0
        assert "response" in data
        assert len(data["response"]) > 0
        
        # Store conversation ID for follow-up test
        self.conversation_id = data["conversation_id"]
        
        # The response should reference relevant legal concepts
        response_content = data["response"].lower()
        assert any(term in response_content for term in [
            "repair", "landlord", "tenant", "obligation", "habitability", "rights"
        ])
    
    def test_arguments_follow_up(self):
        """Test follow-up questions for arguments."""
        # First create a new arguments case
        initial_request = {
            "case_content": """
            I signed a 12-month lease but need to leave early due to a job relocation.
            What are my options for early termination of the lease?
            """,
            "case_title": "Early lease termination",
            "case_topic": "Tenancy Law",
            "llm_model": "gpt-4o"
        }
        
        initial_response = client.post("/api/arguments", json=initial_request)
        assert initial_response.status_code == 200
        conversation_id = initial_response.json()["conversation_id"]
        
        # Now send a follow-up question
        follow_up_request = {
            "message_content": """
            The lease agreement says "tenant may terminate the lease early with 4 weeks notice
            and payment of a break fee equal to 6 weeks rent." Does this seem reasonable?
            """,
            "conversation_id": conversation_id,
            "llm_model": "gpt-4o"
        }
        
        follow_up_response = client.post("/api/arguments/follow-up", json=follow_up_request)
        
        # Verify follow-up response
        assert follow_up_response.status_code == 200
        data = follow_up_response.json()
        assert data["conversation_id"] == conversation_id
        assert "response" in data
        assert len(data["response"]) > 0
        
        # The response should reference break fee or early termination
        response_content = data["response"].lower()
        assert any(term in response_content for term in ["break fee", "termination", "notice", "reasonable"])


if __name__ == "__main__":
    pytest.main(["-v", __file__]) 