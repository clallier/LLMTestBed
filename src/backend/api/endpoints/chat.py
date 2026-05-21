"""
Chat and Agent Loop API Endpoints.

High level role: Handles client chat POST requests and registers the multi-turn agent pipeline.
"""
import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.core.agent_processor import AgentStreamProcessor
from backend.core.payload_builder import format_system_prompt_with_tools
from backend.schemas.chat import ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter()
processor = AgentStreamProcessor()


@router.post(
    "/chat",
    summary="Chat with Agent",
    description="Handles multi-step chat logic with tool detection and streaming support."
)
async def chat(request: ChatRequest):
    """Primary chat endpoint implementing a streaming-first Agent Loop.

    High level role: Handles client chat POST requests and registers the multi-turn agent pipeline.
    Description: Integrates raw message history, formats and prepends the system prompt with
    any activated tools, and initiates the streaming processor to yield NDJSON response lines.
    How it works:
    - Deserializes and dumps the client-provided messages from ChatRequest.
    - If a system prompt is provided, appends the activated tools line and prepends it to the history.
    - Constructs and returns a StreamingResponse yielding the asynchronous NDJSON chunks.

    Args:
        request (ChatRequest): Incoming HTTP request body containing model configurations,
            messages history, optional system prompt, and tools list.

    Returns:
        StreamingResponse: Asynchronous NDJSON stream yielding security telemetry, assistant
            completions, and parallel tool executions.

    Raises:
        HTTPException: Raises 500 status code errors if client processing or downstream stream
            retrieval encounters unexpected failures.

    Examples:
        # Example of calling chat endpoint programmatically or in test context:
        >>> from backend.schemas.chat import ChatRequest, ChatMessage
        >>> request = ChatRequest(model="gemma", messages=[ChatMessage(role="user", content="Hi")])
        >>> response = await chat(request)
        >>> assert response.media_type == "application/x-ndjson"
    """
    try:
        messages = [msg.model_dump() for msg in request.messages]
        if request.system:
            sys_content = format_system_prompt_with_tools(request.system, request.tools)
            messages.insert(0, {"role": "system", "content": sys_content})
        logger.info("Messages:\n%s", json.dumps(messages, indent=2))

        return StreamingResponse(
            processor.process_stream(request, messages),
            media_type="application/x-ndjson"
        )
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error("Error in chat endpoint: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e
