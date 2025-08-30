from langgraph.graph import StateGraph, END
from typing import List, Dict, Union, Any

from .workflow_types import InsightState
from .workflow_nodes import (
    analyze_data_node,
    understand_business_node,
    map_files_to_insights_node,
    generate_insights_node
)
from .utils import setup_logger, file_objects_to_temp_paths, cleanup_temp_files

# Setup logger
logger = setup_logger(__name__)

def create_ai_workflow():
    """Build and compile the LangGraph workflow."""
    logger.info("🔧 Creating AI workflow...")
    
    workflow = StateGraph(InsightState)
    
    # Add nodes
    workflow.add_node("analyze_data", analyze_data_node)
    workflow.add_node("understand_business", understand_business_node)
    workflow.add_node("map_files", map_files_to_insights_node)
    workflow.add_node("generate_insights", generate_insights_node)
    
    # Define flow
    workflow.set_entry_point("analyze_data")
    workflow.add_edge("analyze_data", "understand_business")
    workflow.add_edge("understand_business", "map_files")
    workflow.add_edge("map_files", "generate_insights")
    workflow.add_edge("generate_insights", END)
    
    logger.info("✅ Workflow created successfully")
    return workflow.compile()

# Create workflow instance
ai_workflow_app = create_ai_workflow()

def run_complete_workflow(files: Union[List[str], List[Dict[str, Any]]], business_description: str) -> Dict:
    """Run complete workflow with error handling.
    
    Args:
        files: List of file paths (strings) or file data objects (dicts)
        business_description: Business description string
        
    Returns:
        Dictionary with status and data/error
    """
    logger.info("🚀 Starting complete workflow...")
    
    # Convert file objects to paths if needed
    temp_files_created = False
    if files and isinstance(files[0], dict):
        logger.info("📁 Converting file objects to temporary paths...")
        file_paths = file_objects_to_temp_paths(files)
        temp_files_created = True
        logger.info(f"📁 Created {len(file_paths)} temporary files")
    else:
        file_paths = files
    
    # Create initial state
    initial_state: InsightState = {
        "files": file_paths,
        "business_description": business_description,
        "file_metadata": {},
        "business_understanding": "",
        "help_suggestions": [],
        "file_mappings": {},
        "final_insights": [],
        "current_step": "initialized"
    }
    
    try:
        logger.info(f"Processing {len(file_paths)} files...")
        result = ai_workflow_app.invoke(initial_state)
        
        logger.info(f"✅ Workflow completed successfully")
        logger.info(f"Generated {len(result.get('final_insights', []))} insights")
        
        return {
            "status": "success",
            "data": result
        }
        
    except Exception as e:
        logger.error(f"❌ Workflow failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "data": initial_state
        }
    finally:
        # Clean up temporary files if we created them
        if temp_files_created:
            logger.info("🧹 Cleaning up temporary files...")
            cleanup_temp_files(file_paths)

def run_complete_workflow_with_file_objects(file_objects: List[Dict[str, Any]], business_description: str) -> Dict:
    """Run complete workflow with file objects (supports bytea data).
    
    Args:
        file_objects: List of file data objects from database
        business_description: Business description string
        
    Returns:
        Dictionary with status and data/error
    """
    logger.info("🚀 Starting workflow with file objects...")
    logger.info(f"📁 Processing {len(file_objects)} file objects")
    
    return run_complete_workflow(file_objects, business_description)
