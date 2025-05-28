"""Main application module for the RAG system.

This module initializes the FastAPI application.
"""
# Apply monkey patch to fix proxies issue with OpenAI client
try:
    import httpx
    from functools import wraps

    # Store the original Client.__init__
    original_client_init = httpx.Client.__init__

    @wraps(original_client_init)
    def patched_client_init(self, *args, **kwargs):
        # Remove 'proxies' from kwargs if present
        if 'proxies' in kwargs:
            print("Removing 'proxies' from httpx.Client initialization")
            kwargs.pop('proxies')
        
        # Call the original init
        return original_client_init(self, *args, **kwargs)

    # Apply the monkey patch
    httpx.Client.__init__ = patched_client_init
    print("Successfully patched httpx.Client.__init__ to fix 'proxies' issue")
except Exception as e:
    print(f"Failed to patch httpx.Client: {e}")
    # Continue anyway

from fastapi import FastAPI, Depends, HTTPException, status, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
import time
import os
import logging
from dotenv import load_dotenv
from app.config import settings
from app.api.routes.chat import router as chat_router
from app.api.routes.arguments import router as arguments_router
from app.api.routes.case_chunks import router as case_chunks_router
from app.api.routes.users import router as users_router
from app.api.routes.citation_graph import router as citation_graph_router
from app.api.routes.health import router as health_router
from app.api.dependencies import get_current_user
from app.db.database import init_db, engine
from app.db import models
from rag import initialize_rag

logger = logging.getLogger(__name__)

# Create all database tables (if they don't exist)
models.Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title="SAT Legal Decisions API",
    description="API for searching and analyzing legal decisions",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Add request processing time middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Add health check endpoint
@app.get("/health", response_class=PlainTextResponse, tags=["Health"])
async def health_check():
    """Health check endpoint for Docker healthcheck"""
    return "OK"

# Include routers
app.include_router(chat_router)
app.include_router(arguments_router)
app.include_router(case_chunks_router)
app.include_router(users_router, prefix="/api/v1")
app.include_router(citation_graph_router)
app.include_router(health_router)

# Add root route that returns a simple message
@app.get("/")
async def root():
    return {"message": "Welcome to the SAT Legal Decisions API. Visit /docs for API documentation."}

# Startup event
@app.on_event("startup")
async def startup_event():
    # Initialize database
    init_db()
    
    # Initialize RAG components
    try:
        initialize_rag()
    except Exception as e:
        logger.error(f"Error initializing RAG system: {e}")
        logger.warning("Application will continue with limited functionality")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down")
