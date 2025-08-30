#!/usr/bin/env python3
"""
Check environment variables and .env file
"""
import os

# Try to load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("📄 Loaded environment from .env file")
except ImportError:
    print("💡 python-dotenv not installed")

print("\n🔧 Environment Variables:")
print(f"AZURE_OPENAI_API_KEY: {'✅ SET' if os.getenv('AZURE_OPENAI_API_KEY') else '❌ NOT SET'}")
print(f"AZURE_OPENAI_ENDPOINT: {'✅ SET' if os.getenv('AZURE_OPENAI_ENDPOINT') else '❌ NOT SET'}")

if os.getenv('AZURE_OPENAI_API_KEY'):
    key = os.getenv('AZURE_OPENAI_API_KEY')
    print(f"API Key preview: {key[:20]}...{key[-4:] if len(key) > 24 else key}")

if os.getenv('AZURE_OPENAI_ENDPOINT'):
    print(f"Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")

print("\n📄 .env file contents:")
try:
    with open('.env', 'r') as f:
        content = f.read()
        print(content)
except FileNotFoundError:
    print("❌ .env file not found")
except Exception as e:
    print(f"❌ Error reading .env: {e}")

# Test the configuration
print("\n🧪 Testing configuration:")
try:
    from app.config import validate_environment
    if validate_environment():
        print("✅ Environment validation passed!")
    else:
        print("❌ Environment validation failed!")
except Exception as e:
    print(f"❌ Error testing config: {e}")
