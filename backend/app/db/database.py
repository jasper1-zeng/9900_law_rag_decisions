"""Database connection and session management.

This module handles database connections and SQLAlchemy session setup.
"""

import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import DDL
import os
from app.config import settings

logger = logging.getLogger(__name__)

# Use the connection string from settings
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# Log the database connection string (obscuring password)
safe_db_url = SQLALCHEMY_DATABASE_URL
if "://" in safe_db_url:
    parts = safe_db_url.split("://", 1)
    if "@" in parts[1]:
        credentials, rest = parts[1].split("@", 1)
        if ":" in credentials:
            username, _ = credentials.split(":", 1)
            safe_db_url = f"{parts[0]}://{username}:****@{rest}"
logger.info(f"Connecting to database with URL: {safe_db_url}")

try:
    # Create SQLAlchemy engine
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        # Remove sqlite-specific parameters
        # connect_args={"check_same_thread": False}
    )
    logger.info("Database engine created successfully")
    
    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Database session factory created")
    
    # Create base class for declarative models
    Base = declarative_base()
    
except Exception as e:
    logger.error(f"Error setting up database connection: {str(e)}")
    raise

def init_db():
    """Initialize the database by creating all tables and enabling pgvector extension."""
    # Import models so they are registered with Base
    from app.db.models import Case, User, CaseChunk
    
    # Enable pgvector extension
    with engine.connect() as conn:
        conn.execute(DDL("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    
    # Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
    
    # Create vector indexes after tables exist
    with engine.connect() as conn:
        # Create index for reasons_chunks
        conn.execute(DDL(
            "CREATE INDEX IF NOT EXISTS reasons_chunks_embedding_idx ON reasons_chunks "
            "USING ivfflat (chunk_embedding vector_l2_ops) WITH (lists = 100)"
        ))
        
        # Create index for satdata reasons_summary_embedding
        conn.execute(DDL(
            "CREATE INDEX IF NOT EXISTS satdata_reasons_summary_embedding_idx ON satdata "
            "USING ivfflat (reasons_summary_embedding vector_l2_ops) WITH (lists = 100)"
        ))
        
        conn.commit()

    # Check database connection with a simple query
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        logger.info(f"Database connection test successful: {result.fetchone()}")

def get_db():
    """Dependency for getting the database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 