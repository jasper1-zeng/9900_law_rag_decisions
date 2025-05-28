from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from app.api.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import process_chat
from app.db.database import get_db
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import json
import asyncio
from sse_starlette.sse import EventSourceResponse

router = APIRouter(
    prefix="/api/v1",
    tags=["chat"]
)

@router.post("/chat", response_model=ChatResponse)
async def simple_chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Simple chat endpoint that returns a response to a user message.
    
    This uses the database to maintain conversation history.
    """
    try:
        return await process_chat(request, db=db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat/stream")
async def stream_chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Streaming chat endpoint that returns a response to a user message as a server-sent event stream.
    """
    async def event_generator():
        # Buffer to collect response
        response_buffer = []
        
        # Define a callback to send chunks as they're generated
        def send_chunk(chunk: str):
            response_buffer.append(chunk)
            # Yield the chunk as a server-sent event
            return {"data": json.dumps({"chunk": chunk})}
        
        # Initialize response with conversation_id
        initial_response = {"conversation_id": request.conversation_id or ""}
        yield {"data": json.dumps(initial_response)}
        
        try:
            # Process the chat request with streaming
            response = await process_chat(
                request, 
                db=db,
                streaming_callback=send_chunk
            )
            
            # Update conversation_id if it was generated
            if not request.conversation_id:
                yield {"data": json.dumps({"conversation_id": response.conversation_id})}
                
            # Signal completion
            yield {"data": json.dumps({"done": True})}
            
        except Exception as e:
            # Send error message
            yield {"data": json.dumps({"error": str(e)})}
    
    return EventSourceResponse(event_generator())

@router.get("/conversations", response_model=List[Dict[str, Any]])
async def get_conversations(db: Session = Depends(get_db), limit: int = 20, offset: int = 0):
    """
    Get a list of conversations.
    """
    from app.db.conversation_repository import ConversationRepository
    
    try:
        repo = ConversationRepository(db)
        conversations = repo.get_conversations_for_user(user_id=None, limit=limit, offset=offset)
        
        return [
            {
                "id": conv.id,
                "title": conv.title,
                "type": conv.conversation_type,
                "created_at": conv.created_at.isoformat() if conv.created_at else None,
                "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
                "message_count": len(conv.messages) if hasattr(conv, "messages") else 0
            }
            for conv in conversations
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{conversation_id}/messages", response_model=List[Dict[str, Any]])
async def get_conversation_messages(conversation_id: str, db: Session = Depends(get_db), limit: int = 50):
    """
    Get messages for a conversation.
    """
    from app.db.conversation_repository import ConversationRepository
    
    try:
        repo = ConversationRepository(db)
        messages = repo.get_messages(conversation_id, limit=limit)
        
        return [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
                "reasoning_steps": msg.reasoning_steps,
                "has_retrieved_documents": len(msg.retrieved_documents) > 0 if msg.retrieved_documents else False
            }
            for msg in messages
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, db: Session = Depends(get_db)):
    """
    Delete a conversation and all its messages.
    """
    from app.db.conversation_repository import ConversationRepository
    
    try:
        repo = ConversationRepository(db)
        deleted = repo.delete_conversation(conversation_id)
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Conversation with id {conversation_id} not found")
            
        return {"status": "success", "message": "Conversation deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 