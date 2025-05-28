from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, Date, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.config import settings
import uuid
from datetime import datetime

# Import and register pgvector type
from pgvector.sqlalchemy import Vector

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    reset_password_token = Column(String, nullable=True)
    reset_token_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationship to conversations
    conversations = relationship("Conversation", back_populates="user")

class Case(Base):
    __tablename__ = "satdata"
    
    id = Column(Integer, primary_key=True, index=True)
    case_url = Column(String, unique=True, index=True)
    case_title = Column(String)  
    citation_number = Column(String)
    case_year = Column(String)
    case_act = Column(String)
    case_topic = Column(String, index=True)
    member = Column(String)
    heard_date = Column(Date)
    delivery_date = Column(Date)
    file_no = Column(String)
    case_between = Column(Text)
    catchwords = Column(Text)
    legislations = Column(Text)
    result = Column(Text)
    category = Column(String)
    representation = Column(Text)
    referred_cases = Column(Text)
    reasons = Column(Text)
    reasons_summary = Column(Text)
    reasons_summary_embedding = Column(Vector(settings.EMBEDDING_DIM))
    embedding = Column(Vector(settings.EMBEDDING_DIM))
    
    # Legacy fields - keeping them for backwards compatibility
    summary = Column(Text)
    case_type = Column(String, index=True)
    outcome = Column(String, index=True)
    key_points = Column(ARRAY(Text), default=[])
    arguments = Column(JSONB, default={})
    is_draft = Column(Boolean, default=True)
    status = Column(String, default="draft")
    confidence_score = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationship to chunks
    chunks = relationship("CaseChunk", back_populates="case", cascade="all, delete-orphan")

class CaseChunk(Base):
    __tablename__ = "reasons_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("satdata.id"))
    case_topic = Column(String, index=True)
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_embedding = Column(Vector(768))  # Renamed from embedding to chunk_embedding
    chunk_metadata = Column(JSONB, default={})
    
    # Metadata
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationship to parent case
    case = relationship("Case", back_populates="chunks")
    
    class Config:
        indexes = [
            # Composite index for faster retrieval of chunks for a specific case
            {"name": "idx_reasons_chunks_case_id_chunk_index", "fields": ["case_id", "chunk_index"]}
        ]

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # Optional user association
    title = Column(String)  # Auto-generated title based on first message
    is_active = Column(Boolean, default=True)
    conversation_type = Column(String, default="chat")  # chat or arguments
    conversation_metadata = Column(JSONB, default={})  # Additional metadata (client info, etc.)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id"))
    role = Column(String)  # 'user' or 'assistant'
    content = Column(Text)
    
    # For build_arguments, store reasoning steps
    reasoning_steps = Column(JSONB, default=[])
    
    # Store retrieved documents used for this message
    retrieved_documents = Column(JSONB, default=[])
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    conversation = relationship("Conversation", back_populates="messages") 