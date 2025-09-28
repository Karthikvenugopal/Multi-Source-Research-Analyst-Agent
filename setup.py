#!/usr/bin/env python3
"""
Setup script for the Multi-Source Research Analyst Agent
Helps users configure the environment and test the installation
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = [
        'langchain',
        'langgraph', 
        'langchain-openai',
        'tavily-python',
        'wikipedia-api',
        'arxiv',
        'python-dotenv',
        'gradio'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n📦 Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    
    return True

def check_env_file():
    """Check if .env file exists and has required keys"""
    env_file = Path('.env')
    
    if not env_file.exists():
        print("❌ .env file not found")
        print("Creating template .env file...")
        
        env_template = """# Multi-Source Research Analyst Agent Configuration
# Choose your preferred LLM provider (FREE options available!)

# 🆓 FREE OPTIONS (Recommended):
# HuggingFace (No API key required)
LLM_PROVIDER=huggingface
LLM_MODEL=microsoft/DialoGPT-medium

# OR Google Gemini (Free with API key)
# LLM_PROVIDER=google
# LLM_MODEL=gemini-1.5-flash
# GOOGLE_API_KEY=your_google_key_here

# 💰 PAID OPTION:
# LLM_PROVIDER=openai
# LLM_MODEL=gpt-3.5-turbo
# OPENAI_API_KEY=your_openai_api_key_here

# Required: Tavily API Key (FREE - get at https://tavily.com)
TAVILY_API_KEY=your_tavily_api_key_here

# Optional: Model configuration
# MAX_ITERATIONS=5
"""
        
        with open('.env', 'w') as f:
            f.write(env_template)
        
        print("✅ Created .env template file")
        print("🆓 FREE setup: Set LLM_PROVIDER=huggingface (no API key needed!)")
        print("⚠️  Please edit .env and configure your settings")
        return False
    
    # Check if API keys are set
    from dotenv import load_dotenv
    load_dotenv()
    
    llm_provider = os.getenv('LLM_PROVIDER', 'huggingface')
    tavily_key = os.getenv('TAVILY_API_KEY')
    
    print(f"🤖 LLM Provider: {llm_provider}")
    
    # Check Tavily API key
    if not tavily_key or tavily_key == 'your_tavily_api_key_here':
        print("❌ TAVILY_API_KEY not set in .env file")
        print("🆓 Get free key at: https://tavily.com")
        return False
    else:
        print("✅ TAVILY_API_KEY configured")
    
    # Check LLM provider specific requirements
    if llm_provider == 'huggingface':
        print("✅ HuggingFace (FREE - No API key required)")
        return True
    elif llm_provider == 'google':
        google_key = os.getenv('GOOGLE_API_KEY')
        if not google_key or google_key == 'your_google_key_here':
            print("❌ GOOGLE_API_KEY not set")
            print("🆓 Get free key at: https://makersuite.google.com/app/apikey")
            return False
        else:
            print("✅ Google Gemini configured (FREE)")
            return True
    elif llm_provider == 'openai':
        openai_key = os.getenv('OPENAI_API_KEY')
        if not openai_key or openai_key == 'your_openai_api_key_here':
            print("❌ OPENAI_API_KEY not set")
            print("💰 OpenAI requires paid API key")
            return False
        else:
            print("✅ OpenAI configured (PAID)")
            return True
    else:
        print(f"❌ Unknown LLM provider: {llm_provider}")
        return False

def test_imports():
    """Test if all modules can be imported"""
    try:
        from graph import ResearchGraph
        from nodes import AgentNodes
        from tools import ResearchTools
        from state import AgentState
        from evaluation import ResearchEvaluator
        print("✅ All modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def run_quick_test():
    """Run a quick test to verify the agent works"""
    print("\n🧪 Running quick test...")
    
    try:
        from graph import ResearchGraph
        research_graph = ResearchGraph()
        
        # Test with a simple question
        test_question = "What is artificial intelligence?"
        print(f"Testing with: {test_question}")
        
        result = research_graph.run(test_question)
        
        if result and result.get('report'):
            print("✅ Agent test successful!")
            print(f"📊 Quality Score: {result.get('research_quality_score', 0):.2f}")
            print(f"🔄 Iterations: {result.get('iterations', 0)}")
            return True
        else:
            print("❌ Agent test failed - no report generated")
            return False
            
    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Multi-Source Research Analyst Agent Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return False
    
    print("\n📦 Checking dependencies...")
    if not check_dependencies():
        print("\n❌ Please install missing dependencies:")
        print("pip install -r requirements.txt")
        return False
    
    print("\n🔑 Checking environment configuration...")
    if not check_env_file():
        print("\n❌ Please configure your API keys in .env file")
        return False
    
    print("\n📚 Testing imports...")
    if not test_imports():
        print("\n❌ Import test failed")
        return False
    
    print("\n🧪 Running agent test...")
    if not run_quick_test():
        print("\n❌ Agent test failed")
        return False
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Run the web interface: python app.py")
    print("2. Run the demo: python demo.py")
    print("3. Run tests: python test_agent.py")
    print("\n🌐 Web interface will be available at: http://localhost:7860")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
