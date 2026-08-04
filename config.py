# config.py
import os
from dotenv import load_dotenv

load_dotenv()


def _env_int(name: str, default: int) -> int:
    """Read a positive integer setting with a safe fallback."""
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    """Read a positive float setting with a safe fallback."""
    try:
        return max(0.1, float(os.getenv(name, str(default))))
    except ValueError:
        return default

class Config:
    # API Keys - Support multiple providers
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # LLM Configuration - Choose your preferred provider.
    # Default is Google Gemini Flash: free with an API key and, unlike small
    # local chat models, capable enough to follow the agent's reasoning prompts.
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google")  # Options: google, openai, huggingface
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")

    # Model options by provider:
    # Google:      "gemini-2.5-flash", "gemini-2.5-pro" (free tier, requires GOOGLE_API_KEY)
    # OpenAI:      "gpt-4o-mini", "gpt-4o" (paid, requires OPENAI_API_KEY)
    # HuggingFace: local models — experimental; most small models cannot follow
    #              the supervisor/synthesis prompts well enough for usable output.
    
    # Agent configuration
    MAX_ITERATIONS = _env_int("RESEARCH_MAX_ITERATIONS", 5)
    MAX_TOOL_CALLS = _env_int("RESEARCH_MAX_TOOL_CALLS", 6)
    TOOL_TIMEOUT_SECONDS = _env_float("RESEARCH_TOOL_TIMEOUT_SECONDS", 20.0)
    MAX_CONTEXT_CHARS = _env_int("RESEARCH_MAX_CONTEXT_CHARS", 14000)
    MAX_EVIDENCE_CHARS = _env_int("RESEARCH_MAX_EVIDENCE_CHARS", 4000)
    WEB_RESULT_LIMIT = _env_int("WEB_RESULT_LIMIT", 5)
    WIKIPEDIA_RESULT_LIMIT = _env_int("WIKIPEDIA_RESULT_LIMIT", 3)
    ARXIV_RESULT_LIMIT = _env_int("ARXIV_RESULT_LIMIT", 3)
