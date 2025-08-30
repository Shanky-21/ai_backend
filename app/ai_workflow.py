from langgraph.graph import StateGraph, END
from typing import List, Dict

from .workflow_types import InsightState
from .workflow_nodes import (
    analyze_data_node,
    understand_business_node,
    map_files_to_insights_node,
    generate_insights_node
)
from .utils import setup_logger

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

def run_complete_workflow(files: List[str], business_description: str) -> Dict:
    """Run complete workflow with error handling."""
    logger.info("🚀 Starting complete workflow...")
    
    # Create initial state
    initial_state: InsightState = {
        "files": files,
        "business_description": business_description,
        "file_metadata": {},
        "business_understanding": "",
        "help_suggestions": [],
        "file_mappings": {},
        "final_insights": [],
        "current_step": "initialized"
    }
    
    try:
        logger.info(f"Processing {len(files)} files...")
        result = ai_workflow_app.inv
        oke(initial_state)
        
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
