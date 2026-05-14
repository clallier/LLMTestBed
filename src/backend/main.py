"""
Main API Application Entry Point.

High level role: Initializes the FastAPI application, mounts middlewares 
(like CORS), attaches all routers, serves static files, and configures a 
global exception handler.
"""
import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.api.router import api_router
from backend.core.config import STATIC_DIR
import logging
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LLMTestbed API")

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Catches any unhandled exceptions across the application.
    Logs the stack trace and returns a structured 500 JSON response.
    """
    logger.error(f"GLOBAL ERROR: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"message": str(exc), "traceback": traceback.format_exc()},
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routes
app.include_router(api_router)

# Serve static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def read_index():
    """Serves the main frontend index.html file."""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

if __name__ == "__main__":
    import uvicorn
    # Watch the src directory specifically
    watch_dir = os.path.dirname(os.path.abspath(__file__))
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, reload_dirs=[watch_dir])
