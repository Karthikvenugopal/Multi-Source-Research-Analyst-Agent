#!/usr/bin/env python3
"""
Quick fix script for Google Gemini model issues
Updates configuration to use the correct model name
"""

import os
from pathlib import Path

def fix_gemini_config():
    """Fix Google Gemini configuration"""
    print("🔧 Fixing Google Gemini Configuration")
    print("=" * 40)
    
    env_file = Path('.env')
    
    if not env_file.exists():
        print("❌ .env file not found")
        print("Please run: python setup.py")
        return False
    
    # Read current .env file
    with open('.env', 'r') as f:
        content = f.read()
    
    # Check if gemini-pro is being used
    if 'gemini-pro' in content:
        print("🔍 Found gemini-pro in configuration")
        
        # Replace with correct model name
        updated_content = content.replace('gemini-pro', 'gemini-1.5-flash')
        
        # Write updated content
        with open('.env', 'w') as f:
            f.write(updated_content)
        
        print("✅ Updated model name to gemini-1.5-flash")
        print("🔄 Please restart the application")
        return True
    else:
        print("✅ Configuration looks correct")
        return True

def check_google_api():
    """Check Google API configuration"""
    print("\n🔍 Checking Google API Configuration")
    print("-" * 40)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    google_key = os.getenv('GOOGLE_API_KEY')
    llm_provider = os.getenv('LLM_PROVIDER', 'huggingface')
    llm_model = os.getenv('LLM_MODEL', 'microsoft/DialoGPT-medium')
    
    print(f"🤖 LLM Provider: {llm_provider}")
    print(f"📝 LLM Model: {llm_model}")
    
    if llm_provider == 'google':
        if not google_key or google_key == 'your_google_key_here':
            print("❌ GOOGLE_API_KEY not configured")
            print("🆓 Get free key at: https://makersuite.google.com/app/apikey")
            return False
        else:
            print("✅ GOOGLE_API_KEY configured")
            return True
    else:
        print(f"ℹ️ Using {llm_provider} provider")
        return True

def main():
    """Main fix function"""
    print("🚀 Google Gemini Configuration Fix")
    print("=" * 50)
    
    # Fix configuration
    config_fixed = fix_gemini_config()
    
    # Check API configuration
    api_ok = check_google_api()
    
    if config_fixed and api_ok:
        print("\n🎉 Configuration fixed successfully!")
        print("\n📋 Next steps:")
        print("1. Restart the application: python app.py")
        print("2. If issues persist, try HuggingFace (no API key needed)")
        print("3. Set in .env: LLM_PROVIDER=huggingface")
    else:
        print("\n⚠️ Some issues remain")
        print("\n🆓 Recommended: Use HuggingFace (completely free)")
        print("Set in .env:")
        print("LLM_PROVIDER=huggingface")
        print("LLM_MODEL=microsoft/DialoGPT-medium")

if __name__ == "__main__":
    main()
