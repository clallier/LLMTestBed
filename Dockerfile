# Stage 1: Build the virtual environment using uv
FROM python:3.12-slim AS builder

# Install uv via pip to bypass the Docker Hub namespace authentication issue with the container CLI
RUN pip install uv

WORKDIR /app

# Enable bytecode compilation for performance optimization
ENV UV_COMPILE_BYTECODE=1

# Copy configuration files needed for installation
COPY pyproject.toml uv.lock ./

# Sync dependencies (frozen locks ensure reproducibility) without installing dev libraries
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Stage 2: Final runtime container
FROM python:3.12-slim

WORKDIR /app

# Copy virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv

# Prepend virtual environment path to activate it
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV OLLAMA_HOST="http://192.168.64.1:11434"

# Copy source code
COPY src/ /app/src/

# Expose ports for FastAPI (8000) and Streamlit (8501)
EXPOSE 8000
EXPOSE 8501
# Start the FastAPI backend and Streamlit frontend via the launcher script
CMD ["python", "src/launcher.py"]
