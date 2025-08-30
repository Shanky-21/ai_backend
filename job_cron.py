#!/usr/bin/env python3
"""
Cron job script for automatically processing jobs from the database queue.

This script continuously monitors the processing_jobs table for new jobs 
with status 'pending' and processes them one at a time using the existing 
AI workflow system.

Usage:
    python job_cron.py [--interval SECONDS] [--max-jobs NUMBER] [--daemon]
    
Examples:
    python job_cron.py                    # Run with default 30s interval
    python job_cron.py --interval 10      # Check every 10 seconds
    python job_cron.py --max-jobs 100     # Stop after 100 jobs
    python job_cron.py --daemon           # Run as background daemon
"""

import os
import sys
import time
import signal
import argparse
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import traceback

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("📄 Loaded environment from .env file")
except ImportError:
    print("💡 python-dotenv not installed, using system environment variables")

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database import DatabaseManager
from app.ai_workflow import run_complete_workflow
from app.utils import setup_logger

# Setup logging
logger = setup_logger(__name__)

class JobCronProcessor:
    """
    Cron job processor that monitors and processes jobs from the database queue.
    
    Features:
    - Continuous monitoring of processing_jobs table
    - Automatic job status updates (pending -> processing -> completed/failed)
    - Retry logic for failed jobs
    - Graceful shutdown handling
    - Configurable polling interval
    - Job processing limits
    - Comprehensive logging
    """
    
    def __init__(
        self, 
        poll_interval: int = 30,
        max_jobs: Optional[int] = None,
        daemon_mode: bool = False
    ):
        """
        Initialize the cron job processor.
        
        Args:
            poll_interval: Seconds between job queue checks (default: 30)
            max_jobs: Maximum number of jobs to process before stopping (default: unlimited)
            daemon_mode: Whether to run as a background daemon
        """
        self.db = DatabaseManager()
        self.poll_interval = poll_interval
        self.max_jobs = max_jobs
        self.daemon_mode = daemon_mode
        
        # Runtime state
        self.running = False
        self.jobs_processed = 0
        self.start_time = None
        self.shutdown_requested = False
        
        logger.info("🔧 Job cron processor initialized")
        logger.info(f"   Poll interval: {poll_interval} seconds")
        logger.info(f"   Max jobs: {max_jobs or 'unlimited'}")
        logger.info(f"   Daemon mode: {daemon_mode}")
    
    def setup_signal_handlers(self) -> None:
        logger.info("setting up signal handlers")

        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum: int, frame) -> None:
            signal_name = signal.Signals(signum).name
            logger.info(f"🛑 Received {signal_name} signal - initiating graceful shutdown...")
            self.shutdown_requested = True
        
        signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Termination request
        
        if hasattr(signal, 'SIGHUP'):  # Unix systems only
            signal.signal(signal.SIGHUP, signal_handler)  # Hangup
    
    def get_pending_job(self) -> Optional[Dict[str, Any]]:
        """
        Get the next pending job and mark it as processing.
        
        Returns:
            Job dictionary if found, None otherwise
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Get next pending job and mark as processing atomically
                    cursor.execute("""
                        UPDATE processing_jobs 
                        SET status = 'in-progress', 
                            started_at = CURRENT_TIMESTAMP
                        WHERE id = (
                            SELECT id FROM processing_jobs 
                            WHERE status = 'not-started' 
                            ORDER BY created_at ASC 
                            LIMIT 1 
                            FOR UPDATE SKIP LOCKED
                        )
                        RETURNING 
                            id, file_id, job_type, metadata, 
                            created_at;
                    """)
                    
                    result = cursor.fetchone()
                    if result:
                        # Convert to expected format
                        job = {
                            'job_id': str(result['id']),
                            'file_id': result['file_id'],
                            'business_description': result.get('job_type', 'General business analysis'),
                            'file_ids': [str(result['file_id'])] if result['file_id'] else [],
                            'metadata': result.get('metadata', {}),
                            'created_at': result['created_at']
                        }
                        
                        logger.info(f"📋 Retrieved job {job['job_id']} (created: {job['created_at']})")
                        return job
                    
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error getting pending job: {e}")
            return None
    
    def get_file_paths(self, file_ids: list[str]) -> list[str]:
        """
        Get file paths from file IDs.
        
        Args:
            file_ids: List of file ID strings
            
        Returns:
            List of file paths
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, file_path, original_name 
                        FROM files 
                        WHERE id = ANY(%s) AND status = 'uploaded'
                    """, (file_ids,))
                    
                    results = cursor.fetchall()
                    file_paths = [row['file_path'] for row in results if row['file_path']]
                    
                    logger.info(f"📁 Found {len(file_paths)} files for IDs: {file_ids}")
                    return file_paths
                    
        except Exception as e:
            logger.error(f"❌ Error getting file paths: {e}")
            return []
    
    def update_job_status(
        self, 
        job_id: str, 
        status: str, 
        error_message: Optional[str] = None
    ) -> None:
        """
        Update job status in database.
        
        Args:
            job_id: Job ID to update
            status: New status (in-progress, completed, failed)
            error_message: Error message if status is failed
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    if status == 'completed':
                        cursor.execute("""
                            UPDATE processing_jobs 
                            SET status = %s, 
                                completed_at = CURRENT_TIMESTAMP,
                                error_message = %s
                            WHERE id = %s
                        """, (status, error_message, job_id))
                    elif status == 'failed':
                        cursor.execute("""
                            UPDATE processing_jobs 
                            SET status = %s, 
                                error_message = %s, 
                                retry_count = retry_count + 1
                            WHERE id = %s
                        """, (status, error_message, job_id))
                    else:
                        cursor.execute("""
                            UPDATE processing_jobs 
                            SET status = %s, 
                                error_message = %s
                            WHERE id = %s
                        """, (status, error_message, job_id))
                    
                    logger.info(f"✅ Updated job {job_id} status to: {status}")
                    
        except Exception as e:
            logger.error(f"❌ Error updating job status: {e}")
    
    def save_analysis_results(self, job_id: str, results: Dict[str, Any]) -> None:
        """
        Save analysis results to database.
        
        Args:
            job_id: Job ID
            results: Analysis results dictionary
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Save each insight separately
                    insights = results.get('final_insights', [])
                    
                    for insight in insights:
                        cursor.execute("""
                            INSERT INTO insights (job_id, insight_type, content, confidence_score, created_at)
                            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        """, (
                            job_id,
                            insight.get('title', 'General Analysis'),
                            insight,  # Store full insight object as JSON
                            insight.get('confidence', 0.8)  # Default confidence
                        ))
                    
                    logger.info(f"💾 Saved {len(insights)} insights for job {job_id}")
                    
        except Exception as e:
            logger.error(f"❌ Error saving results: {e}")
    
    def should_retry_job(self, job_id: str) -> bool:
        """
        Check if a failed job should be retried.
        
        Args:
            job_id: Job ID to check
            
        Returns:
            True if job should be retried, False otherwise
        """
        try:
            with self.db.get_connection() as conn:
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
    
    def reset_job_to_pending(self, job_id: str) -> None:
        """
        Reset a failed job back to pending for retry.
        
        Args:
            job_id: Job ID to reset
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE processing_jobs 
                        SET status = 'not-started', 
                            started_at = NULL, 
                            error_message = NULL
                        WHERE id = %s
                    """, (job_id,))
                    
                    logger.info(f"🔄 Reset job {job_id} to not-started for retry")
                    
        except Exception as e:
            logger.error(f"❌ Error resetting job: {e}")
    
    def process_single_job(self, job: Dict[str, Any]) -> bool:
        """
        Process a single analysis job.
        
        Args:
            job: Job dictionary containing job details
            
        Returns:
            True if job processed successfully, False otherwise
        """
        job_id = job['job_id']
        business_description = job['business_description']
        file_ids = job['file_ids']
        
        logger.info(f"⚡ Processing job {job_id}")
        logger.info(f"   Business: {business_description[:100]}...")
        logger.info(f"   Files: {len(file_ids)} file(s)")
        
        try:
            # Get file paths from file IDs
            file_paths = self.get_file_paths(file_ids)
            
            if not file_paths:
                error_msg = f"No valid files found for IDs: {file_ids}"
                logger.error(f"❌ {error_msg}")
                self.update_job_status(job_id, 'failed', error_msg)
                return False
            
            logger.info(f"📁 Processing {len(file_paths)} files")
            
            # Run the AI workflow
            result = run_complete_workflow(file_paths, business_description)
            
            if result['status'] == 'success':
                # Save results to database
                self.save_analysis_results(job_id, result['data'])
                self.update_job_status(job_id, 'completed')
                
                insights_count = len(result['data'].get('final_insights', []))
                logger.info(f"✅ Job {job_id} completed successfully - {insights_count} insights generated")
                return True
            else:
                error_msg = result.get('error', 'Unknown workflow error')
                logger.error(f"❌ Workflow failed for job {job_id}: {error_msg}")
                self.update_job_status(job_id, 'failed', error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Job processing error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            
            # Check if we should retry
            if self.should_retry_job(job_id):
                logger.info(f"🔄 Job {job_id} will be retried")
                self.reset_job_to_pending(job_id)
            else:
                logger.info(f"❌ Job {job_id} failed permanently (max retries reached)")
                self.update_job_status(job_id, 'failed', error_msg)
            
            return False
    
    def run_once(self) -> bool:
        """
        Run one iteration of job processing.
        
        Returns:
            True if a job was processed, False otherwise
        """
        try:
            # Check if we should stop
            if self.shutdown_requested:
                logger.info("🛑 Shutdown requested, stopping job processing")
                return False
            
            if self.max_jobs and self.jobs_processed >= self.max_jobs:
                logger.info(f"🏁 Reached maximum job limit ({self.max_jobs}), stopping")
                return False
            
            logger.debug("going to find pending jobs")
            
            # Get next pending job
            job = self.get_pending_job()

            logger.debug("after finding pending jobs")
            
            if job:
                success = self.process_single_job(job)
                if success:
                    self.jobs_processed += 1
                return True
            else:
                logger.info("📭 No pending jobs found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in job processing iteration: {e}")
            return False
    
    def print_status(self) -> None:
        """Print current processing status."""
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            rate = self.jobs_processed / elapsed.total_seconds() if elapsed.total_seconds() > 0 else 0
            
            logger.info(f"📊 Status - Processed: {self.jobs_processed} jobs, "
                       f"Elapsed: {elapsed}, Rate: {rate:.2f} jobs/sec")
    
    def start_processing(self) -> None:
        """
        Start continuous job processing.
        
        This is the main processing loop that:
        1. Checks for pending jobs
        2. Processes them one at a time
        3. Handles errors and retries
        4. Provides status updates
        5. Handles graceful shutdown
        """
        logger.info("🚀 Starting job cron processor...")
        
        # Setup signal handlers for graceful shutdown
        self.setup_signal_handlers()
        
        # logger.info("after setting up signal handlers")
        
        self.running = True
        self.start_time = datetime.now()
        last_status_time = self.start_time

        logger.info("after setting up signal handlers")
        
        try:
            while self.running and not self.shutdown_requested:
                try:
                    # Process one job
                    logger.info("going to run once")
                    job_processed = self.run_once()
                    
                    logger.info("after running once")
                    
                    # Print status every 5 minutes or after processing jobs
                    now = datetime.now()
                    if (job_processed or 
                        (now - last_status_time) > timedelta(minutes=5)):
                        self.print_status()
                        last_status_time = now
                    
                    # Check if we should stop
                    if self.max_jobs and self.jobs_processed >= self.max_jobs:
                        break
                    
                    # Sleep between iterations (only if no job was processed)
                    if not job_processed:
                        time.sleep(self.poll_interval)
                    else:
                        # Small delay between jobs to prevent overwhelming the system
                        time.sleep(1)
                    
                except KeyboardInterrupt:
                    logger.info("⏹️  Received keyboard interrupt")
                    break
                except Exception as e:
                    logger.error(f"❌ Unexpected error in processing loop: {e}")
                    logger.error(f"Stack trace: {traceback.format_exc()}")
                    # Wait longer after errors
                    time.sleep(self.poll_interval * 2)
                    
        except Exception as e:
            logger.error(f"❌ Fatal error in job processor: {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
        finally:
            self.running = False
            self.print_status()
            logger.info(f"🏁 Job cron processor stopped. Total processed: {self.jobs_processed} jobs")
    
    def stop_processing(self) -> None:
        """Stop job processing."""
        logger.info("⏹️  Stopping job cron processor...")
        self.running = False
        self.shutdown_requested = True


def main():
    """Main entry point for the cron job script."""
    parser = argparse.ArgumentParser(
        description="Automated job processor for Business Insights AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     # Run with default settings (30s interval)
  %(prog)s --interval 10       # Check every 10 seconds
  %(prog)s --max-jobs 100      # Stop after processing 100 jobs
  %(prog)s --daemon            # Run as background daemon
  %(prog)s --interval 5 --max-jobs 50  # Custom interval and limit
        """
    )
    
    parser.add_argument(
        '--interval', 
        type=int, 
        default=30,
        help='Polling interval in seconds (default: 30)'
    )
    
    parser.add_argument(
        '--max-jobs', 
        type=int, 
        default=None,
        help='Maximum number of jobs to process before stopping (default: unlimited)'
    )
    
    parser.add_argument(
        '--daemon', 
        action='store_true',
        help='Run as background daemon'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Validate environment
    database_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
    if not database_url:
        logger.error("❌ DATABASE_URL or POSTGRES_URL environment variable required")
        sys.exit(1)
    
    # Create and start processor
    try:
        processor = JobCronProcessor(
            poll_interval=args.interval,
            max_jobs=args.max_jobs,
            daemon_mode=args.daemon
        )
        
        processor.start_processing()
        
    except KeyboardInterrupt:
        logger.info("👋 Shutting down job processor...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
