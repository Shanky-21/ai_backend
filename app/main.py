from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import tempfile
import os

from .ai_workflow import run_complete_workflow
from .config import validate_environment
from .utils import setup_logger

# Setup
logger = setup_logger(__name__)
app = FastAPI(title="Business Insights AI", version="1.0.0")

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