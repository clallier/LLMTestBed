"""
Constants for the Streamlit frontend application component system.

High level role: Encapsulates all public/shared styling, role markers, and configurations.
"""

import os

# Backend API Configuration
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")

# UI Styling & Role Markers
AVATAR_TOOLS: str = "⚙️"
ROLE_TOOLS: str = "tools"
ROLE_USER: str = "user"
ROLE_ASSISTANT: str = "assistant"
