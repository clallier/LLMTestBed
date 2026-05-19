"""
Configuration module for the backend API application.

High level role: Loads environment variables and configures backend constants.
"""
import os

from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
