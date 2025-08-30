#!/usr/bin/env python3
"""
Create a test job using existing files in the database
"""
import os

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def create_test_job():
    """Create a test job using an existing file."""
    try:
        import psycopg
        from psycopg.rows import dict_row
        
        database_url = os.getenv('DATABASE_URL')
        conn = psycopg.connect(database_url, row_factory=dict_row)
        
        with conn.cursor() as cursor:
            # Get an existing file ID
            cursor.execute("""
                SELECT id, original_name 
                FROM files 
                WHERE status = 'uploaded' 
                LIMIT 1
            """)
            
            file_result = cursor.fetchone()
            if not file_result:
                print("❌ No uploaded files found. Upload some files first.")
                return
            
            file_id = file_result['id']
            file_name = file_result['original_name']
            
            print(f"📁 Using file: {file_name} (ID: {file_id})")
            
            # Create a test job
            cursor.execute("""
                INSERT INTO processing_jobs (file_id, job_type, status)
                VALUES (%s, %s, %s)
                RETURNING id, created_at
            """, (
                file_id,
                'business_analysis',
                'pending'
            ))
            
            job_result = cursor.fetchone()
            job_id = job_result['id']
            created_at = job_result['created_at']
            
            print(f"✅ Created test job:")
            print(f"   Job ID: {job_id}")
            print(f"   File: {file_name}")
            print(f"   Status: pending")
            print(f"   Created: {created_at}")
            
        conn.close()
        
        print(f"\n🎯 Test job created successfully!")
        print(f"💡 Now run: python test_job_system.py")
        
    except Exception as e:
        print(f"❌ Error creating test job: {e}")

if __name__ == "__main__":
    print("🧪 Creating Test Job for Business Insights AI")
    print("=" * 50)
    create_test_job()
