"""
Database connection and operations for job queue system
"""
import os
import asyncio
import psycopg
from psycopg.rows import dict_row
from typing import List, Dict, Any, Optional
import json
from datetime import datetime

from .utils import setup_logger

logger = setup_logger(__name__)

class DatabaseManager:
    """Manages PostgreSQL database connections and operations."""
    
    def __init__(self):
        self.connection_string = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
        if not self.connection_string:
            raise ValueError("DATABASE_URL or POSTGRES_URL environment variable required")
    
    def get_connection(self):
        """Get database connection."""
        try:
            conn = psycopg.connect(
                self.connection_string,
                row_factory=dict_row
            )
            return conn
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    
    def get_pending_job(self) -> Optional[Dict[str, Any]]:
        """Get the next pending job from the queue."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Get next pending job and mark as processing
                    cursor.execute("""
                        UPDATE processing_jobs 
                        SET status = 'processing', 
                            started_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = (
                            SELECT id FROM processing_jobs 
                            WHERE status = 'pending' 
                            ORDER BY created_at ASC 
                            LIMIT 1 
                            FOR UPDATE SKIP LOCKED
                        )
                        RETURNING id, file_id, job_type, metadata, business_description, created_at;
                    """)
                    
                    result = cursor.fetchone()
                    if result:
                        # Adapt to our expected format
                        adapted_job = {
                            'job_id': str(result['id']),
                            'business_description': (
                                result.get('business_description') or 
                                result.get('job_type', 'General business analysis')
                            ),
                            'file_ids': [str(result['file_id'])] if result['file_id'] else [],
                            'priority': 1,  # Default priority
                            'metadata': result.get('metadata', {}),
                            'created_at': result['created_at']
                        }
                        logger.info(f"📋 Retrieved job: {adapted_job['job_id']}")
                        return adapted_job
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error getting pending job: {e}")
            return None
    
    def get_file_paths(self, file_ids: List[str]) -> List[str]:
        """Get file paths from file IDs."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, file_path, original_name 
                        FROM files 
                        WHERE id = ANY(%s) AND status = 'uploaded'
                    """, (file_ids,))
                    
                    results = cursor.fetchall()
                    file_paths = [row['file_path'] for row in results]
                    
                    logger.info(f"📁 Found {len(file_paths)} files for IDs: {file_ids}")
                    return file_paths
                    
        except Exception as e:
            logger.error(f"❌ Error getting file paths: {e}")
            return []
    
    def update_job_status(self, job_id: str, status: str, error_message: str = None):
        """Update job status."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    if status == 'completed':
                        cursor.execute("""
                            UPDATE processing_jobs 
                            SET status = %s, 
                                completed_at = CURRENT_TIMESTAMP, 
                                updated_at = CURRENT_TIMESTAMP,
                                error_message = %s
                            WHERE id = %s
                        """, (status, error_message, job_id))
                    elif status == 'failed':
                        cursor.execute("""
                            UPDATE processing_jobs 
                            SET status = %s, 
                                error_message = %s, 
                                retry_count = retry_count + 1,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (status, error_message, job_id))
                    else:
                        cursor.execute("""
                            UPDATE processing_jobs 
                            SET status = %s, 
                                error_message = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (status, error_message, job_id))
                    
                    logger.info(f"✅ Updated job {job_id} status to: {status}")
                    
        except Exception as e:
            logger.error(f"❌ Error updating job status: {e}")
    
    def save_analysis_results(self, job_id: str, results: Dict[str, Any]):
        """Save analysis results to database."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Save each insight separately
                    insights = results.get('final_insights', [])
                    
                    for insight in insights:
                        # Save to insights table
                        cursor.execute("""
                            INSERT INTO insights (job_id, insight_type, content, confidence_score)
                            VALUES (%s, %s, %s, %s)
                        """, (
                            job_id,
                            insight.get('title', 'General Analysis'),
                            json.dumps(insight),
                            0.8  # Default confidence score
                        ))
                    
                    logger.info(f"💾 Saved {len(insights)} insights for job {job_id}")
                    
        except Exception as e:
            logger.error(f"❌ Error saving results: {e}")
    
    def should_retry_job(self, job_id: str) -> bool:
        """Check if a failed job should be retried."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT retry_count 
                        FROM processing_jobs 
                        WHERE id = %s
                    """, (job_id,))
                    
                    result = cursor.fetchone()
                    if result:
                        # Allow up to 3 retries
                        return result['retry_count'] < 3
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Error checking retry status: {e}")
            return False
    
    def reset_job_to_pending(self, job_id: str):
        """Reset a failed job back to pending for retry."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE processing_jobs 
                        SET status = 'pending', started_at = NULL, error_message = NULL
                        WHERE id = %s
                    """, (job_id,))
                    
                    logger.info(f"🔄 Reset job {job_id} to pending for retry")
                    
        except Exception as e:
            logger.error(f"❌ Error resetting job: {e}")
