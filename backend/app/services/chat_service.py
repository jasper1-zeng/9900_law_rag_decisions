"""
Service for processing chat requests.
"""
from typing import Optional, List, Dict, Any, Callable
from sqlalchemy.orm import Session
from app.api.schemas.chat import ChatRequest, ChatResponse
from app.db.conversation_repository import ConversationRepository
from rag.embeddings import generate_embeddings
from rag.retrieval import retrieve_documents, retrieve_case_chunks
from rag.generation import generate_response
import uuid
import logging
import json

logger = logging.getLogger(__name__)

async def process_chat(
    request: ChatRequest, 
    db: Optional[Session] = None,
    streaming_callback: Optional[Callable[[str], None]] = None
) -> ChatResponse:
    """
    Process a chat request using RAG components.
    
    Args:
        request: The chat request containing the message and optional conversation ID
        db: Optional database session for conversation history
        streaming_callback: Optional callback for streaming responses
        
    Returns:
        ChatResponse: The response from the RAG system
    """
    # Import the query classifier
    from app.services.helpers.query_classifier import classify_query
    
    # Classify the query
    query_type, confidence = classify_query(request.message)
    
    # Handle conversation ID
    conversation_id = request.conversation_id
    conversation_repo = None
    conversation_history = []
    
    if db:
        conversation_repo = ConversationRepository(db)
        
        # If conversation ID provided, get history
        if conversation_id:
            # Verify conversation exists
            conversation = conversation_repo.get_conversation(conversation_id)
            if not conversation:
                # Create new conversation if ID doesn't exist
                conversation = conversation_repo.create_conversation(
                    title=f"Chat: {request.message[:30]}...",
                    conversation_type="chat"
                )
                conversation_id = conversation.id
                
            # Get conversation history
            conversation_history = conversation_repo.get_conversation_history(conversation_id)
        else:
            # Create new conversation
            conversation = conversation_repo.create_conversation(
                title=f"Chat: {request.message[:30]}...",
                conversation_type="chat",
                metadata={
                    "query_type": query_type,
                    "query_confidence": confidence
                }
            )
            conversation_id = conversation.id
            
        # Add user message to history
        conversation_repo.add_message(
            conversation_id=conversation_id,
            role="user",
            content=request.message
        )
    else:
        # No database, generate random ID
        if not conversation_id:
            conversation_id = f"conv_{uuid.uuid4()}"
    
    try:
        # Generate embeddings for the query
        query_embedding = generate_embeddings(request.message)
        
        # Retrieve relevant documents and chunks
        documents = retrieve_documents(query_embedding, limit=3)
        chunks = retrieve_case_chunks(query_embedding, limit=5)
        
        # Debug logging
        logger.info(f"Retrieved {len(documents)} documents with query: {request.message}")
        if len(documents) > 0:
            logger.info(f"First document similarity: {documents[0].get('similarity', 0)}")
        
        # Combine context from both sources
        combined_context = []
        
        # Add document-level context
        for doc in documents:
            combined_context.append({
                "type": "document",
                "id": doc["id"],
                "case_title": doc["case_title"],
                "reasons_summary": doc.get("reasons_summary", ""),
                "citation_number": doc.get("citation_number", ""),
                "case_url": doc.get("case_url", ""),
                "similarity": doc["similarity"]
            })
        
        # Add chunk-level context
        for chunk in chunks:
            combined_context.append({
                "type": "chunk",
                "chunk_id": chunk["chunk_id"],
                "case_id": chunk["case_id"],
                "case_title": chunk["case_title"],
                "reasons_summary": chunk["chunk_text"],  # Map chunk_text to reasons_summary
                "citation_number": chunk.get("citation_number", ""),
                "case_url": chunk.get("case_url", ""),
                "similarity": chunk["similarity"]
            })
        
        # Sort by similarity (highest first)
        combined_context.sort(key=lambda x: x["similarity"], reverse=True)
        
        # Generate response with streaming if callback provided
        if streaming_callback:
            # Start streaming response
            response_content = []
            
            # Define a callback to collect the response chunks
            def collect_response(chunk: str):
                response_content.append(chunk)
                streaming_callback(chunk)
            
            # Generate streaming response
            generate_response(
                request.message, 
                combined_context, 
                conversation_history=conversation_history,
                streaming_callback=collect_response
            )
            
            # Combine response chunks for database storage
            response = "".join(response_content)
        else:
            # Generate regular response
            response = generate_response(
                request.message, 
                combined_context,
                conversation_history=conversation_history
            )
        
        # Store response in conversation history if DB available
        if db and conversation_repo:
            conversation_repo.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=response,
                retrieved_documents=[
                    {
                        "id": doc.get("id", ""),
                        "title": doc.get("case_title", ""),
                        "content": doc.get("reasons_summary", "")[:300] + "...",  # Limit content length
                        "similarity": doc.get("similarity", 0)
                    } 
                    for doc in combined_context[:5]  # Store top 5 documents
                ]
            )
        
        logger.info(f"Generated response for query: {request.message[:50]}...")
        return ChatResponse(
            response=response,
            conversation_id=conversation_id
        )
    
    except Exception as e:
        error_message = f"Error processing chat request: {str(e)}"
        logger.error(error_message)
        
        # Store error in conversation history if DB available
        if db and conversation_repo:
            conversation_repo.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=f"I'm sorry, I encountered an error while processing your request: {str(e)}"
            )
        
        # Return error response
        return ChatResponse(
            response=f"I'm sorry, I encountered an error while processing your request. Please try again later.",
            conversation_id=conversation_id
        ) 