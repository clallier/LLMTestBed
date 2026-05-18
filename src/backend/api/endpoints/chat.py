from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.schemas.chat import ChatRequest
from backend.core.agent_processor import AgentStreamProcessor
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
processor = AgentStreamProcessor()

@router.post("/chat", summary="Chat with Agent", description="Handles multi-step chat logic with tool detection and streaming support.")
async def chat(request: ChatRequest):
    """
    Primary chat endpoint implementing a streaming-first Agent Loop.
    
    Args:
        request (ChatRequest): User payload with model, messages, and optional tools.
        
    Returns:
        StreamingResponse: NDJSON stream of the assistant's response.
    """
    try:
        messages = [msg.model_dump() for msg in request.messages]
        if request.system:
            messages.insert(0, {"role": "system", "content": request.system})
            
        return StreamingResponse(
            processor.process_stream(request, messages),
            media_type="application/x-ndjson"
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
