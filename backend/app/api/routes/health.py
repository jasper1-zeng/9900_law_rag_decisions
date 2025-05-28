"""Health check routes for the API.

This module provides routes for health checks and status monitoring.
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(
    prefix="/health",
    tags=["Health"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_class=PlainTextResponse)
async def health_check():
    """Health check endpoint for Docker healthcheck"""
    return "OK"