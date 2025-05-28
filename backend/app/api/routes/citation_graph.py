from fastapi import APIRouter, Depends, HTTPException, Request
import httpx
from app.config import settings
from app.db.database import get_db
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List

# Original prefix was causing a mismatch with the Neo4j API routes
router = APIRouter(
    prefix="/api",
    tags=["citation-graph"]
)

# Get Neo4j API base URL from settings
NEO4J_API_BASE_URL = settings.neo4j_api_base_url


@router.get("/cases/search")
async def search_cases(q: str, limit: Optional[int] = 10, db: Session = Depends(get_db)):
    """
    Search for cases matching a query string
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{NEO4J_API_BASE_URL}/api/cases/search",
                params={"q": q, "limit": limit}
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to Neo4j API: {str(e)}")


@router.get("/cases/{citation_number}")
async def get_case(citation_number: str, db: Session = Depends(get_db)):
    """
    Get details about a specific case and its citations
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{NEO4J_API_BASE_URL}/api/cases/{citation_number}")
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to Neo4j API: {str(e)}")


@router.get("/cases/{citation_number}/graph")
async def get_case_graph(citation_number: str, db: Session = Depends(get_db)):
    """
    Get visualization data for a specific case
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{NEO4J_API_BASE_URL}/api/cases/{citation_number}/graph")
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to Neo4j API: {str(e)}")


@router.get("/cases/{citation_number}/cited_by")
async def get_cited_by(citation_number: str, db: Session = Depends(get_db)):
    """
    Get cases that cite this case
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{NEO4J_API_BASE_URL}/api/cases/{citation_number}/cited_by")
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to Neo4j API: {str(e)}")


@router.get("/laws/search")
async def search_laws(q: str, limit: Optional[int] = 10, db: Session = Depends(get_db)):
    """
    Search for laws matching a query string
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{NEO4J_API_BASE_URL}/api/laws/search",
                params={"q": q, "limit": limit}
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to Neo4j API: {str(e)}")


@router.get("/laws/{law_id}")
async def get_law(law_id: str, db: Session = Depends(get_db)):
    """
    Get details about a specific law and cases that cite it
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{NEO4J_API_BASE_URL}/api/laws/{law_id}")
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to Neo4j API: {str(e)}")


@router.get("/laws/{law_id}/graph")
async def get_law_graph(law_id: str, db: Session = Depends(get_db)):
    """
    Get visualization data for a specific law
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{NEO4J_API_BASE_URL}/api/laws/{law_id}/graph")
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to Neo4j API: {str(e)}")


@router.get("/sections/{law_id}/{section_id}")
async def get_section(law_id: str, section_id: str, db: Session = Depends(get_db)):
    """
    Get details about a specific law section
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{NEO4J_API_BASE_URL}/api/sections/{law_id}/{section_id}")
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to Neo4j API: {str(e)}")


@router.get("/visualizer")
async def get_visualizer(request: Request, db: Session = Depends(get_db)):
    """
    Proxy to the Neo4j visualizer
    (Note: This is a temporary solution; you might want to integrate this directly into your React app)
    """
    return {"redirect_url": f"{NEO4J_API_BASE_URL}/visualizer"}


@router.post("/network")
async def get_network(request: Request, db: Session = Depends(get_db)):
    """
    Get a network of cases and their relationships for visualization
    """
    try:
        body = await request.json()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{NEO4J_API_BASE_URL}/api/network",
                json=body
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Error connecting to Neo4j API: {str(e)}") 