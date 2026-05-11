# LLMTestbed

Local setup for testing LLM agent security with Ollama.

## Setup
1. **Ollama**:
   - Start server: `ollama serve`
   - Pull models:
     ```bash
     ollama pull gemma4:e4b
     ollama pull qwen3.6:35b
     ```
2. **Project**:
   - Install `uv`: `curl -LsSf https://astral-sh/uv/install.sh | sh`
   - Sync deps: `uv sync`

## Running
- **Backend**: `uv run src/backend/main.py` (FastAPI on :8000)
- **Frontend 1**: `http://localhost:8000` (Web Components)
- **Frontend 2**: `uv run streamlit run src/streamlit_app/app.py` (Streamlit)

## Structure
- `src/backend`: FastAPI proxy for Ollama + Tool execution loop.
- `src/backend/core/tool_registry.py`: Define mock tools here.
- `src/front`: Vanilla JS / Web Components UI.
- `src/streamlit_app`: Python-based chat UI.

## Notes
- Backend handles the "Agent Loop" (calls tools, feeds results back to LLM).
- Logs show full JSON history + model "thinking" if supported.
- Use the "Vulnerable Agent" preset for testing injections.
