#!/usr/bin/env python3
"""
Standalone job processor for Business Insights AI
Monitors PostgreSQL for analysis jobs and processes them
"""
import os
import sys

# Try to load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("📄 Loaded environment from .env file")
except ImportError:
    print("💡 python-dotenv not installed, using system environment variables")

def main():
    """Main function to start job processor."""
    from app.job_processor import JobProcessor
    from app.config import validate_environment
    from app.utils import setup_logger
    
    logger = setup_logger(__name__)
    
    # Validate environment
    logger.info("🔧 Validating environment...")
    if not validate_environment():
        logger.error("❌ Environment validation failed")
        logger.info("💡 Make sure to set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT")
        return
    
    # Check database connection
    database_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
    if not database_url:
        logger.error("❌ DATABASE_URL or POSTGRES_URL not set")
        logger.info("💡 Set your PostgreSQL connection string in environment variables")
        return
    
    logger.info("✅ Environment validated")
    logger.info(f"🗄️  Database: {database_url.split('@')[1] if '@' in database_url else 'configured'}")
    
    # Start job processor
    poll_interval = int(os.getenv('JOB_POLL_INTERVAL', '5'))
    processor = JobProcessor(poll_interval=poll_interval)
    
    logger.info("🚀 Starting Business Insights AI Job Processor...")
    logger.info(f"⏰ Polling interval: {poll_interval} seconds")
    logger.info("Press Ctrl+C to stop")
    
    try:
        processor.start_monitoring()
    except KeyboardInterrupt:
        logger.info("👋 Received shutdown signal")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        return 1
    finally:
        processor.stop_monitoring()
        logger.info("🏁 Job processor stopped")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
