from fastapi import APIRouter, HTTPException
from backend.core.ollama_client import ollama_client
from backend.core.tool_registry import TOOLS

router = APIRouter()

@router.get("/health", summary="Health Check")
async def health_check():
    """Verifies backend connectivity to the Ollama server."""
    try:
        models = await ollama_client.list_models()
        return {"status": "ok", "ollama": "connected", "model_count": len(models)}
    except Exception as e:
        return {"status": "ok", "ollama": "disconnected", "error": str(e)}

@router.get("/models", summary="List Models")
async def list_models():
    """Retrieves the list of available models from the local Ollama instance."""
    try:
        return await ollama_client.list_models()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tools", summary="List Tools")
async def list_tools():
    """Returns the registry of mock security tools available to the agent."""
    return TOOLS
