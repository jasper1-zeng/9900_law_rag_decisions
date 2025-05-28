"""
Service for handling case content chunking and embeddings.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import uuid
from app.db.models import Case, CaseChunk
from rag.embeddings import generate_embeddings
from langchain.text_splitter import SpacyTextSplitter

# Default chunk size and overlap
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 100

async def process_case_chunks(
    case_id: str, 
    content: str, 
    db: Session, 
    chunk_size: int = DEFAULT_CHUNK_SIZE, 
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
) -> List[str]:
    """
    Process a case document into chunks, generate embeddings, and store in the database.
    
    Args:
        case_id: The ID of the case
        content: The case text content to chunk
        db: Database session
        chunk_size: Size of each chunk in characters
        chunk_overlap: Overlap between chunks in characters
        
    Returns:
        List of chunk IDs created
    """
    # Check if the case exists
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise ValueError(f"Case with ID {case_id} not found")
    
    # Delete any existing chunks for this case to avoid duplicates
    db.query(CaseChunk).filter(CaseChunk.case_id == case_id).delete()
    
    # Create text splitter
    text_splitter = SpacyTextSplitter(
        chunk_size=chunk_size, 
        chunk_overlap=chunk_overlap
    )
    
    # Split text into chunks
    chunks = text_splitter.split_text(content)
    
    # Process each chunk
    chunk_ids = []
    for i, chunk_text in enumerate(chunks):
        # Generate embedding for the chunk
        embedding = generate_embeddings(chunk_text)
        
        # Create a new chunk record
        chunk_id = str(uuid.uuid4())
        chunk = CaseChunk(
            id=chunk_id,
            case_id=case_id,
            case_topic=case.case_topic,
            chunk_index=i,
            chunk_text=chunk_text,
            chunk_embedding=embedding,
            chunk_metadata={
                "position": i,
                "total_chunks": len(chunks),
                "chars": len(chunk_text)
            }
        )
        
        # Add to database
        db.add(chunk)
        chunk_ids.append(chunk_id)
    
    # Commit the changes
    db.commit()
    
    return chunk_ids

async def search_similar_chunks(
    query: str, 
    db: Session, 
    limit: int = 5, 
    case_topic: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search for chunks similar to the query text.
    
    Args:
        query: The query text
        db: Database session
        limit: Maximum number of results to return
        case_topic: Optional topic filter
        
    Returns:
        List of similar chunks with their case information
    """
    # Generate query embedding
    query_embedding = generate_embeddings(query)
    
    # Build the SQL query for vector similarity search
    query_text = """
    SELECT 
        rc.id as chunk_id,
        rc.chunk_text,
        rc.chunk_index,
        s.id as case_id,
        s.case_title,
        rc.case_topic,
        s.citation_number,
        s.case_url,
        1 - (rc.chunk_embedding <-> CAST(:embedding AS vector)) as similarity
    FROM 
        reasons_chunks rc
    JOIN 
        satdata s ON rc.case_id = s.id
    """
    
    # Add filter by topic if provided
    params = {"embedding": query_embedding, "limit": limit}
    if case_topic:
        query_text += " WHERE rc.case_topic = :topic"
        params["topic"] = case_topic
    
    # Add order by and limit
    query_text += """
    ORDER BY rc.chunk_embedding <-> CAST(:embedding AS vector)
    LIMIT :limit
    """
    
    # Execute the query
    results = db.execute(query_text, params).fetchall()
    
    # Format the results
    return [
        {
            "chunk_id": row.chunk_id,
            "chunk_text": row.chunk_text,
            "chunk_index": row.chunk_index,
            "case_id": row.case_id,
            "case_title": row.case_title,
            "case_topic": row.case_topic,
            "citation_number": row.citation_number,
            "case_url": row.case_url,
            "similarity": float(row.similarity)
        }
        for row in results
    ] 