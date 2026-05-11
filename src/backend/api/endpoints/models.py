from fastapi import APIRouter, HTTPException
from core.ollama_client import ollama_client
from core.tool_registry import TOOLS

router = APIRouter()

@router.get("/health")
async def health_check():
    try:
        models = await ollama_client.list_models()
        return {"status": "ok", "ollama": "connected", "model_count": len(models)}
    except Exception as e:
        return {"status": "ok", "ollama": "disconnected", "error": str(e)}

@router.get("/models")
async def list_models():
    try:
        return await ollama_client.list_models()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tools")
async def list_tools():
    return TOOLS
