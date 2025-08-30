import uvicorn
import os
from .config import validate_environment
from .utils import setup_logger

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("📄 Loaded environment from .env file")
except ImportError:
    print("💡 python-dotenv not installed, using system environment variables")

logger = setup_logger(__name__)

def main():
    """Main startup function."""
    logger.info("🚀 Starting Business Insights AI Server...")
    
    # Validate environment
    if not validate_environment():
        logger.error("❌ Environment validation failed")
        logger.info("💡 Make sure to set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT in your environment")
        return
    
    # Start server
    logger.info("🌐 Starting FastAPI server...")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
