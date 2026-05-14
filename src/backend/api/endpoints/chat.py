from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.schemas.chat import ChatRequest
from backend.core.ollama_client import ollama_client
from backend.core.tool_registry import TOOL_MAP
from backend.core.payload_builder import build_ollama_payload
import json
import logging
from typing import Any, Dict, List, AsyncGenerator

logger = logging.getLogger(__name__)

router = APIRouter()

def run_tool(tool_call: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a single tool call against the TOOL_MAP.

    High level role: Acts as the execution bridge between the LLM's intent 
    and our local Python functions.

    Args:
        tool_call (Dict[str, Any]): The tool call object from Ollama.

    Returns:
        Dict[str, Any]: A message object with role 'tool' and the execution result.
    """
    func_name = tool_call["function"]["name"]
    args = tool_call["function"]["arguments"]
    
    if isinstance(args, str):
        args = json.loads(args)
        
    if func_name in TOOL_MAP:
        logger.info(f"Executing tool: {func_name}")
        result = TOOL_MAP[func_name](**args)
        return {"role": "tool", "content": str(result)}
    
    return {"role": "tool", "content": f"Error: Tool {func_name} not found"}

async def handle_model_stream(request: ChatRequest, messages: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
    """
    Async generator that manages the recursive agent execution loop.

    High level role: Core logic for streaming answers while handling 
    intermediate tool calls. It yields chunks to the user in real-time.
    """
    payload = build_ollama_payload(request, stream=True)
    payload["messages"] = messages
    
    tool_calls = []
    assistant_msg = {"role": "assistant", "content": ""}
    
    async for chunk_str in ollama_client.chat_stream(payload):
        logger.debug(f"Received chunk: {chunk_str}")
        try:
            data = json.loads(chunk_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON chunk: {chunk_str}")
            continue
            
        if "message" in data:
            msg = data["message"]
            # Yield content for the chat UI
            if "content" in msg and msg["content"]:
                logger.info(f"Yielding content chunk: {msg['content'][:20]}...")
                assistant_msg["content"] += msg["content"]
                yield json.dumps(data) + "\n"
            # Yield tool calls so the Observability Hub can track them
            if "tool_calls" in msg:
                logger.info(f"Detected tool call in stream: {len(msg['tool_calls'])} calls")
                tool_calls.extend(msg["tool_calls"])
                yield json.dumps(data) + "\n"
        
    if tool_calls:
        assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)
        for tc in tool_calls:
            messages.append(run_tool(tc))
        # Recursive call to handle the next step
        async for next_chunk in handle_model_stream(request, messages):
            yield next_chunk

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
            handle_model_stream(request, messages),
            media_type="application/x-ndjson"
        )
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
