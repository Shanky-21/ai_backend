"""
Job processor for monitoring and processing analysis jobs
"""
import asyncio
import time
from typing import Dict, Any
import traceback

from .database import DatabaseManager
from .ai_workflow import run_complete_workflow
from .utils import setup_logger

logger = setup_logger(__name__)

class JobProcessor:
    """Processes analysis jobs from the database queue."""
    
    def __init__(self, poll_interval: int = 5):
        self.db = DatabaseManager()
        self.poll_interval = poll_interval
        self.running = False
        logger.info(f"🔧 Job processor initialized (poll interval: {poll_interval}s)")
    
    def process_single_job(self, job: Dict[str, Any]) -> bool:
        """Process a single analysis job."""
        job_id = job['job_id']
        business_description = job['business_description']
        file_ids = job['file_ids']
        
        logger.info(f"⚡ Processing job {job_id}")
        logger.info(f"   Business: {business_description[:100]}...")
        logger.info(f"   Files: {len(file_ids)} file(s)")
        
        try:
            # Get file paths from file IDs
            file_paths = self.db.get_file_paths(file_ids)
            
            if not file_paths:
                error_msg = f"No valid files found for IDs: {file_ids}"
                logger.error(f"❌ {error_msg}")
                self.db.update_job_status(job_id, 'failed', error_msg)
                return False
            
            logger.info(f"📁 Processing {len(file_paths)} files")
            
            # Run the AI workflow
            result = run_complete_workflow(file_paths, business_description)
            
            if result['status'] == 'success':
                # Save results to database
                self.db.save_analysis_results(job_id, result['data'])
                self.db.update_job_status(job_id, 'completed')
                
                insights_count = len(result['data'].get('final_insights', []))
                logger.info(f"✅ Job {job_id} completed successfully - {insights_count} insights generated")
                return True
            else:
                error_msg = result.get('error', 'Unknown workflow error')
                logger.error(f"❌ Workflow failed for job {job_id}: {error_msg}")
                self.db.update_job_status(job_id, 'failed', error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Job processing error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            
            # Check if we should retry
            if self.db.should_retry_job(job_id):
                logger.info(f"🔄 Job {job_id} will be retried")
                self.db.reset_job_to_pending(job_id)
            else:
                logger.info(f"❌ Job {job_id} failed permanently (max retries reached)")
                self.db.update_job_status(job_id, 'failed', error_msg)
            
            return False
    
    def run_once(self) -> bool:
        """Run one iteration of job processing."""
        try:
            # Get next pending job
            job = self.db.get_pending_job()
            
            if job:
                return self.process_single_job(job)
            else:
                logger.debug("📭 No pending jobs found")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error in job processing iteration: {e}")
            return False
    
    def start_monitoring(self):
        """Start continuous job monitoring."""
        logger.info("🚀 Starting job processor monitoring...")
        self.running = True
        
        processed_count = 0
        
        try:
            while self.running:
                try:
                    job_processed = self.run_once()
                    
                    if job_processed:
                        processed_count += 1
                        logger.info(f"📊 Total jobs processed: {processed_count}")
                    
                    # Sleep between iterations
                    time.sleep(self.poll_interval)
                    
                except KeyboardInterrupt:
                    logger.info("⏹️  Received interrupt signal")
                    break
                except Exception as e:
                    logger.error(f"❌ Unexpected error in monitoring loop: {e}")
                    time.sleep(self.poll_interval * 2)  # Wait longer after errors
                    
        except Exception as e:
            logger.error(f"❌ Fatal error in job processor: {e}")
        finally:
            self.running = False
            logger.info(f"🏁 Job processor stopped. Total processed: {processed_count}")
    
    def stop_monitoring(self):
        """Stop job monitoring."""
        logger.info("⏹️  Stopping job processor...")
        self.running = False

# Async version for integration with FastAPI
class AsyncJobProcessor:
    """Async version of job processor for FastAPI integration."""
    
    def __init__(self, poll_interval: int = 5):
        self.processor = JobProcessor(poll_interval)
        self.task = None
    
    async def start_background_processing(self):
        """Start background job processing."""
        if self.task is None or self.task.done():
            logger.info("🔄 Starting background job processing...")
            self.task = asyncio.create_task(self._run_background())
    
    async def _run_background(self):
        """Background processing loop."""
        while True:
            try:
                # Run job processing in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.processor.run_once)
                await asyncio.sleep(self.processor.poll_interval)
            except asyncio.CancelledError:
                logger.info("🛑 Background processing cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in background processing: {e}")
                await asyncio.sleep(self.processor.poll_interval * 2)
    
    def stop_background_processing(self):
        """Stop background processing."""
        if self.task and not self.task.done():
            logger.info("⏹️  Stopping background processing...")
            self.task.cancel()

# Global instance for FastAPI integration
background_processor = AsyncJobProcessor()

if __name__ == "__main__":
    # Run standalone job processor
    processor = JobProcessor(poll_interval=3)
    
    try:
        processor.start_monitoring()
    except KeyboardInterrupt:
        logger.info("👋 Shutting down job processor...")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        processor.stop_monitoring()
