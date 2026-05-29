# LLMTestbed

Making a testbed to test LLM agent security against local LLM (using Ollama).

## Idea

Inspired from "Understanding Prompt Injection Techniques, Challenges, and Advanced Escalation by [Brian Vermeer](https://brianvermeer.nl/)" presentation at Devoxx Belgium 2025.

https://www.youtube.com/watch?v=72e_0WxaQl0

"**Prompt Injection** focuses on injecting commands into the model's input, which it then interprets as part of its own directives."
"**Jailbreaking** primarily aims to bypass content policies and safety guardrails that are baked into the model."

![Prompt Injection vs Jailbreaking](./docs/prompt-injection-vs-jailbreaking.png)

See https://github.com/elder-plinius/L1B3RT4S/ for more
creative prompt injection examples.

## Setup

Local setup for testing LLM agent security with Ollama.

1. **Ollama**:
   - Start server: `ollama serve`
   - Pull models:
     ```bash
     ollama pull llama3.2:latest
     ollama pull gemma4:e4b
     ollama pull qwen3.6:35b
     ```
2. **Project**:
   - Install `uv`: `curl -LsSf https://astral-sh/uv/install.sh | sh`
   - Sync deps: `uv sync --all-extras`

## Running

### 1. Local Execution (using `uv`)

- **Backend**: `uv run src/backend/main.py` (FastAPI on :8000)
- **Frontend**: `uv run streamlit run src/streamlit_app/app.py` (Streamlit)

### 2. Containerized Execution (using Apple `container` - alternative to Docker)

`container` permits to run the app inside a highly-isolated, native macOS micro-VM container:

#### A. Configure Ollama 
By default, Ollama only binds to `127.0.0.1`, which blocks connection requests from the container VM. 

You must configure it to listen on all interfaces (`0.0.0.0`):

- 🚨 Should be run from a secure environment

  ```bash
  OLLAMA_HOST=0.0.0.0 ollama serve
  ```

#### B. Build and start the Container

```bash
# 1. Start the container subsystem (if not already running)
container system start

# 2. Build the container image
container build -t testbed-app .

# 3. Start the container (mapping ports 8000 and 8501)
container run -p 8000:8000 -p 8501:8501 --name testbed-app testbed-app
```

Once running, access:
* 🎈 **Streamlit Frontend:** [http://localhost:8501](http://localhost:8501)
* ⚡ **FastAPI Backend:** [http://localhost:8000](http://localhost:8000)

*Note: To stop and clean up the container for the next run, execute `container stop testbed-app && container rm testbed-app`.*

### 3. Docker Compose (for Docker/Podman users)

You can use standard **Docker** or **Podman** instead of Apple's `container` tool, using the provided `docker-compose.yml`:

```bash
# Build and launch the services in the background (with live code reloading)
docker compose up --build
```

## Structure

- `src/backend`: FastAPI proxy for Ollama + Tool execution loop.
- `src/backend/core/tool_registry.py`: Define mock tools here.
- `src/streamlit_app`: Python-based chat UI.

## Notes

- Backend handles the "Agent Loop" (calls tools, feeds results back to LLM).
- Logs show full JSON history + model "thinking" if supported.

## Testing & Code Quality

The repository includes a suite of automated unit tests, end-to-end tests, and strict static analysis tools to maintain high modularity, type-safety, and logic bounds.

### 1. Automated Testing (pytest)

To sync development/testing optional dependencies and run the test suite:

```bash
# Sync optional dev packages
uv sync --all-extras

# Run full test suite (includes AST custom code smell checker)
uv run pytest
```

### 2. Static Analysis & Code Smell Tools

You can execute standard static code quality checkers locally using `uv`:

- **Linting & Style Checks (Ruff):** `uv run ruff check src/`
- **Static Refactoring & Smells (Pylint):** `uv run pylint src/`
- **Cognitive Complexity Analysis (Radon):** `uv run radon cc src/ -a`
- **Static Security Scanning (Bandit):** `uv run bandit -r src/`
