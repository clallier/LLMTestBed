"""
Configuration module for the backend API application.

High level role: Loads environment variables and configures backend constants.
"""
import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434"
