#!/usr/bin/env python3
"""
Complete system test for Business Insights AI
"""
import os
import sys

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("📄 Loaded environment from .env file")
except ImportError:
    print("💡 python-dotenv not installed, using system environment variables")

def test_environment():
    """Test environment setup."""
    print("🔧 Testing environment setup...")
    
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    
    if not azure_key:
        print("❌ AZURE_OPENAI_API_KEY not set")
        return False
    
    if not azure_endpoint:
        print("❌ AZURE_OPENAI_ENDPOINT not set")
        return False
    
    print("✅ Azure OpenAI environment variables found")
    return True

def test_imports():
    """Test all imports work."""
    print("📦 Testing imports...")
    
    try:
        from app.config import validate_environment
        from app.ai_workflow import run_complete_workflow
        from tests.test_basic_workflow import test_workflow_with_real_data, list_available_files
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def run_complete_test():
    """Run the complete system test."""
    print("🚀 Business Insights AI - Complete System Test")
    print("=" * 60)
    
    if not test_environment():
        print("💡 Please set up your environment variables:")
        print("   export AZURE_OPENAI_API_KEY=your_azure_key_here")
        print("   export AZURE_OPENAI_ENDPOINT=https://your-endpoint.cognitiveservices.azure.com/")
        print("   export LANGCHAIN_TRACING_V2=true")
        return
    
    if not test_imports():
        print("💡 Please check your package installations")
        return
    
    print("\n🧪 Running workflow test...")
    from tests.test_basic_workflow import test_workflow_with_real_data
    test_workflow_with_real_data()
    
    print("\n🎉 Complete system test finished!")
    print("🌐 You can now start the server with: python start_server.py")

if __name__ == "__main__":
    run_complete_test()
