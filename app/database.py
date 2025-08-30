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
    
    def get_file_data(self, file_ids: List[str]) -> List[Dict[str, Any]]:
        """Get file data and metadata from file IDs."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, filename, original_name, file_path, files_data, mime_type, file_size
                        FROM files 
                        WHERE id = ANY(%s) AND status = 'uploaded'
                    """, (file_ids,))
                    
                    results = cursor.fetchall()
                    file_objects = []
                    
                    for row in results:
                        file_obj = {
                            'id': str(row['id']),
                            'filename': row['filename'],
                            'original_name': row['original_name'],
                            'file_path': row['file_path'],  # Keep for backward compatibility
                            'files_data': row['files_data'],  # New bytea data
                            'mime_type': row['mime_type'],
                            'file_size': row['file_size']
                        }
                        file_objects.append(file_obj)
                    
                    logger.info(f"📁 Found {len(file_objects)} files for IDs: {file_ids}")
                    return file_objects
                    
        except Exception as e:
            logger.error(f"❌ Error getting file data: {e}")
            return []

    def get_file_paths(self, file_ids: List[str]) -> List[str]:
        """Get file paths from file IDs (legacy method for backward compatibility)."""
        try:
            file_objects = self.get_file_data(file_ids)
            file_paths = []
            
            for file_obj in file_objects:
                # If files_data exists, we'll need to create temporary files
                if file_obj['files_data']:
                    # For now, return the original file path if it exists
                    if file_obj['file_path']:
                        file_paths.append(file_obj['file_path'])
                else:
                    # Fallback to file_path if files_data is not available
                    if file_obj['file_path']:
                        file_paths.append(file_obj['file_path'])
                    
            logger.info(f"📁 Found {len(file_paths)} file paths for IDs: {file_ids}")
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
        """Save analysis results to database as a single row per job."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Get file_id for this job
                    cursor.execute("""
                        SELECT file_id FROM processing_jobs WHERE id = %s
                    """, (job_id,))
                    job_result = cursor.fetchone()
                    file_id = job_result['file_id'] if job_result else None
                    
                    # Get all insights for this job
                    insights = results.get('final_insights', [])
                    
                    if not insights:
                        logger.warning(f"⚠️ No insights to save for job {job_id}")
                        return
                    
                    # Calculate overall confidence score (average of all insights)
                    total_confidence = 0
                    confidence_count = 0
                    
                    for insight in insights:
                        confidence = self._extract_confidence_score(insight)
                        total_confidence += confidence
                        confidence_count += 1
                    
                    overall_confidence = total_confidence / confidence_count if confidence_count > 0 else 0.7
                    
                    # Prepare comprehensive metadata
                    metadata = {
                        'total_insights': len(insights),
                        'insight_types': [insight.get('title', 'General Analysis') for insight in insights],
                        'analysis_summary': {
                            'total_metrics': sum(len(insight.get('metrics', {})) for insight in insights),
                            'total_findings': sum(len(insight.get('key_findings', [])) for insight in insights),
                            'total_recommendations': sum(len(insight.get('recommendations', [])) for insight in insights),
                            'total_visualizations': sum(len(insight.get('visualizations', [])) for insight in insights)
                        },
                        'execution_info': {
                            'generated_at': insights[0].get('generated_at') if insights else None,
                            'status': 'success' if all(insight.get('status') != 'error' for insight in insights) else 'partial_success'
                        }
                    }
                    
                    # Create insight type summary (comma-separated list of main insights)
                    insight_type_summary = ', '.join([insight.get('title', 'General Analysis') for insight in insights[:3]])
                    if len(insights) > 3:
                        insight_type_summary += f' (+{len(insights) - 3} more)'
                    
                    # Save all insights as single row
                    cursor.execute("""
                        INSERT INTO insights (
                            job_id, 
                            file_id, 
                            insight_type, 
                            content, 
                            confidence_score, 
                            metadata, 
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                    """, (
                        job_id,
                        file_id,
                        insight_type_summary,
                        json.dumps({
                            'final_insights': insights,
                            'summary': {
                                'total_insights': len(insights),
                                'overall_confidence': overall_confidence,
                                'analysis_complete': True
                            }
                        }),
                        overall_confidence,
                        json.dumps(metadata)
                    ))
                    
                    logger.info(f"💾 Saved complete analysis with {len(insights)} insights for job {job_id} (confidence: {overall_confidence:.2f})")
                    
        except Exception as e:
            logger.error(f"❌ Error saving results: {e}")
    
    def _extract_confidence_score(self, insight: Dict[str, Any]) -> float:
        """Extract confidence score from insight data."""
        # Try various possible keys for confidence score
        confidence_keys = ['confidence', 'confidence_score', 'score', 'certainty']
        
        for key in confidence_keys:
            if key in insight and isinstance(insight[key], (int, float)):
                score = float(insight[key])
                # Ensure score is between 0 and 1
                if 0 <= score <= 1:
                    return score
                elif 0 <= score <= 100:  # Convert percentage to decimal
                    return score / 100
        
        # Default confidence based on insight quality
        if insight.get('key_findings') and insight.get('recommendations'):
            return 0.85  # High confidence for complete insights
        elif insight.get('error'):
            return 0.3   # Low confidence for error cases
        else:
            return 0.7   # Medium confidence as default
    
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
    
    def get_insights_by_job_id(self, job_id: str) -> Dict[str, Any]:
        """Retrieve insights for a specific job (single row with all insights)."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            id,
                            job_id,
                            file_id,
                            insight_type,
                            content,
                            confidence_score,
                            metadata,
                            created_at
                        FROM insights 
                        WHERE job_id = %s 
                        ORDER BY created_at DESC
                        LIMIT 1
                    """, (job_id,))
                    
                    result = cursor.fetchone()
                    
                    if result:
                        insight_record = {
                            'id': str(result['id']),
                            'job_id': str(result['job_id']),
                            'file_id': str(result['file_id']) if result['file_id'] else None,
                            'insight_type': result['insight_type'],
                            'content': result['content'],  # Contains all insights in final_insights array
                            'confidence_score': float(result['confidence_score']) if result['confidence_score'] else 0.0,
                            'metadata': result['metadata'] if result['metadata'] else {},
                            'created_at': result['created_at'].isoformat() if result['created_at'] else None,
                            'individual_insights': result['content'].get('final_insights', []) if result['content'] else [],
                            'summary': result['content'].get('summary', {}) if result['content'] else {}
                        }
                        
                        logger.info(f"📊 Retrieved insights for job {job_id} with {len(insight_record['individual_insights'])} individual insights")
                        return insight_record
                    else:
                        logger.info(f"📊 No insights found for job {job_id}")
                        return {}
                    
        except Exception as e:
            logger.error(f"❌ Error retrieving insights: {e}")
            return {}
    
    def get_insights_by_file_id(self, file_id: str) -> List[Dict[str, Any]]:
        """Retrieve all insights for a specific file."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            i.id,
                            i.job_id,
                            i.file_id,
                            i.insight_type,
                            i.content,
                            i.confidence_score,
                            i.metadata,
                            i.created_at,
                            pj.job_type
                        FROM insights i
                        JOIN processing_jobs pj ON i.job_id = pj.id
                        WHERE i.file_id = %s 
                        ORDER BY i.created_at DESC
                    """, (file_id,))
                    
                    results = cursor.fetchall()
                    insights = []
                    
                    for row in results:
                        insight = {
                            'id': str(row['id']),
                            'job_id': str(row['job_id']),
                            'file_id': str(row['file_id']) if row['file_id'] else None,
                            'insight_type': row['insight_type'],
                            'content': row['content'],
                            'confidence_score': float(row['confidence_score']) if row['confidence_score'] else 0.0,
                            'metadata': row['metadata'] if row['metadata'] else {},
                            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                            'job_type': row['job_type']
                        }
                        insights.append(insight)
                    
                    logger.info(f"📊 Retrieved {len(insights)} insights for file {file_id}")
                    return insights
                    
        except Exception as e:
            logger.error(f"❌ Error retrieving insights by file: {e}")
            return []
    
    def get_recent_insights(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent insights across all jobs."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT 
                            i.id,
                            i.job_id,
                            i.file_id,
                            i.insight_type,
                            i.content,
                            i.confidence_score,
                            i.metadata,
                            i.created_at,
                            pj.job_type,
                            f.original_name as file_name
                        FROM insights i
                        JOIN processing_jobs pj ON i.job_id = pj.id
                        LEFT JOIN files f ON i.file_id = f.id
                        ORDER BY i.created_at DESC
                        LIMIT %s
                    """, (limit,))
                    
                    results = cursor.fetchall()
                    insights = []
                    
                    for row in results:
                        insight = {
                            'id': str(row['id']),
                            'job_id': str(row['job_id']),
                            'file_id': str(row['file_id']) if row['file_id'] else None,
                            'insight_type': row['insight_type'],
                            'content': row['content'],
                            'confidence_score': float(row['confidence_score']) if row['confidence_score'] else 0.0,
                            'metadata': row['metadata'] if row['metadata'] else {},
                            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                            'job_type': row['job_type'],
                            'file_name': row['file_name']
                        }
                        insights.append(insight)
                    
                    logger.info(f"📊 Retrieved {len(insights)} recent insights")
                    return insights
                    
        except Exception as e:
            logger.error(f"❌ Error retrieving recent insights: {e}")
            return []
    
    def update_insight_confidence(self, insight_id: str, confidence_score: float) -> bool:
        """Update confidence score for a specific insight."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE insights 
                        SET confidence_score = %s
                        WHERE id = %s
                    """, (confidence_score, insight_id))
                    
                    if cursor.rowcount > 0:
                        logger.info(f"✅ Updated confidence score for insight {insight_id}")
                        return True
                    else:
                        logger.warning(f"⚠️ No insight found with ID {insight_id}")
                        return False
                    
        except Exception as e:
            logger.error(f"❌ Error updating insight confidence: {e}")
            return False
