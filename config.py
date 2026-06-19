# config.py
import os
from dotenv import load_dotenv

load_dotenv()

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
    LLM_MODEL = os.getenv("LLM_MODEL", "gemini-1.5-flash")

    # Model options by provider:
    # Google:      "gemini-1.5-flash", "gemini-1.5-pro" (free tier, requires GOOGLE_API_KEY)
    # OpenAI:      "gpt-4o-mini", "gpt-4o" (paid, requires OPENAI_API_KEY)
    # HuggingFace: local models — experimental; most small models cannot follow
    #              the supervisor/synthesis prompts well enough for usable output.
    
    # Agent configuration
    MAX_ITERATIONS = 5