"""
Repository for managing conversation history.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid
from app.db.models import Conversation, Message

class ConversationRepository:
    """Repository for managing conversation history."""
    
    def __init__(self, db: Session):
        """
        Initialize the repository.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def create_conversation(self, user_id: Optional[str] = None, title: str = "New Conversation", 
                          conversation_type: str = "chat", metadata: Dict[str, Any] = None) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            user_id: ID of the user (optional)
            title: Title of the conversation
            conversation_type: Type of conversation (chat or arguments)
            metadata: Additional metadata
            
        Returns:
            Conversation: The created conversation
        """
        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=title,
            conversation_type=conversation_type,
            metadata=metadata or {}
        )
        
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        
        return conversation
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get a conversation by ID.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Optional[Conversation]: The conversation if found, None otherwise
        """
        return self.db.query(Conversation).filter(Conversation.id == conversation_id).first()
    
    def get_conversations_for_user(self, user_id: str, limit: int = 20, offset: int = 0) -> List[Conversation]:
        """
        Get conversations for a user.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of conversations to return
            offset: Offset for pagination
            
        Returns:
            List[Conversation]: List of conversations
        """
        return self.db.query(Conversation)\
            .filter(Conversation.user_id == user_id)\
            .order_by(desc(Conversation.updated_at))\
            .offset(offset)\
            .limit(limit)\
            .all()
    
    def add_message(self, conversation_id: str, role: str, content: str,
                 reasoning_steps: List[Dict[str, Any]] = None,
                 retrieved_documents: List[Dict[str, Any]] = None) -> Message:
        """
        Add a message to a conversation.
        
        Args:
            conversation_id: ID of the conversation
            role: Role of the message sender (user, assistant, system)
            content: Content of the message
            reasoning_steps: Reasoning steps for build_arguments feature
            retrieved_documents: Documents retrieved for this message
            
        Returns:
            Message: The created message
        """
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content,
            reasoning_steps=reasoning_steps or [],
            retrieved_documents=retrieved_documents or []
        )
        
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        
        # Update conversation's updated_at timestamp
        conversation = self.get_conversation(conversation_id)
        if conversation:
            # SQLAlchemy will auto-update the updated_at field
            self.db.add(conversation)
            self.db.commit()
        
        return message
    
    def get_messages(self, conversation_id: str, limit: int = 50) -> List[Message]:
        """
        Get messages for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages to return
            
        Returns:
            List[Message]: List of messages
        """
        return self.db.query(Message)\
            .filter(Message.conversation_id == conversation_id)\
            .order_by(Message.created_at)\
            .limit(limit)\
            .all()
    
    def get_conversation_history(self, conversation_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get conversation history in a format suitable for LLM context.
        
        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages to return
            
        Returns:
            List[Dict[str, Any]]: List of messages in LLM-friendly format
        """
        messages = self.get_messages(conversation_id, limit)
        
        # Format for LLM context
        history = []
        for message in messages:
            history.append({
                "role": message.role,
                "content": message.content
            })
        
        return history
        
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation and all its associated messages.
        
        Args:
            conversation_id: ID of the conversation to delete
            
        Returns:
            bool: True if the conversation was deleted, False if it wasn't found
        """
        # First check if the conversation exists
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return False
            
        # Delete all messages associated with the conversation
        self.db.query(Message).filter(Message.conversation_id == conversation_id).delete()
        
        # Delete the conversation itself
        self.db.query(Conversation).filter(Conversation.id == conversation_id).delete()
        
        # Commit the changes
        self.db.commit()
        
        return True 