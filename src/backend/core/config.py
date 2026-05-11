import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
PROJECT_ROOT = "/Users/corentin/Documents/GitHub/testbed"
STATIC_DIR = os.path.join(PROJECT_ROOT, "src/front")
