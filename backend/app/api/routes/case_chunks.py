from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.chunking_service import process_case_chunks, search_similar_chunks

router = APIRouter(
    prefix="/api/v1/case-chunks",
    tags=["case-chunks"]
)

class ChunkProcessRequest(BaseModel):
    case_id: str
    content: str
    chunk_size: Optional[int] = 500
    chunk_overlap: Optional[int] = 100

class ChunkProcessResponse(BaseModel):
    chunk_ids: List[str]
    total_chunks: int

class ChunkSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5
    case_topic: Optional[str] = None

class ChunkSearchResponse(BaseModel):
    results: List[Dict[str, Any]]
    total_results: int

@router.post("/process", response_model=ChunkProcessResponse)
async def process_chunks(
    request: ChunkProcessRequest,
    db: Session = Depends(get_db)
):
    """
    Process a case document into chunks and store them with embeddings.
    """
    try:
        chunk_ids = await process_case_chunks(
            request.case_id,
            request.content,
            db,
            request.chunk_size,
            request.chunk_overlap
        )
        
        return ChunkProcessResponse(
            chunk_ids=chunk_ids,
            total_chunks=len(chunk_ids)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=ChunkSearchResponse)
async def search_chunks(
    request: ChunkSearchRequest,
    db: Session = Depends(get_db)
):
    """
    Search for case chunks similar to the query.
    """
    try:
        results = await search_similar_chunks(
            request.query, 
            db,
            request.limit,
            request.case_topic
        )
        
        return ChunkSearchResponse(
            results=results,
            total_results=len(results)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 