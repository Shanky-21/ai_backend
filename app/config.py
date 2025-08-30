import os
from typing import Optional

# Environment variables
AZURE_OPENAI_API_KEY: Optional[str] = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT: Optional[str] = os.getenv("AZURE_OPENAI_ENDPOINT")
LANGCHAIN_API_KEY: Optional[str] = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "true")

# Azure OpenAI Configuration
AZURE_OPENAI_API_VERSION: str = "2024-02-01"
AZURE_DEPLOYMENT_NAME: str = "gpt-4o"  # Using gpt-4o deployment
LLM_TEMPERATURE: float = 0.1

# File Configuration
ALLOWED_FILE_EXTENSIONS = ['.csv', '.xlsx', '.xls']
MAX_FILE_SIZE_MB = 50

def validate_environment() -> bool:
    """Validate required environment variables are set."""
    if not AZURE_OPENAI_API_KEY:
        print("⚠️  AZURE_OPENAI_API_KEY not set")
        return False
    
    if not AZURE_OPENAI_ENDPOINT:
        print("⚠️  AZURE_OPENAI_ENDPOINT not set")
        return False
    
    print("✅ Environment variables validated")
    return True
