"""
LLM Manager for Multi-Source Research Analyst Agent
Supports multiple free and paid LLM providers
"""

from typing import Optional, Dict, Any
import os
from config import Config

class LLMManager:
    """Manages different LLM providers with fallback options"""
    
    def __init__(self):
        self.provider = Config.LLM_PROVIDER
        self.model = Config.LLM_MODEL
        self.llm = self._initialize_llm()
    
    def _initialize_llm(self):
        """Initialize the appropriate LLM based on configuration"""
        try:
            if self.provider == "huggingface":
                return self._init_huggingface()
            elif self.provider == "google":
                return self._init_google()
            elif self.provider == "openai":
                return self._init_openai()
            else:
                # Fallback to HuggingFace
                print("⚠️ Unknown provider, falling back to HuggingFace")
                return self._init_huggingface()
        except Exception as e:
            print(f"❌ Error initializing {self.provider}: {e}")
            print("🔄 Falling back to HuggingFace...")
            return self._init_huggingface()
    
    def _init_huggingface(self):
        """Initialize HuggingFace model (FREE)"""
        try:
            from langchain_huggingface import HuggingFacePipeline
            from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
            
            print(f"🤗 Initializing HuggingFace model: {self.model}")
            
            # Load model and tokenizer
            tokenizer = AutoTokenizer.from_pretrained(self.model)
            model = AutoModelForCausalLM.from_pretrained(self.model)
            
            # Create pipeline
            pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                max_length=512,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
            
            # Create LangChain wrapper
            llm = HuggingFacePipeline(pipeline=pipe)
            print("✅ HuggingFace model loaded successfully")
            return llm
            
        except ImportError:
            print("❌ HuggingFace dependencies not installed")
            print("📦 Install with: pip install langchain-huggingface transformers torch")
            raise
        except Exception as e:
            print(f"❌ Error loading HuggingFace model: {e}")
            raise
    
    def _init_google(self):
        """Initialize Google Gemini model (FREE with API key)"""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            if not Config.GOOGLE_API_KEY:
                raise ValueError("GOOGLE_API_KEY not found in environment")
            
            # Use the correct model name for current API
            model_name = "gemini-1.5-flash" if self.model == "gemini-pro" else self.model
            
            print(f"🔍 Initializing Google Gemini model: {model_name}")
            llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=Config.GOOGLE_API_KEY,
                temperature=0.7
            )
            print("✅ Google Gemini model loaded successfully")
            return llm
            
        except ImportError:
            print("❌ Google dependencies not installed")
            print("📦 Install with: pip install langchain-google-genai")
            raise
        except Exception as e:
            print(f"❌ Error loading Google model: {e}")
            print("🔄 Falling back to HuggingFace...")
            return self._init_huggingface()
    
    def _init_openai(self):
        """Initialize OpenAI model (PAID)"""
        try:
            from langchain_openai import ChatOpenAI
            
            if not Config.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not found in environment")
            
            print(f"🤖 Initializing OpenAI model: {self.model}")
            llm = ChatOpenAI(
                model=self.model,
                openai_api_key=Config.OPENAI_API_KEY,
                temperature=0.7
            )
            print("✅ OpenAI model loaded successfully")
            return llm
            
        except ImportError:
            print("❌ OpenAI dependencies not installed")
            print("📦 Install with: pip install langchain-openai")
            raise
        except Exception as e:
            print(f"❌ Error loading OpenAI model: {e}")
            raise
    
    def invoke(self, prompt: str) -> str:
        """Invoke the LLM with a prompt"""
        try:
            if hasattr(self.llm, 'invoke'):
                response = self.llm.invoke(prompt)
                
                # Handle different response formats
                if hasattr(response, 'content'):
                    return response.content
                elif isinstance(response, str):
                    return response
                elif hasattr(response, 'text'):
                    return response.text
                else:
                    return str(response)
            else:
                # Fallback for different response formats
                response = self.llm(prompt)
                if isinstance(response, str):
                    return response
                elif hasattr(response, 'content'):
                    return response.content
                else:
                    return str(response)
        except Exception as e:
            print(f"❌ Error invoking LLM: {e}")
            return f"Error: {str(e)}"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        return {
            "provider": self.provider,
            "model": self.model,
            "is_free": self.provider in ["huggingface"],
            "requires_api_key": self.provider in ["google", "openai"]
        }

# Free model recommendations
FREE_MODELS = {
    "huggingface": [
        "microsoft/DialoGPT-medium",
        "facebook/blenderbot-400M-distill", 
        "microsoft/DialoGPT-small",
        "facebook/blenderbot-90M"
    ],
    "google": [
        "gemini-pro"  # Requires free API key
    ]
}

def get_free_setup_instructions():
    """Get setup instructions for free models"""
    return """
🆓 FREE LLM Setup Instructions

1. 🤗 HuggingFace (Completely Free - No API Key Required):
   - Install: pip install langchain-huggingface transformers torch
   - Set in .env: LLM_PROVIDER=huggingface
   - Set in .env: LLM_MODEL=microsoft/DialoGPT-medium

2. 🔍 Google Gemini (Free with API Key):
   - Get free API key: https://makersuite.google.com/app/apikey
   - Install: pip install langchain-google-genai
   - Set in .env: LLM_PROVIDER=google
   - Set in .env: LLM_MODEL=gemini-pro
   - Set in .env: GOOGLE_API_KEY=your_key_here

3. 🤖 OpenAI (Paid):
   - Requires paid API key
   - Set in .env: LLM_PROVIDER=openai
   - Set in .env: LLM_MODEL=gpt-3.5-turbo
   - Set in .env: OPENAI_API_KEY=your_key_here

Recommended for free usage: HuggingFace (no API key required)
"""
