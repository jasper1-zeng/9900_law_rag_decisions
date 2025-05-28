"""
End-to-end system tests using direct HTTP requests to the running server.

These tests verify the complete flow of requests through the system.
"""
import pytest
import requests
import uuid

# Define the base URL for API requests
BASE_URL = "http://localhost:8000"

# Mark this as a system test
@pytest.mark.system
class TestDirectSystemE2E:
    """System tests using direct HTTP requests."""
    
    def setup_method(self):
        """Setup before each test."""
        # Check if server is running
        try:
            response = requests.get(f"{BASE_URL}/docs")
            if response.status_code != 200:
                pytest.skip("Server not available for system testing")
        except requests.exceptions.ConnectionError:
            pytest.skip("Server not available for system testing")
        
        # Create a unique session ID for each test
        self.session_id = str(uuid.uuid4())
    
    def test_chat_with_no_rag(self):
        """Test chat functionality without RAG, using only the language model."""
        request_data = {
            "message": "Explain the difference between common law and statutory law",
            "conversation_id": None,
            "llm_model": "gpt-4o",
            "use_rag": False
        }
        
        response = requests.post(f"{BASE_URL}/api/v1/chat", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] is not None
        assert "response" in data
        assert len(data["response"]) > 0
        
        # The response should reference the legal concepts asked about
        response_content = data["response"].lower()
        assert all(term in response_content for term in ["common law", "statutory"])
    
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
        response = requests.post(f"{BASE_URL}/api/v1/build-arguments", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        # Verify basic structure
        assert "conversation_id" in data
        assert data["conversation_id"] is not None
        assert "disclaimer" in data
        assert len(data["disclaimer"]) > 0
        assert "raw_content" in data
        assert len(data["raw_content"]) > 0
        
        # The response should reference relevant legal concepts
        response_content = data["raw_content"].lower()
        assert any(term in response_content for term in [
            "repair", "landlord", "tenant", "obligation", "habitability", "rights"
        ])

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 