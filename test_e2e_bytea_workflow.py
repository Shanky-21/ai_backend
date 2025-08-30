#!/usr/bin/env python3
"""
End-to-End test for the Business Insights AI system with bytea file support.

This script tests the complete workflow:
1. Creates a test file with bytea data in the database
2. Creates a processing job for that file
3. Simulates job_cron.py processing the job
4. Verifies insights are generated and stored correctly

Usage:
    python test_e2e_bytea_workflow.py
"""

import os
import sys
import uuid
import json
import time
from typing import Dict, Any, List, Optional
import psycopg
from psycopg.rows import dict_row
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database import DatabaseManager
from app.ai_workflow import run_complete_workflow
from app.utils import setup_logger

logger = setup_logger(__name__)

class E2ETestRunner:
    """End-to-end test runner for the complete bytea workflow."""
    
    def __init__(self):
        """Initialize the test runner."""
        self.db = DatabaseManager()
        self.test_file_id = None
        self.test_job_id = None
        self.cleanup_items = []
        
    def create_test_csv_data(self) -> bytes:
        """Create realistic test CSV data as bytes."""
        test_data = """Date,Product,Category,Sales,Quantity,Customer_Type,Region
2024-01-15,Laptop Pro,Electronics,1299.99,1,Business,North
2024-01-15,Office Chair,Furniture,299.99,2,Business,South
2024-01-16,Smartphone X,Electronics,899.99,1,Consumer,East
2024-01-16,Desk Lamp,Furniture,79.99,3,Consumer,West
2024-01-17,Tablet Air,Electronics,599.99,2,Consumer,North
2024-01-17,Bookshelf,Furniture,199.99,1,Business,South
2024-01-18,Wireless Mouse,Electronics,49.99,5,Consumer,East
2024-01-18,Standing Desk,Furniture,499.99,1,Business,West
2024-01-19,Monitor 4K,Electronics,399.99,2,Business,North
2024-01-19,Filing Cabinet,Furniture,149.99,1,Business,South
2024-01-20,Keyboard Pro,Electronics,129.99,3,Consumer,East
2024-01-20,Conference Table,Furniture,799.99,1,Business,West
2024-01-21,Headphones,Electronics,199.99,4,Consumer,North
2024-01-21,Ergonomic Chair,Furniture,449.99,2,Business,South
2024-01-22,Webcam HD,Electronics,89.99,6,Consumer,East"""
        
        return test_data.encode('utf-8')
    
    def create_test_file_in_db(self) -> str:
        """Create a test file with bytea data in the database."""
        logger.info("📁 Creating test file with bytea data...")
        
        try:
            csv_data = self.create_test_csv_data()
            file_id = str(uuid.uuid4())
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO files (
                            id, filename, original_name, file_path, files_data, 
                            mime_type, file_size, status, upload_date
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING id;
                    """, (
                        file_id,
                        'test_sales_data.csv',
                        'sales_data_2024.csv',
                        None,  # No file path - using bytea data
                        csv_data,
                        'text/csv',
                        len(csv_data),
                        'uploaded'
                    ))
                    
                    result = cursor.fetchone()
                    self.test_file_id = result['id']
                    self.cleanup_items.append(('file', self.test_file_id))
                    
            logger.info(f"✅ Test file created with ID: {self.test_file_id}")
            logger.info(f"   File size: {len(csv_data)} bytes")
            logger.info(f"   Data type: bytea (no file path)")
            
            return self.test_file_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create test file: {e}")
            raise
    
    def create_test_job(self, file_id: str) -> str:
        """Create a test processing job."""
        logger.info("📋 Creating test processing job...")
        
        try:
            job_id = str(uuid.uuid4())
            business_description = """
            We are a mid-size retail company analyzing our sales data to understand:
            - Product performance across different categories
            - Customer purchasing patterns (Business vs Consumer)
            - Regional sales distribution
            - Revenue trends and opportunities for growth
            
            We need insights to optimize our inventory, improve customer targeting, 
            and identify the most profitable product-region combinations.
            """
            
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO processing_jobs (
                            id, file_id, business_description, job_type, 
                            status, created_at, metadata
                        )
                        VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
                        RETURNING id;
                    """, (
                        job_id,
                        file_id,
                        business_description.strip(),
                        'sales_analysis',
                        'not-started',
                        json.dumps({
                            'test_run': True,
                            'expected_insights': ['sales_trends', 'customer_analysis', 'regional_performance'],
                            'data_source': 'bytea'
                        })
                    ))
                    
                    result = cursor.fetchone()
                    self.test_job_id = result['id']
                    self.cleanup_items.append(('job', self.test_job_id))
                    
            logger.info(f"✅ Test job created with ID: {self.test_job_id}")
            logger.info(f"   File ID: {file_id}")
            logger.info(f"   Status: not-started")
            
            return self.test_job_id
            
        except Exception as e:
            logger.error(f"❌ Failed to create test job: {e}")
            raise
    
    def simulate_job_processing(self, job_id: str) -> Dict[str, Any]:
        """Simulate the job_cron.py processing logic."""
        logger.info("⚡ Simulating job processing...")
        
        try:
            # Step 1: Get the job (simulate get_pending_job)
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Mark job as in-progress
                    cursor.execute("""
                        UPDATE processing_jobs 
                        SET status = 'in-progress', 
                            started_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        RETURNING id, file_id, business_description, job_type, metadata;
                    """, (job_id,))
                    
                    job_data = cursor.fetchone()
                    if not job_data:
                        raise ValueError(f"Job {job_id} not found")
            
            # Step 2: Get file data objects (using the new bytea support)
            file_ids = [str(job_data['file_id'])]
            file_objects = self.db.get_file_data(file_ids)
            
            if not file_objects:
                raise ValueError(f"No file objects found for IDs: {file_ids}")
            
            logger.info(f"📁 Retrieved {len(file_objects)} file objects")
            
            # Log file object details
            for file_obj in file_objects:
                has_bytea = bool(file_obj.get('files_data'))
                has_path = bool(file_obj.get('file_path'))
                filename = file_obj.get('original_name', 'unknown')
                file_size = file_obj.get('file_size', 0)
                logger.info(f"   📄 {filename}: bytea={has_bytea}, path={has_path}, size={file_size}")
            
            # Step 3: Run the AI workflow
            logger.info("🤖 Running AI workflow with file objects...")
            result = run_complete_workflow(file_objects, job_data['business_description'])
            
            # Step 4: Update job status and save results
            if result['status'] == 'success':
                # Save results to database
                self.db.save_analysis_results(job_id, result['data'])
                self.db.update_job_status(job_id, 'completed')
                
                insights_count = len(result['data'].get('final_insights', []))
                logger.info(f"✅ Job processing completed - {insights_count} insights generated")
                
                return {
                    'status': 'success',
                    'job_id': job_id,
                    'insights_count': insights_count,
                    'workflow_result': result
                }
            else:
                error_msg = result.get('error', 'Unknown workflow error')
                self.db.update_job_status(job_id, 'failed', error_msg)
                logger.error(f"❌ Workflow failed: {error_msg}")
                
                return {
                    'status': 'failed',
                    'job_id': job_id,
                    'error': error_msg
                }
                
        except Exception as e:
            logger.error(f"❌ Job processing simulation failed: {e}")
            # Update job status to failed
            try:
                self.db.update_job_status(job_id, 'failed', str(e))
            except:
                pass
            
            return {
                'status': 'error',
                'job_id': job_id,
                'error': str(e)
            }
    
    def verify_insights_storage(self, job_id: str) -> Dict[str, Any]:
        """Verify that insights were stored correctly in the database."""
        logger.info("🔍 Verifying insights storage...")
        
        try:
            insights_data = self.db.get_insights_by_job_id(job_id)
            
            if not insights_data:
                return {
                    'status': 'failed',
                    'error': 'No insights found in database',
                    'insights_count': 0
                }
            
            # Extract insights details
            individual_insights = insights_data.get('individual_insights', [])
            summary = insights_data.get('summary', {})
            confidence_score = insights_data.get('confidence_score', 0)
            
            logger.info(f"📊 Insights verification results:")
            logger.info(f"   Total insights: {len(individual_insights)}")
            logger.info(f"   Confidence score: {confidence_score:.2f}")
            logger.info(f"   Insight types: {insights_data.get('insight_type', 'Unknown')}")
            
            # Verify insight content
            valid_insights = 0
            for i, insight in enumerate(individual_insights):
                if isinstance(insight, dict):
                    has_title = bool(insight.get('title'))
                    has_findings = bool(insight.get('key_findings'))
                    has_recommendations = bool(insight.get('recommendations'))
                    
                    if has_title and (has_findings or has_recommendations):
                        valid_insights += 1
                    
                    logger.info(f"   Insight {i+1}: title={has_title}, findings={has_findings}, recs={has_recommendations}")
            
            return {
                'status': 'success',
                'insights_count': len(individual_insights),
                'valid_insights': valid_insights,
                'confidence_score': confidence_score,
                'insights_data': insights_data
            }
            
        except Exception as e:
            logger.error(f"❌ Insights verification failed: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'insights_count': 0
            }
    
    def verify_file_data_handling(self, file_id: str) -> Dict[str, Any]:
        """Verify that file data was handled correctly."""
        logger.info("📂 Verifying file data handling...")
        
        try:
            file_objects = self.db.get_file_data([file_id])
            
            if not file_objects:
                return {
                    'status': 'failed',
                    'error': 'File data not found'
                }
            
            file_obj = file_objects[0]
            
            # Test loading data from bytea
            from app.utils import load_dataframe_from_file_object
            df = load_dataframe_from_file_object(file_obj)
            
            verification_results = {
                'status': 'success',
                'file_id': file_id,
                'has_bytea_data': bool(file_obj.get('files_data')),
                'has_file_path': bool(file_obj.get('file_path')),
                'file_size': file_obj.get('file_size', 0),
                'dataframe_shape': df.shape,
                'dataframe_columns': list(df.columns),
                'sample_data': df.head(2).to_dict('records')
            }
            
            logger.info(f"✅ File data verification:")
            logger.info(f"   Bytea data: {verification_results['has_bytea_data']}")
            logger.info(f"   File path: {verification_results['has_file_path']}")
            logger.info(f"   DataFrame shape: {verification_results['dataframe_shape']}")
            logger.info(f"   Columns: {len(verification_results['dataframe_columns'])}")
            
            return verification_results
            
        except Exception as e:
            logger.error(f"❌ File data verification failed: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def cleanup_test_data(self):
        """Clean up test data from database."""
        logger.info("🧹 Cleaning up test data...")
        
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Clean up in reverse order
                    for item_type, item_id in reversed(self.cleanup_items):
                        try:
                            if item_type == 'job':
                                # Delete insights first, then job
                                cursor.execute("DELETE FROM insights WHERE job_id = %s", (item_id,))
                                cursor.execute("DELETE FROM processing_jobs WHERE id = %s", (item_id,))
                                logger.info(f"   ✅ Cleaned up job: {item_id}")
                            elif item_type == 'file':
                                cursor.execute("DELETE FROM files WHERE id = %s", (item_id,))
                                logger.info(f"   ✅ Cleaned up file: {item_id}")
                        except Exception as e:
                            logger.warning(f"   ⚠️ Failed to cleanup {item_type} {item_id}: {e}")
            
            logger.info("✅ Test data cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")
    
    def run_complete_test(self) -> bool:
        """Run the complete end-to-end test."""
        logger.info("🚀 Starting End-to-End Bytea Workflow Test")
        logger.info("=" * 70)
        
        test_results = {}
        overall_success = True
        
        try:
            # Test 1: Create test file with bytea data
            logger.info("📁 STEP 1: Creating test file with bytea data")
            file_id = self.create_test_file_in_db()
            test_results['file_creation'] = True
            print()
            
            # Test 2: Verify file data handling
            logger.info("📂 STEP 2: Verifying file data handling")
            file_verification = self.verify_file_data_handling(file_id)
            test_results['file_verification'] = file_verification['status'] == 'success'
            if not test_results['file_verification']:
                logger.error(f"File verification failed: {file_verification.get('error')}")
                overall_success = False
            print()
            
            # Test 3: Create processing job
            logger.info("📋 STEP 3: Creating processing job")
            job_id = self.create_test_job(file_id)
            test_results['job_creation'] = True
            print()
            
            # Test 4: Simulate job processing
            logger.info("⚡ STEP 4: Simulating job processing")
            processing_result = self.simulate_job_processing(job_id)
            test_results['job_processing'] = processing_result['status'] == 'success'
            if not test_results['job_processing']:
                logger.error(f"Job processing failed: {processing_result.get('error')}")
                overall_success = False
            print()
            
            # Test 5: Verify insights storage
            logger.info("🔍 STEP 5: Verifying insights storage")
            insights_verification = self.verify_insights_storage(job_id)
            test_results['insights_verification'] = insights_verification['status'] == 'success'
            if not test_results['insights_verification']:
                logger.error(f"Insights verification failed: {insights_verification.get('error')}")
                overall_success = False
            else:
                logger.info(f"✅ Found {insights_verification['insights_count']} insights with confidence {insights_verification['confidence_score']:.2f}")
            print()
            
        except Exception as e:
            logger.error(f"❌ Test execution failed: {e}")
            overall_success = False
        
        finally:
            # Always cleanup
            self.cleanup_test_data()
        
        # Results summary
        logger.info("=" * 70)
        logger.info("🎯 End-to-End Test Results:")
        
        passed_tests = sum(1 for result in test_results.values() if result)
        total_tests = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"   {test_name.replace('_', ' ').title()}: {status}")
        
        logger.info("=" * 70)
        logger.info(f"🏆 Overall Result: {passed_tests}/{total_tests} tests passed")
        
        if overall_success and passed_tests == total_tests:
            logger.info("🎉 SUCCESS: End-to-end bytea workflow is working perfectly!")
            logger.info("")
            logger.info("✅ Your system can now:")
            logger.info("   - Store files as bytea data in PostgreSQL")
            logger.info("   - Process jobs using bytea file data")
            logger.info("   - Generate insights from bytea files")
            logger.info("   - Store insights correctly in the database")
            logger.info("")
            logger.info("🚀 Ready for production use with bytea file storage!")
        else:
            logger.error("❌ FAILURE: Some tests failed. Check the logs above.")
            logger.info("")
            logger.info("💡 Common issues:")
            logger.info("   - Missing environment variables (Azure OpenAI)")
            logger.info("   - Database connection problems")
            logger.info("   - Missing database tables")
        
        return overall_success and passed_tests == total_tests

def check_prerequisites() -> bool:
    """Check if prerequisites are met for testing."""
    logger.info("🔧 Checking prerequisites...")
    
    # Check database connection
    try:
        database_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
        if not database_url:
            logger.error("❌ DATABASE_URL or POSTGRES_URL environment variable required")
            return False
        
        conn = psycopg.connect(database_url, row_factory=dict_row)
        conn.close()
        logger.info("✅ Database connection: OK")
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False
    
    # Check required tables
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                for table in ['files', 'processing_jobs', 'insights']:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_name = %s
                        );
                    """, (table,))
                    
                    if not cursor.fetchone()['exists']:
                        logger.error(f"❌ Required table '{table}' not found")
                        return False
        
        logger.info("✅ Database tables: OK")
        
    except Exception as e:
        logger.error(f"❌ Database table check failed: {e}")
        return False
    
    return True

def main():
    """Main entry point."""
    logger.info("🧪 Business Insights AI - End-to-End Bytea Workflow Test")
    logger.info("")
    
    # Check prerequisites
    if not check_prerequisites():
        logger.error("❌ Prerequisites not met. Please fix the issues above.")
        sys.exit(1)
    
    # Run the test
    test_runner = E2ETestRunner()
    success = test_runner.run_complete_test()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
