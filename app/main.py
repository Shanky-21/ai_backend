from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import tempfile
import os

from .ai_workflow import run_complete_workflow
from .config import validate_environment
from .utils import setup_logger
from .database import DatabaseManager

# Setup
logger = setup_logger(__name__)
app = FastAPI(title="Business Insights AI", version="1.0.0")

# Initialize database manager (will be None if no database configured)
try:
    db_manager = DatabaseManager()
    logger.info("✅ Database manager initialized")
except Exception as e:
    logger.warning(f"⚠️  Database not available: {e}")
    db_manager = None

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Validate environment on startup."""
    logger.info("🚀 Starting Business Insights AI...")
    if not validate_environment():
        logger.warning("⚠️  Some environment variables missing")
    
    # Job processing is now handled by separate cron system
    database_url = os.getenv('DATABASE_URL') or os.getenv('POSTGRES_URL')
    if database_url:
        logger.info("💡 Database configured - job processing handled by separate cron system")
        logger.info("🔧 Start job processor with: ./start_job_cron.sh dev")
        logger.info("🔧 Or run directly: python job_cron.py --interval 10")
    else:
        logger.info("💡 No database configured - job processing disabled")
        logger.info("🔧 Configure DATABASE_URL to enable job processing")
    
    logger.info("✅ Server startup complete")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("⏹️  Shutting down Business Insights AI...")
    logger.info("💡 Job processing runs independently via cron system")
    logger.info("👋 Shutdown complete")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy", 
        "service": "Business Insights AI",
        "version": "1.0.0"
    }

@app.post("/analyze")
async def analyze_business_data(
    files: List[UploadFile] = File(...),
    business_description: str = Form(...)
):
    """Main endpoint for business data analysis."""
    logger.info(f"📊 New analysis request with {len(files)} files")
    
    temp_files = []
    try:
        # Validate and save uploaded files
        for file in files:
            if not file.filename.endswith(('.csv', '.xlsx', '.xls')):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported file type: {file.filename}"
                )
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
                content = await file.read()
                tmp.write(content)
                temp_files.append(tmp.name)
                logger.info(f"📁 Saved {file.filename} temporarily")
        
        # Run workflow
        result = run_complete_workflow(temp_files, business_description)
        
        if result["status"] == "success":
            data = result["data"]
            return {
                "status": "success",
                "business_understanding": data.get("business_understanding", ""),
                "insights": data.get("final_insights", []),
                "total_insights": len(data.get("final_insights", [])),
                "message": "Analysis completed successfully"
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Workflow failed: {result['error']}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    
    finally:
        # Cleanup temporary files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
                logger.info(f"🗑️  Cleaned up {temp_file}")
            except Exception as cleanup_error:
                logger.warning(f"⚠️  Cleanup failed for {temp_file}: {cleanup_error}")

@app.get("/insights/job/{job_id}")
async def get_insights_by_job(job_id: str):
    """Get all insights for a specific job."""
    if not db_manager:
        raise HTTPException(
            status_code=503, 
            detail="Database not configured - insights storage not available"
        )
    
    try:
        insight_record = db_manager.get_insights_by_job_id(job_id)
        
        if not insight_record:
            raise HTTPException(status_code=404, detail="No insights found for this job")
        
        return {
            "status": "success",
            "job_id": job_id,
            "insight_record": insight_record,
            "individual_insights": insight_record.get('individual_insights', []),
            "total_insights": len(insight_record.get('individual_insights', [])),
            "overall_confidence": insight_record.get('confidence_score', 0.0),
            "summary": insight_record.get('summary', {}),
            "created_at": insight_record.get('created_at')
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error retrieving insights for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve insights: {str(e)}")

@app.get("/insights/file/{file_id}")
async def get_insights_by_file(file_id: str):
    """Get all insights for a specific file."""
    if not db_manager:
        raise HTTPException(
            status_code=503, 
            detail="Database not configured - insights storage not available"
        )
    
    try:
        insights = db_manager.get_insights_by_file_id(file_id)
        return {
            "status": "success",
            "file_id": file_id,
            "insights": insights,
            "total": len(insights)
        }
    except Exception as e:
        logger.error(f"❌ Error retrieving insights for file {file_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve insights: {str(e)}")

@app.get("/insights/recent")
async def get_recent_insights(limit: int = Query(50, ge=1, le=500)):
    """Get recent insights across all jobs."""
    if not db_manager:
        raise HTTPException(
            status_code=503, 
            detail="Database not configured - insights storage not available"
        )
    
    try:
        insights = db_manager.get_recent_insights(limit)
        return {
            "status": "success",
            "insights": insights,
            "total": len(insights),
            "limit": limit
        }
    except Exception as e:
        logger.error(f"❌ Error retrieving recent insights: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve insights: {str(e)}")

@app.put("/insights/{insight_id}/confidence")
async def update_insight_confidence(
    insight_id: str, 
    confidence_score: float = Query(..., ge=0.0, le=1.0)
):
    """Update confidence score for a specific insight."""
    if not db_manager:
        raise HTTPException(
            status_code=503, 
            detail="Database not configured - insights storage not available"
        )
    
    try:
        success = db_manager.update_insight_confidence(insight_id, confidence_score)
        if success:
            return {
                "status": "success",
                "insight_id": insight_id,
                "new_confidence_score": confidence_score,
                "message": "Confidence score updated successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Insight not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating insight confidence: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update confidence: {str(e)}")

@app.get("/insights/stats")
async def get_insights_stats():
    """Get statistics about stored insights."""
    if not db_manager:
        raise HTTPException(
            status_code=503, 
            detail="Database not configured - insights storage not available"
        )
    
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # Get total insights count
                cursor.execute("SELECT COUNT(*) as total FROM insights")
                total_count = cursor.fetchone()['total']
                
                # Get insights by type
                cursor.execute("""
                    SELECT insight_type, COUNT(*) as count 
                    FROM insights 
                    GROUP BY insight_type 
                    ORDER BY count DESC
                """)
                by_type = cursor.fetchall()
                
                # Get average confidence score
                cursor.execute("SELECT AVG(confidence_score) as avg_confidence FROM insights")
                avg_confidence = cursor.fetchone()['avg_confidence']
                
                # Get recent activity (last 7 days)
                cursor.execute("""
                    SELECT COUNT(*) as recent_count 
                    FROM insights 
                    WHERE created_at >= NOW() - INTERVAL '7 days'
                """)
                recent_count = cursor.fetchone()['recent_count']
                
                return {
                    "status": "success",
                    "stats": {
                        "total_insights": total_count,
                        "insights_by_type": [dict(row) for row in by_type],
                        "average_confidence": float(avg_confidence) if avg_confidence else 0.0,
                        "recent_insights_7_days": recent_count
                    }
                }
                
    except Exception as e:
        logger.error(f"❌ Error retrieving insights stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve stats: {str(e)}")