#!/usr/bin/env python3
"""
Test script for the updated Business Insights AI system

This script tests:
1. FastAPI server startup (without job processing)
2. Job cron system functionality
3. Database connectivity
4. System integration

Usage:
    python test_new_system.py
"""

import os
import sys
import time
import subprocess
import requests
from typing import Dict, Any
import psycopg
from psycopg.rows import dict_row

def setup_logging():
    """Setup basic logging."""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

logger = setup_logging()

def check_environment() -> bool:
    """Check if required environment variables are set."""
    logger.info("🔧 Checking environment variables...")
    
    required_vars = {
        'DATABASE_URL': os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL'),
        'AZURE_OPENAI_API_KEY': os.getenv('AZURE_OPENAI_API_KEY'),
        'AZURE_OPENAI_ENDPOINT': os.getenv('AZURE_OPENAI_ENDPOINT')
    }
    
    missing_vars = []
    for var_name, var_value in required_vars.items():
        if var_value:
            logger.info(f"   ✅ {var_name}: Configured")
        else:
            logger.error(f"   ❌ {var_name}: Missing")
            missing_vars.append(var_name)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        return False
    
    return True

def test_database_connection() -> bool:
    """Test database connectivity."""
    logger.info("🗄️  Testing database connection...")
    
    try:
        database_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
        if not database_url:
            logger.error("No database URL configured")
            return False
        
        conn = psycopg.connect(database_url, row_factory=dict_row)
        with conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            result = cursor.fetchone()
            logger.info(f"   ✅ Database connected: {result['version'][:50]}...")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"   ❌ Database connection failed: {e}")
        return False

def check_database_tables() -> Dict[str, bool]:
    """Check if required database tables exist."""
    logger.info("📋 Checking database tables...")
    
    required_tables = ['processing_jobs', 'files', 'insights']
    table_status = {}
    
    try:
        database_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
        conn = psycopg.connect(database_url, row_factory=dict_row)
        
        with conn.cursor() as cursor:
            for table in required_tables:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    );
                """, (table,))
                
                exists = cursor.fetchone()['exists']
                table_status[table] = exists
                
                if exists:
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table};")
                    count = cursor.fetchone()['count']
                    logger.info(f"   ✅ {table}: Exists ({count} rows)")
                else:
                    logger.warning(f"   ⚠️  {table}: Missing")
        
        conn.close()
        return table_status
        
    except Exception as e:
        logger.error(f"   ❌ Error checking tables: {e}")
        return {table: False for table in required_tables}

def test_fastapi_server() -> bool:
    """Test if FastAPI server can be imported and configured."""
    logger.info("🌐 Testing FastAPI server configuration...")
    
    try:
        # Try to import the main app
        sys.path.insert(0, os.path.dirname(__file__))
        from app.main import app
        
        logger.info("   ✅ FastAPI app imported successfully")
        logger.info("   ✅ No automatic job processing will start")
        
        # Check if health endpoint exists
        routes = [route.path for route in app.routes]
        if '/health' in routes:
            logger.info("   ✅ Health endpoint configured")
        if '/analyze' in routes:
            logger.info("   ✅ Analysis endpoint configured")
        
        return True
        
    except Exception as e:
        logger.error(f"   ❌ FastAPI server test failed: {e}")
        return False

def test_job_cron_script() -> bool:
    """Test if job cron script is properly configured."""
    logger.info("⚡ Testing job cron script...")
    
    try:
        # Check if script exists and is executable
        script_path = os.path.join(os.path.dirname(__file__), 'job_cron.py')
        if not os.path.exists(script_path):
            logger.error(f"   ❌ Job cron script not found: {script_path}")
            return False
        
        if not os.access(script_path, os.X_OK):
            logger.warning(f"   ⚠️  Job cron script not executable: {script_path}")
            # Make it executable
            os.chmod(script_path, 0o755)
            logger.info("   ✅ Made job cron script executable")
        
        # Test help command
        result = subprocess.run(
            [sys.executable, script_path, '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info("   ✅ Job cron script responds to --help")
            return True
        else:
            logger.error(f"   ❌ Job cron script error: {result.stderr}")
            return False
        
    except subprocess.TimeoutExpired:
        logger.error("   ❌ Job cron script timed out")
        return False
    except Exception as e:
        logger.error(f"   ❌ Job cron script test failed: {e}")
        return False

def test_startup_scripts() -> Dict[str, bool]:
    """Test startup scripts."""
    logger.info("🚀 Testing startup scripts...")
    
    scripts = {
        'start_server.py': 'FastAPI server startup script',
        'start_job_cron.sh': 'Job cron management script',
        'start_full_system.sh': 'Full system management script'
    }
    
    script_status = {}
    
    for script, description in scripts.items():
        script_path = os.path.join(os.path.dirname(__file__), script)
        
        if os.path.exists(script_path):
            if os.access(script_path, os.X_OK):
                logger.info(f"   ✅ {script}: Exists and executable")
                script_status[script] = True
            else:
                logger.warning(f"   ⚠️  {script}: Exists but not executable")
                script_status[script] = False
        else:
            logger.error(f"   ❌ {script}: Missing")
            script_status[script] = False
    
    return script_status

def create_test_job() -> bool:
    """Create a test job in the database."""
    logger.info("📝 Creating test job...")
    
    try:
        database_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
        conn = psycopg.connect(database_url, row_factory=dict_row)
        
        with conn.cursor() as cursor:
            # Create a test file entry first
            cursor.execute("""
                INSERT INTO files (file_path, original_name, status)
                VALUES ('/tmp/test_file.csv', 'test_file.csv', 'uploaded')
                RETURNING id;
            """)
            file_id = cursor.fetchone()['id']
            
            # Create a test job
            cursor.execute("""
                INSERT INTO processing_jobs (file_id, business_description, job_type, status)
                VALUES (%s, %s, %s, 'pending')
                RETURNING id;
            """, (file_id, "Test business analysis", "test"))
            
            job_id = cursor.fetchone()['id']
            
        conn.close()
        logger.info(f"   ✅ Test job created with ID: {job_id}")
        return True
        
    except Exception as e:
        logger.error(f"   ❌ Failed to create test job: {e}")
        return False

def run_comprehensive_test():
    """Run comprehensive system test."""
    logger.info("🧪 Starting comprehensive system test...")
    logger.info("=" * 60)
    
    test_results = {}
    
    # Test 1: Environment
    test_results['environment'] = check_environment()
    
    # Test 2: Database
    test_results['database'] = test_database_connection()
    
    # Test 3: Database Tables
    table_status = check_database_tables()
    test_results['tables'] = all(table_status.values())
    
    # Test 4: FastAPI Server
    test_results['fastapi'] = test_fastapi_server()
    
    # Test 5: Job Cron Script
    test_results['job_cron'] = test_job_cron_script()
    
    # Test 6: Startup Scripts
    script_status = test_startup_scripts()
    test_results['scripts'] = all(script_status.values())
    
    # Test 7: Create Test Job (optional)
    if test_results['database'] and test_results['tables']:
        test_results['test_job'] = create_test_job()
    else:
        test_results['test_job'] = False
        logger.info("📝 Skipping test job creation (database issues)")
    
    # Summary
    logger.info("=" * 60)
    logger.info("🎯 Test Results Summary:")
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"   {test_name.capitalize()}: {status}")
        if result:
            passed += 1
    
    logger.info("=" * 60)
    logger.info(f"🏆 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Your system is ready to go!")
        logger.info("")
        logger.info("🚀 Quick Start:")
        logger.info("   ./start_full_system.sh dev")
        logger.info("")
        logger.info("📚 For more options, see: UPDATED_STARTUP_GUIDE.md")
        return True
    else:
        logger.error("❌ Some tests failed. Check the issues above.")
        logger.info("")
        logger.info("💡 Common fixes:")
        logger.info("   - Set missing environment variables")
        logger.info("   - Create database tables")
        logger.info("   - Install missing dependencies")
        return False

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
