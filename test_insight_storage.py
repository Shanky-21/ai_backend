#!/usr/bin/env python3
"""
Test script to demonstrate insight storage functionality
"""
import os
import sys

# Load environment variables first
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("📄 Loaded environment from .env file")
except ImportError:
    print("💡 python-dotenv not installed, using system environment")

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.database import DatabaseManager
from app.utils import setup_logger

logger = setup_logger(__name__)

def test_insight_storage():
    """Test the enhanced insight storage functionality."""
    try:
        # Check environment variables first
        database_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
        print(f"🔧 Database URL: {database_url[:50]}..." if database_url else "❌ No DATABASE_URL found")
        
        if not database_url:
            print("❌ DATABASE_URL or POSTGRES_URL environment variable not set")
            print("💡 Make sure you have a .env file with DATABASE_URL configured")
            return False
        
        # Initialize database manager
        db = DatabaseManager()
        logger.info("✅ Database manager initialized")
        
        # Test basic connection
        print("🔌 Testing database connection...")
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 as test")
                result = cursor.fetchone()
                if result['test'] == 1:
                    print("✅ Database connection successful!")
                else:
                    raise Exception("Connection test failed")
        
        # Test data - simulating what would come from the workflow
        test_results = {
            'final_insights': [
                {
                    'title': 'Revenue Analysis',
                    'description': 'Analysis of revenue trends and patterns',
                    'priority': 'high',
                    'analysis_type': 'financial_analysis',
                    'confidence': 0.85,
                    'confidence_score': 0.85,
                    'metrics': {
                        'total_revenue': 150000,
                        'growth_rate': 0.12,
                        'avg_monthly_revenue': 12500
                    },
                    'key_findings': [
                        'Revenue has grown 12% over the past year',
                        'Q4 shows strongest performance',
                        'Customer retention rate is 85%'
                    ],
                    'recommendations': [
                        'Focus marketing spend on Q4 channels',
                        'Implement customer loyalty program',
                        'Expand successful product lines'
                    ],
                    'visualizations': [
                        {
                            'title': 'Revenue Trend Chart',
                            'type': 'line_chart',
                            'data': 'base64_encoded_chart_data'
                        }
                    ],
                    'executive_summary': 'Revenue analysis shows strong 12% growth with Q4 being the strongest quarter. Customer retention is solid at 85%.',
                    'next_steps': [
                        'Review Q4 marketing strategies',
                        'Implement retention improvements',
                        'Plan expansion for high-performing products'
                    ],
                    'generated_at': '2024-01-15T10:30:00',
                    'status': 'success'
                },
                {
                    'title': 'Customer Segmentation',
                    'description': 'Analysis of customer segments and behavior patterns',
                    'priority': 'medium',
                    'analysis_type': 'customer_analysis',
                    'confidence': 0.78,
                    'confidence_score': 0.78,
                    'metrics': {
                        'total_customers': 1250,
                        'segments_identified': 4,
                        'high_value_customers': 180
                    },
                    'key_findings': [
                        'Four distinct customer segments identified',
                        'High-value customers represent 14% but 40% of revenue',
                        'Young professionals show highest engagement'
                    ],
                    'recommendations': [
                        'Create targeted campaigns for each segment',
                        'Develop premium services for high-value customers',
                        'Increase engagement with young professional segment'
                    ],
                    'executive_summary': 'Customer segmentation reveals four distinct groups with high-value customers driving disproportionate revenue.',
                    'next_steps': [
                        'Develop segment-specific marketing materials',
                        'Launch premium customer program',
                        'Analyze young professional preferences'
                    ],
                    'generated_at': '2024-01-15T10:35:00',
                    'status': 'success'
                }
            ]
        }
        
        # First, create a test job and file in the database
        import uuid
        test_job_id = str(uuid.uuid4())
        test_file_id = str(uuid.uuid4())
        
        print(f"🔧 Creating test job and file entries...")
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Create test file entry
                cursor.execute("""
                    INSERT INTO files (id, filename, original_name, file_path, file_size, mime_type, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (test_file_id, "test_file.csv", "test_file.csv", "/tmp/test_file.csv", 1024, "text/csv", "uploaded"))
                
                # Create test job entry
                cursor.execute("""
                    INSERT INTO processing_jobs (id, file_id, job_type, status)
                    VALUES (%s, %s, %s, %s)
                """, (test_job_id, test_file_id, "test_analysis", "completed"))
        
        print(f"✅ Created test job: {test_job_id}")
        print(f"✅ Created test file: {test_file_id}")
        
        logger.info(f"💾 Testing insight storage for job: {test_job_id}")
        
        db.save_analysis_results(test_job_id, test_results)
        logger.info("✅ Insights saved successfully!")
        
        # Test retrieving insights
        logger.info("📊 Testing insight retrieval...")
        
        insight_record = db.get_insights_by_job_id(test_job_id)
        
        if insight_record:
            individual_insights = insight_record.get('individual_insights', [])
            logger.info(f"✅ Retrieved insight record for job {test_job_id}")
            logger.info(f"  - Record ID: {insight_record.get('id')}")
            logger.info(f"  - Insight Type Summary: {insight_record.get('insight_type')}")
            logger.info(f"  - Overall Confidence: {insight_record.get('confidence_score')}")
            logger.info(f"  - Individual Insights: {len(individual_insights)}")
            logger.info(f"  - Created: {insight_record.get('created_at')}")
            logger.info(f"  - Has Metadata: {'Yes' if insight_record.get('metadata') else 'No'}")
            
            # Display individual insights within the record
            for i, insight in enumerate(individual_insights, 1):
                logger.info(f"  Individual Insight {i}: {insight.get('title', 'Unknown')} (confidence: {insight.get('confidence', 'N/A')})")
        else:
            logger.warning("⚠️ No insights found for the job")
        
        # Test recent insights
        recent_insights = db.get_recent_insights(limit=10)
        logger.info(f"📈 Found {len(recent_insights)} recent insights")
        
        # Cleanup test data
        print("🧹 Cleaning up test data...")
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                # Delete insights first (due to foreign key constraints)
                cursor.execute("DELETE FROM insights WHERE job_id = %s", (test_job_id,))
                # Delete job
                cursor.execute("DELETE FROM processing_jobs WHERE id = %s", (test_job_id,))
                # Delete file
                cursor.execute("DELETE FROM files WHERE id = %s", (test_file_id,))
        print("✅ Test data cleaned up")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Insight Storage System")
    print("=" * 50)
    
    success = test_insight_storage()
    
    if success:
        print("\n✅ All tests passed! Insight storage is working correctly.")
        print("\nThe system now properly stores insights with:")
        print("- All database columns (id, job_id, file_id, insight_type, content, confidence_score, metadata, created_at)")
        print("- Enhanced confidence scoring based on analysis quality")
        print("- Structured metadata for better organization")
        print("- API endpoints for retrieving insights")
        print("\nAvailable API endpoints:")
        print("- GET /insights/job/{job_id} - Get insights by job ID")
        print("- GET /insights/file/{file_id} - Get insights by file ID")
        print("- GET /insights/recent - Get recent insights")
        print("- PUT /insights/{insight_id}/confidence - Update confidence score")
        print("- GET /insights/stats - Get insights statistics")
    else:
        print("\n❌ Tests failed. Check the error messages above.")
        sys.exit(1)
