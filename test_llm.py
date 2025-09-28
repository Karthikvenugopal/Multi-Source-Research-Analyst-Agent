#!/usr/bin/env python3
"""
Test script to debug LLM response format
Helps identify the exact response structure from different providers
"""

from llm_manager import LLMManager
import json

def test_llm_response():
    """Test LLM response format"""
    print("🧪 Testing LLM Response Format")
    print("=" * 40)
    
    try:
        # Initialize LLM manager
        llm_manager = LLMManager()
        
        # Test prompt
        test_prompt = "What is artificial intelligence? Please answer in one sentence."
        
        print(f"🤖 Provider: {llm_manager.provider}")
        print(f"📝 Model: {llm_manager.model}")
        print(f"🔍 Test prompt: {test_prompt}")
        print("-" * 40)
        
        # Get response
        response = llm_manager.invoke(test_prompt)
        
        print(f"📤 Response type: {type(response)}")
        print(f"📤 Response: {response}")
        print("-" * 40)
        
        # Check response attributes
        if hasattr(response, '__dict__'):
            print("🔍 Response attributes:")
            for attr in dir(response):
                if not attr.startswith('_'):
                    try:
                        value = getattr(response, attr)
                        if not callable(value):
                            print(f"  {attr}: {type(value)} = {value}")
                    except:
                        pass
        
        # Test different access methods
        print("\n🧪 Testing different access methods:")
        
        if hasattr(response, 'content'):
            print(f"✅ response.content: {response.content}")
        else:
            print("❌ No 'content' attribute")
            
        if hasattr(response, 'text'):
            print(f"✅ response.text: {response.text}")
        else:
            print("❌ No 'text' attribute")
            
        if isinstance(response, str):
            print(f"✅ Direct string: {response}")
        else:
            print("❌ Not a string")
        
        print("\n✅ LLM test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing LLM: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("🚀 LLM Response Format Test")
    print("=" * 50)
    
    success = test_llm_response()
    
    if success:
        print("\n🎉 Test completed! The LLM is working correctly.")
        print("You can now run: python app.py")
    else:
        print("\n❌ Test failed. Please check your configuration.")
        print("\n🆓 Try switching to HuggingFace (completely free):")
        print("Set in .env: LLM_PROVIDER=huggingface")

if __name__ == "__main__":
    main()
