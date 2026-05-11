from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from schemas.chat import ChatRequest
from core.ollama_client import ollama_client
from core.tool_registry import TOOL_MAP
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat")
async def chat(request: ChatRequest):
    try:
        logger.info(f"Chat request for model: {request.model}")
        # We always disable streaming for the first call to reliably detect tool calls
        payload = {
            "model": request.model,
            "messages": [msg.model_dump() for msg in request.messages],
            "stream": False
        }
        
        if request.system:
            payload["messages"].insert(0, {"role": "system", "content": request.system})
            
        if request.options:
            payload["options"] = request.options
            
        if request.tools:
            payload["tools"] = request.tools

        # First Call
        logger.info("Executing first call to Ollama (tool detection)")
        response = await ollama_client.chat(payload)
        
        # Check for Tool Calls (Native)
        if "message" in response and "tool_calls" in response["message"]:
            tool_calls = response["message"]["tool_calls"]
            logger.info(f"Detected {len(tool_calls)} tool calls")
            
            # Add assistant's tool call message to history
            payload["messages"].append(response["message"])
            
            for tool_call in tool_calls:
                try:
                    func_name = tool_call["function"]["name"]
                    args = tool_call["function"]["arguments"]
                    
                    # Ensure args is a dict
                    if isinstance(args, str):
                        args = json.loads(args)
                    
                    if func_name in TOOL_MAP:
                        logger.info(f"Executing mock tool: {func_name} with args: {args}")
                        result = TOOL_MAP[func_name](**args)
                        
                        # Add tool result to history
                        payload["messages"].append({
                            "role": "tool",
                            "content": str(result)
                        })
                except Exception as tool_err:
                    logger.error(f"Error executing tool {tool_call}: {tool_err}")
                    payload["messages"].append({
                        "role": "tool",
                        "content": f"Error: {str(tool_err)}"
                    })
            
            # Second Call: Get the final answer with tool results
            logger.info("Executing second call to Ollama (final answer)")
            final_response = await ollama_client.chat(payload)
            return final_response

        # If streaming was requested and no tools were called, use the stream
        if request.stream:
            logger.info("Streaming response back to user")
            return StreamingResponse(
                ollama_client.chat_stream(payload),
                media_type="application/x-ndjson"
            )

        return response
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
