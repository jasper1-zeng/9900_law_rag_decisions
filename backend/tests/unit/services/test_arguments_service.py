"""
Tests for the arguments service that builds legal arguments.

This file contains tests for the arguments service that integrates with the RAG system
to generate legal arguments based on case content.
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
from app.services.arguments_service import build_arguments_service
from app.api.schemas.arguments import BuildArgumentsRequest, BuildArgumentsResponse, RelatedCase
from app.db.conversation_repository import ConversationRepository


class TestArgumentsService(unittest.TestCase):
    """Tests for the arguments service."""
    
    @patch('app.services.arguments_service.generate_embeddings')
    @patch('app.services.arguments_service.retrieve_with_reranking')
    @patch('app.services.arguments_service.retrieve_case_chunks_with_reranking')
    @patch('app.services.arguments_service.get_llm_provider')
    @patch('app.services.arguments_service.generate_with_single_call_reasoning')
    @patch('app.services.arguments_service.ConversationRepository')
    async def test_build_arguments_single_call(
        self, mock_repo_class, mock_reasoning, mock_llm_provider, 
        mock_retrieve_chunks, mock_retrieve_docs, mock_embeddings
    ):
        """Test building arguments with single-call reasoning approach."""
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
                "case_id": "case2",
                "case_title": "Test Case 2",
                "case_topic": "Commercial Tenancy",
                "citation_number": "2023 SAT 124",
                "case_url": "https://example.com/case2",
                "similarity": 0.88
            }
        ]
        
        # Mock LLM provider
        mock_llm = MagicMock()
        mock_llm.get_name.return_value = "Test Model"
        mock_llm_provider.return_value = mock_llm
        
        # Mock reasoning output
        mock_reasoning.return_value = {
            "final_output": "This is the final legal analysis and arguments.",
            "token_usage": {
                "input_tokens": 500,
                "output_tokens": 300
            },
            "execution_time": 2.5
        }
        
        # Create a mock for the repository instance
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        
        # Mock repository methods
        mock_repo.create_conversation.return_value = MagicMock(id="test_conv_id")
        mock_repo.get_conversation_history.return_value = []
        
        # Create the request
        case_content = "The tenant claims the landlord failed to maintain the property according to the lease agreement."
        request = BuildArgumentsRequest(
            case_content=case_content,
            case_title="Smith v. Johnson",
            case_topic="Commercial Tenancy",
            use_single_call=True,
            conversation_id=None  # New conversation
        )
        
        # Execute
        response = await build_arguments_service(request, db=MagicMock())
        
        # Assert
        self.assertIsInstance(response, BuildArgumentsResponse)
        self.assertEqual(response.raw_content, "This is the final legal analysis and arguments.")
        self.assertEqual(response.conversation_id, "test_conv_id")
        self.assertGreater(len(response.related_cases), 0)
        self.assertIn("Test Model", response.disclaimer)
        
        # Verify mocks were called correctly
        mock_embeddings.assert_called_once_with(case_content)
        mock_retrieve_docs.assert_called_once()
        mock_retrieve_chunks.assert_called_once()
        mock_reasoning.assert_called_once()
        mock_repo.create_conversation.assert_called_once()
        mock_repo.add_message.assert_called()
    
    @patch('app.services.arguments_service.generate_embeddings')
    @patch('app.services.arguments_service.retrieve_with_reranking')
    @patch('app.services.arguments_service.retrieve_case_chunks_with_reranking')
    @patch('app.services.arguments_service.get_llm_provider')
    @patch('app.services.arguments_service.generate_with_optimized_reasoning')
    @patch('app.services.arguments_service.ConversationRepository')
    async def test_build_arguments_multi_step(
        self, mock_repo_class, mock_reasoning, mock_llm_provider, 
        mock_retrieve_chunks, mock_retrieve_docs, mock_embeddings
    ):
        """Test building arguments with multi-step reasoning approach."""
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
                "case_id": "case2",
                "case_title": "Test Case 2",
                "case_topic": "Commercial Tenancy",
                "citation_number": "2023 SAT 124",
                "case_url": "https://example.com/case2",
                "similarity": 0.88
            }
        ]
        
        # Mock LLM provider
        mock_llm = MagicMock()
        mock_llm.get_name.return_value = "Test Model"
        mock_llm_provider.return_value = mock_llm
        
        # Mock reasoning output
        mock_reasoning.return_value = {
            "final_output": "This is the final legal analysis with multi-step reasoning.",
            "steps": [
                {
                    "step": "Step 1: Analyze Facts",
                    "output": "Analyzed the facts of the case.",
                    "metrics": {"execution_time_seconds": 0.5}
                },
                {
                    "step": "Step 2: Identify Legal Issues",
                    "output": "Identified breach of lease agreement.",
                    "metrics": {"execution_time_seconds": 0.5}
                }
            ]
        }
        
        # Setup step callback tracker
        step_calls = []
        def step_callback(step):
            step_calls.append(step)
        
        # Create a mock for the repository instance
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        
        # Mock repository methods
        mock_repo.get_conversation.return_value = MagicMock(id="existing_conv_id")
        mock_repo.get_conversation_history.return_value = [
            {"role": "user", "content": "Previous case analysis"},
            {"role": "assistant", "content": "Previous arguments"}
        ]
        
        # Create the request with existing conversation ID
        case_content = "The tenant claims the landlord failed to maintain the property."
        request = BuildArgumentsRequest(
            case_content=case_content,
            case_title="Smith v. Johnson",
            case_topic="Commercial Tenancy",
            use_single_call=False,  # Use multi-step
            conversation_id="existing_conv_id"
        )
        
        # Execute
        response = await build_arguments_service(
            request, 
            db=MagicMock(),
            step_callback=step_callback
        )
        
        # Assert
        self.assertIsInstance(response, BuildArgumentsResponse)
        self.assertEqual(response.raw_content, "This is the final legal analysis with multi-step reasoning.")
        self.assertEqual(response.conversation_id, "existing_conv_id")
        self.assertGreater(len(response.related_cases), 0)
        
        # Verify step callback was used
        self.assertEqual(len(step_calls), 2)
        
        # Verify mocks were called correctly
        mock_retrieve_docs.assert_called_once()
        mock_retrieve_chunks.assert_called_once()
        mock_reasoning.assert_called_once()
        # Should pass the step_callback
        mock_reasoning.assert_called_with(
            case_content, 
            unittest.mock.ANY,  # We don't know exactly what context will be passed
            topic=request.case_topic, 
            step_callback=step_callback,
            llm_model=None  # Default None if not specified
        )
    
    @patch('app.services.arguments_service.generate_embeddings')
    @patch('app.services.arguments_service.retrieve_documents')
    @patch('app.services.arguments_service.retrieve_case_chunks')
    @patch('app.services.arguments_service.get_llm_provider')
    @patch('app.services.arguments_service.generate_with_single_call_reasoning')
    async def test_build_arguments_without_db(
        self, mock_reasoning, mock_llm_provider, 
        mock_retrieve_chunks, mock_retrieve_docs, mock_embeddings
    ):
        """Test building arguments without database integration."""
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
                "case_id": "case2",
                "case_title": "Test Case 2",
                "case_topic": "Commercial Tenancy",
                "citation_number": "2023 SAT 124",
                "case_url": "https://example.com/case2",
                "similarity": 0.88
            }
        ]
        
        # Mock LLM provider
        mock_llm = MagicMock()
        mock_llm.get_name.return_value = "Test Model"
        mock_llm_provider.return_value = mock_llm
        
        # Mock reasoning output
        mock_reasoning.return_value = {
            "final_output": "This is the final legal analysis without DB."
        }
        
        # Create the request
        case_content = "The tenant claims the landlord failed to maintain the property."
        request = BuildArgumentsRequest(
            case_content=case_content,
            case_title="Smith v. Johnson",
            case_topic="Commercial Tenancy",
            use_single_call=True,
            conversation_id=None
        )
        
        # Execute - no db session provided
        response = await build_arguments_service(request, db=None)
        
        # Assert
        self.assertIsInstance(response, BuildArgumentsResponse)
        self.assertEqual(response.raw_content, "This is the final legal analysis without DB.")
        self.assertTrue(isinstance(response.conversation_id, str))  # Should generate UUID
    
    @patch('app.services.arguments_service.generate_embeddings')
    @patch('app.services.arguments_service.retrieve_with_reranking')
    @patch('app.services.arguments_service.retrieve_case_chunks_with_reranking')
    async def test_build_arguments_with_low_similarity(
        self, mock_retrieve_chunks, mock_retrieve_docs, mock_embeddings
    ):
        """Test building arguments when similarity is low and fallback is used."""
        # Setup mocks
        mock_embeddings.return_value = [0.1] * 768
        
        # First retrieval returns low similarity results
        mock_retrieve_docs.return_value = [
            {
                "id": "case1",
                "case_title": "Test Case 1",
                "reasons_summary": "This is a test case about rental properties.",
                "citation_number": "2023 SAT 123",
                "case_url": "https://example.com/case1",
                "similarity": 0.35  # Low similarity
            }
        ]
        mock_retrieve_chunks.return_value = []
        
        # Create the request
        case_content = "The tenant claims the landlord failed to maintain the property."
        request = BuildArgumentsRequest(
            case_content=case_content,
            case_title="Smith v. Johnson",
            case_topic="Commercial Tenancy",
            use_single_call=True,
            conversation_id=None
        )
        
        # Mock retrieve_documents to test the fallback path with higher limit
        with patch('app.services.arguments_service.retrieve_documents') as mock_retrieve_fallback:
            mock_retrieve_fallback.return_value = [
                {
                    "id": "case1",
                    "case_title": "Fallback Case 1",
                    "reasons_summary": "This is a fallback case with lower similarity.",
                    "citation_number": "2023 SAT 123",
                    "case_url": "https://example.com/case1",
                    "similarity": 0.38  # Above fallback threshold
                }
            ]
            
            # Patch the reasoning function to return a simple response
            with patch('app.services.arguments_service.generate_with_single_call_reasoning') as mock_reasoning:
                mock_reasoning.return_value = {
                    "final_output": "Analysis with fallback documents."
                }
                
                # Mock LLM provider
                with patch('app.services.arguments_service.get_llm_provider') as mock_llm_provider:
                    mock_llm = MagicMock()
                    mock_llm.get_name.return_value = "Test Model"
                    mock_llm_provider.return_value = mock_llm
                
                    # Execute
                    response = await build_arguments_service(request, db=None)
                    
                    # Assert
                    self.assertIsInstance(response, BuildArgumentsResponse)
                    self.assertEqual(response.raw_content, "Analysis with fallback documents.")
                    
                    # Verify fallback path was used
                    mock_retrieve_fallback.assert_called_once()
    
    @patch('app.services.arguments_service.generate_embeddings')
    async def test_build_arguments_error_handling(self, mock_embeddings):
        """Test error handling during argument building."""
        # Setup mocks to raise exception
        mock_embeddings.side_effect = Exception("Embedding error")
        
        # Create the request
        case_content = "The tenant claims the landlord failed to maintain the property."
        request = BuildArgumentsRequest(
            case_content=case_content,
            case_title="Smith v. Johnson",
            case_topic="Commercial Tenancy",
            conversation_id=None
        )
        
        # Execute
        response = await build_arguments_service(request, db=None)
        
        # Assert
        self.assertIsInstance(response, BuildArgumentsResponse)
        self.assertIn("Error", response.raw_content)
        self.assertEqual(len(response.related_cases), 0)  # No cases on error
    
    @patch('app.services.arguments_service.generate_embeddings')
    @patch('app.services.arguments_service.retrieve_with_reranking')
    @patch('app.services.arguments_service.retrieve_case_chunks_with_reranking')
    @patch('app.services.arguments_service.get_llm_provider')
    @patch('app.services.arguments_service.generate_with_single_call_reasoning')
    async def test_build_arguments_with_streaming(
        self, mock_reasoning, mock_llm_provider, 
        mock_retrieve_chunks, mock_retrieve_docs, mock_embeddings
    ):
        """Test building arguments with streaming callback."""
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
                "case_id": "case2",
                "case_title": "Test Case 2",
                "case_topic": "Commercial Tenancy",
                "citation_number": "2023 SAT 124",
                "case_url": "https://example.com/case2",
                "similarity": 0.88
            }
        ]
        
        # Mock LLM provider
        mock_llm = MagicMock()
        mock_llm.get_name.return_value = "Test Model"
        mock_llm_provider.return_value = mock_llm
        
        # For streaming, we need to define what happens when generation is called with streaming_callback
        def fake_streaming_reasoning(case_content, context, topic=None, step_callback=None, streaming_callback=None, llm_model=None):
            # Call step_callback if provided
            if step_callback:
                step_callback({
                    "step": "Test Step",
                    "output": "Test step output",
                    "metrics": {"execution_time_seconds": 0.5}
                })
            
            # Call streaming_callback if provided
            if streaming_callback:
                streaming_callback("This is ")
                streaming_callback("a streamed ")
                streaming_callback("legal ")
                streaming_callback("analysis.")
                return {"final_output": ""}  # Empty final output when streaming
            
            return {"final_output": "This is a complete legal analysis."}
            
        mock_reasoning.side_effect = fake_streaming_reasoning
        
        # Create the request
        case_content = "The tenant claims the landlord failed to maintain the property."
        request = BuildArgumentsRequest(
            case_content=case_content,
            case_title="Smith v. Johnson",
            case_topic="Commercial Tenancy",
            use_single_call=True
        )
        
        # Setup streaming callback tracker
        streamed_chunks = []
        def streaming_callback(chunk):
            streamed_chunks.append(chunk)
        
        # Execute with streaming callback
        response = await build_arguments_service(
            request, 
            db=None, 
            streaming_callback=streaming_callback
        )
        
        # Assert
        self.assertIsInstance(response, BuildArgumentsResponse)
        self.assertEqual(response.raw_content, "")  # Empty string for streaming response
        
        # Check that the streaming chunks were collected
        self.assertEqual(len(streamed_chunks), 4)
        self.assertEqual("".join(streamed_chunks), "This is a streamed legal analysis.")


if __name__ == "__main__":
    unittest.main() 