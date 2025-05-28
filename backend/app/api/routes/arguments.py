from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from app.api.schemas.arguments import BuildArgumentsRequest, BuildArgumentsResponse
from app.services.arguments_service import build_arguments_service
from app.db.database import get_db
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import json
import asyncio
from sse_starlette.sse import EventSourceResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["arguments"]
)

@router.post("/build-arguments", response_model=BuildArgumentsResponse)
async def build_arguments_endpoint(request: BuildArgumentsRequest, db: Session = Depends(get_db)):
    """
    Build arguments based on case content submitted by a lawyer.
    Returns related cases, key insights, and suggested arguments.
    Topic parameter allows filtering results by topic area.
    
    Available options:
    - llm_model: Select the language model to use (e.g., "deepseek-reasoner", "claude-3-7-sonnet")
    - use_single_call: Set to true to use a single LLM call approach (faster, potentially less detailed)
                       Set to false (default) to use multi-step reasoning (slower, often more thorough)
    """
    # Log the requested model
    logger.info(f"[MODEL SELECTION] Received request with model: {request.llm_model or 'default (not specified)'}")
    print(f"[MODEL SELECTION] Received request with model: {request.llm_model or 'default (not specified)'}")
    
    try:
        # Store steps silently
        steps = []
        
        # Test callback before passing
        def debug_step_callback(step):
            print(f"\n==== CALLBACK TRIGGERED: {step.get('step', 'Unknown')} ====")
            steps.append(step)
        
        # Use the same approach as the with-reasoning endpoint
        return await build_arguments_service(
            request, 
            db=db,
            step_callback=debug_step_callback
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/build-arguments/stream")
async def stream_build_arguments(request: BuildArgumentsRequest, db: Session = Depends(get_db)):
    """
    Streaming endpoint for building arguments that returns partial results as they are generated.
    """
    async def event_generator():
        # Buffer to collect response
        response_buffer = []
        
        # Define callbacks for steps and final chunks
        async def send_step(step: Dict[str, Any]):
            yield {"data": json.dumps({"step": step})}
        
        async def send_chunk(chunk: str):
            response_buffer.append(chunk)
            yield {"data": json.dumps({"chunk": chunk})}
        
        # Wrapper functions that await the async generators
        def step_callback(step: Dict[str, Any]):
            return send_step(step).__anext__()
            
        def chunk_callback(chunk: str):
            return send_chunk(chunk).__anext__()
        
        # Start the stream
        yield {"data": json.dumps({"status": "starting"})}
        
        try:
            # Process the build-arguments request with step tracking
            response = await build_arguments_service(
                request, 
                db=db,
                step_callback=step_callback,
                streaming_callback=chunk_callback
            )
            
            # Send the final structured response
            yield {"data": json.dumps({
                "status": "completed",
                "result": {
                    "related_cases": [case.dict() for case in response.related_cases],
                    "key_insights": response.key_insights,
                    "key_arguments": response.key_arguments
                }
            })}
            
        except Exception as e:
            # Send error message
            yield {"data": json.dumps({"error": str(e)})}
    
    return EventSourceResponse(event_generator())

@router.post("/build-arguments/with-reasoning", response_model=Dict[str, Any])
async def build_arguments_with_reasoning(request: BuildArgumentsRequest, db: Session = Depends(get_db)):
    """
    Build arguments with full step-by-step reasoning process shown in the response.
    """
    try:
        # Store steps
        steps = []
        
        # Process with step tracking
        response = await build_arguments_service(
            request, 
            db=db,
            step_callback=lambda step: steps.append(step)
        )
        
        # Return both the steps and the final result
        return {
            "steps": steps,
            "related_cases": [case.dict() for case in response.related_cases],
            "key_insights": response.key_insights,
            "key_arguments": response.key_arguments
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/build-arguments/single-call", response_model=BuildArgumentsResponse)
async def build_arguments_single_call(request: BuildArgumentsRequest, db: Session = Depends(get_db)):
    """
    Build arguments using a single LLM call with internal step-by-step reasoning.
    
    This endpoint is optimized for speed, using one comprehensive prompt rather than
    multiple sequential calls to the LLM. The model is instructed to follow the same
    reasoning steps internally.
    
    Benchmark this against the standard endpoint to compare quality vs. speed tradeoffs.
    """
    try:
        # Force the single-call approach regardless of the request parameter
        modified_request = BuildArgumentsRequest(
            case_content=request.case_content,
            case_title=request.case_title,
            case_topic=request.case_topic,
            llm_model=request.llm_model,
            conversation_id=request.conversation_id,
            use_single_call=True  # Force single-call approach
        )
        
        # Use the same service but with modified request
        return await build_arguments_service(
            modified_request, 
            db=db
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 