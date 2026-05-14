"""
Main API Router for the LLM Testbed Backend.

High level role: This module aggregates all individual endpoint routers (chat, system, etc.) 
into a single APIRouter instance. It serves as the primary entry point for the FastAPI 
application's routing logic, ensuring that all functional areas are correctly mounted 
and tagged for documentation (Swagger/Redoc).

How it works: It imports the sub-routers from the endpoints directory and includes them 
into the global 'api_router' object with appropriate metadata.
"""
from fastapi import APIRouter
from backend.api.endpoints import chat, system

api_router = APIRouter()
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(system.router, tags=["system"])
