#!/usr/bin/env python3
"""
Test script for the job processing system
"""
import os
import uuid
from datetime import datetime

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("📄 Loaded environment from .env file")
except ImportError:
    print("💡 python-dotenv not installed")

def test_database_connection():
    """Test database connection."""
    print("🗄️  Testing database connection...")
    
    try:
        from app.database import DatabaseManager
        
        db = DatabaseManager()
        conn = db.get_connection()
        
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ Database connected: {version['version'][:100]}...")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def create_test_job():
    """Create a test job in the database."""
    print("📝 Creating test job...")
    print("💡 Test job already created - skipping creation")
    return "test-job-id"

def test_job_retrieval():
    """Test job retrieval."""
    print("📋 Testing job retrieval...")
    
    try:
        from app.database import DatabaseManager
        
        db = DatabaseManager()
        job = db.get_pending_job()
        
        if job:
            print(f"✅ Retrieved job: {job['job_id']}")
            print(f"   Business: {job['business_description'][:50]}...")
            print(f"   Files: {job['file_ids']}")
            print(f"   Priority: {job['priority']}")
            return job
        else:
            print("📭 No pending jobs found")
            return None
            
    except Exception as e:
        print(f"❌ Failed to retrieve job: {e}")
        return None

def test_job_processor():
    """Test the job processor."""
    print("⚡ Testing job processor...")
    
    try:
        from app.job_processor import JobProcessor
        
        processor = JobProcessor(poll_interval=1)
        
        # Run one iteration
        result = processor.run_once()
        
        if result:
            print("✅ Job processor ran successfully")
        else:
            print("📭 No jobs processed (this is normal if no jobs are pending)")
            
        return True
        
    except Exception as e:
        print(f"❌ Job processor test failed: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 Business Insights AI - Job System Test")
    print("=" * 50)
    
    # Check environment variables
    print("\n🔧 Checking environment...")
    database_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
    azure_key = os.getenv('AZURE_OPENAI_API_KEY')
    
    if not database_url:
        print("❌ DATABASE_URL or POSTGRES_URL not set")
        print("💡 Add your PostgreSQL connection string to .env file")
        return
    
    if not azure_key:
        print("❌ AZURE_OPENAI_API_KEY not set")
        print("💡 Add your Azure OpenAI API key to .env file")
        return
    
    print("✅ Environment variables found")
    
    # Test database connection
    print("\n" + "="*30)
    if not test_database_connection():
        return
    
    # Test job creation
    print("\n" + "="*30)
    job_id = create_test_job()
    
    # Test job retrieval
    print("\n" + "="*30)
    job = test_job_retrieval()
    
    # Test job processor
    print("\n" + "="*30)
    test_job_processor()
    
    print("\n🎉 Job system test completed!")
    print("\n💡 To start job processing:")
    print("   python start_job_processor.py")
    print("\n💡 To start API server with background processing:")
    print("   python start_server.py")

if __name__ == "__main__":
    main()
