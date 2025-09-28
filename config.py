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
    
    # LLM Configuration - Choose your preferred provider
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "huggingface")  # Options: openai, huggingface, google
    LLM_MODEL = os.getenv("LLM_MODEL", "microsoft/DialoGPT-medium")  # Free HuggingFace model
    
    # Free model options:
    # HuggingFace: "microsoft/DialoGPT-medium", "facebook/blenderbot-400M-distill"
    # Google: "gemini-1.5-flash" (requires GOOGLE_API_KEY)
    # OpenAI: "gpt-3.5-turbo" (requires OPENAI_API_KEY)
    
    # Agent configuration
    MAX_ITERATIONS = 5