import os
from typing import Dict, Any
import pandas as pd
from langchain_openai import AzureChatOpenAI
from langsmith import traceable
import json
from datetime import datetime

from .workflow_types import InsightState
from .utils import load_dataframe, format_dataframe_summary, setup_logger, safe_json_parse
from .config import (
    AZURE_OPENAI_API_KEY, 
    AZURE_OPENAI_ENDPOINT, 
    AZURE_OPENAI_API_VERSION,
    AZURE_DEPLOYMENT_NAME,
    LLM_TEMPERATURE
)

# Setup logger
logger = setup_logger(__name__)

# Initialize Azure OpenAI LLM
try:
    llm = AzureChatOpenAI(
        deployment_name=AZURE_DEPLOYMENT_NAME,
        openai_api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        openai_api_key=AZURE_OPENAI_API_KEY,
        temperature=LLM_TEMPERATURE
    )
    logger.info("✅ Azure OpenAI LLM initialized successfully")
except Exception as e:
    logger.warning(f"⚠️  Azure OpenAI initialization failed: {e}")
    # Create a placeholder that will fail gracefully if used
    llm = None

def analyze_data_node(state: InsightState) -> InsightState:
    """Extract metadata and samples from uploaded files."""
    logger.info("🔍 Analyzing uploaded files...")
    
    metadata = {}
    for file_path in state["files"]:
        try:
            # Load the dataframe
            df = load_dataframe(file_path)
            
            # Generate metadata
            file_metadata = format_dataframe_summary(df)
            file_metadata["filename"] = os.path.basename(file_path)
            
            metadata[file_path] = file_metadata
            logger.info(f"✅ Processed {file_metadata['filename']}: {df.shape}")
            
        except Exception as e:
            logger.error(f"❌ Error processing {file_path}: {e}")
            metadata[file_path] = {"error": str(e)}
    
    return {
        **state, 
        "file_metadata": metadata, 
        "current_step": "analyze_data_complete"
    }

def create_data_summary(file_metadata: Dict[str, Any]) -> str:
    """Create concise data summary for LLM."""
    summary = ""
    for file_path, metadata in file_metadata.items():
        if "error" not in metadata:
            summary += f"File: {metadata['filename']}\n"
            summary += f"- {metadata['shape'][0]} rows, {metadata['shape'][1]} columns\n"
            summary += f"- Columns: {', '.join(metadata['columns'][:5])}\n\n"
    return summary

def calculate_insight_confidence(analysis_results: Dict[str, Any], business_insights: Dict[str, Any]) -> float:
    """Calculate confidence score based on analysis and insight quality."""
    confidence = 0.5  # Base confidence
    
    # Boost confidence based on analysis quality
    if analysis_results.get("metrics") and len(analysis_results["metrics"]) > 0:
        confidence += 0.15  # Has meaningful metrics
    
    if analysis_results.get("key_findings") and len(analysis_results["key_findings"]) > 0:
        confidence += 0.1   # Has findings
    
    if analysis_results.get("visualizations") and len(analysis_results["visualizations"]) > 0:
        confidence += 0.1   # Has visualizations
    
    if analysis_results.get("recommendations") and len(analysis_results["recommendations"]) > 0:
        confidence += 0.1   # Has recommendations
    
    # Boost confidence based on business insight quality
    if business_insights.get("executive_summary") and len(business_insights["executive_summary"]) > 50:
        confidence += 0.05  # Has substantial summary
    
    if business_insights.get("next_steps") and len(business_insights["next_steps"]) > 0:
        confidence += 0.05  # Has actionable next steps
    
    # Penalize for errors
    if "error" in analysis_results:
        confidence -= 0.3   # Significant penalty for errors
    
    # Ensure confidence is between 0.1 and 0.95
    return max(0.1, min(0.95, confidence))

@traceable
def understand_business_node(state: InsightState) -> InsightState:
    """Understand business and generate help suggestions."""
    logger.info("🧠 Understanding business context...")
    
    if llm is None:
        logger.error("❌ LLM not initialized - cannot understand business context")
        return {
            **state,
            "business_understanding": "LLM not available",
            "help_suggestions": [{"title": "General Analysis", "description": "Basic data insights", "priority": "medium"}],
            "current_step": "business_understanding_error"
        }
    
    try:
        data_summary = create_data_summary(state["file_metadata"])
        
        prompt = f"""Analyze this business and data:

BUSINESS: {state['business_description']}

DATA FILES:
{data_summary}

Provide JSON response:
{{
    "business_understanding": "brief 2-3 sentence summary of what they do",
    "help_suggestions": [
        {{"title": "Revenue Analysis", "description": "detailed help description", "priority": "high"}}
    ]
}}

Generate exactly 3 help suggestions."""

        response = llm.invoke(prompt)
        result = safe_json_parse(response.content, {
            "business_understanding": "Analysis in progress...",
            "help_suggestions": [{"title": "General Analysis", "description": "Basic data insights", "priority": "medium"}]
        })
        
        logger.info(f"✅ Generated {len(result['help_suggestions'])} suggestions")
        
        return {
            **state,
            "business_understanding": result["business_understanding"],
            "help_suggestions": result["help_suggestions"],
            "current_step": "business_understanding_complete"
        }
        
    except Exception as e:
        logger.error(f"❌ Business understanding error: {e}")
        return {
            **state, 
            "current_step": "business_understanding_error"
        }

@traceable
def map_files_to_insights_node(state: InsightState) -> InsightState:
    """Map files to insights."""
    logger.info("🔗 Mapping files to insights...")
    
    mappings = {}
    
    try:
        # Create file descriptions for LLM
        file_descriptions = ""
        for file_path, metadata in state["file_metadata"].items():
            if "error" not in metadata:
                file_descriptions += f"{metadata['filename']}: {', '.join(metadata['columns'])}\n"
        
        for suggestion in state["help_suggestions"]:
            prompt = f"""Which files are most relevant for this insight?

INSIGHT: {suggestion['title']} - {suggestion['description']}

AVAILABLE FILES:
{file_descriptions}

Return JSON: {{"relevant_files": ["filename1.csv"], "confidence": "high", "reasoning": "why these files"}}"""

            try:
                response = llm.invoke(prompt)
                result = safe_json_parse(response.content, {
                    "relevant_files": [list(state["file_metadata"].keys())[0]] if state["file_metadata"] else [],
                    "confidence": "medium",
                    "reasoning": "fallback mapping"
                })
                
                # Map back to full file paths
                relevant_files = []
                for filename in result["relevant_files"]:
                    for file_path, metadata in state["file_metadata"].items():
                        if metadata.get("filename") == filename:
                            relevant_files.append(file_path)
                            break
                
                mappings[suggestion['title']] = {
                    "relevant_files": relevant_files,
                    "confidence": result.get("confidence", "medium"),
                    "reasoning": result.get("reasoning", "")
                }
                
            except Exception as e:
                logger.error(f"❌ Error mapping files for {suggestion['title']}: {e}")
                # Fallback: use first available file
                mappings[suggestion['title']] = {
                    "relevant_files": list(state["files"])[:1],
                    "confidence": "low",
                    "reasoning": "fallback due to error"
                }
        
        logger.info(f"✅ Mapped files for {len(mappings)} insights")
        return {
            **state, 
            "file_mappings": mappings, 
            "current_step": "file_mapping_complete"
        }
        
    except Exception as e:
        logger.error(f"❌ File mapping failed: {e}")
        return {**state, "current_step": "file_mapping_error"}

@traceable
def generate_insights_node(state: InsightState) -> InsightState:
    """Generate actual insights using code generation and execution."""
    logger.info("⚡ Generating insights with real analysis...")
    
    from .analysis_engine import get_data_structure_info, generate_analysis_code, execute_analysis_code, generate_insight_summary
    
    final_insights = []
    
    try:
        for suggestion in state["help_suggestions"]:
            logger.info(f"🔍 Processing: {suggestion['title']}")
            
            title = suggestion['title']
            relevant_files = state["file_mappings"].get(title, {}).get("relevant_files", [])
            
            if not relevant_files:
                logger.warning(f"⚠️  No files mapped for {title}, using all files")
                relevant_files = state["files"]
            
            # Get data structure info for LLM
            data_info = get_data_structure_info(relevant_files, state["file_metadata"])
            
            # Generate analysis code
            logger.info(f"🔧 Generating analysis code for {title}")
            analysis_code = generate_analysis_code(suggestion, data_info, llm)
            
            # Execute the generated code
            logger.info(f"⚙️  Executing analysis for {title}")
            analysis_results = execute_analysis_code(analysis_code, relevant_files)
            
            # Generate business-friendly summary
            logger.info(f"📋 Creating business summary for {title}")
            business_insights = generate_insight_summary(suggestion, analysis_results, llm)
            
            # Calculate confidence score based on analysis quality
            confidence_score = calculate_insight_confidence(analysis_results, business_insights)
            
            # Create final insight structure optimized for database storage
            insight = {
                "title": title,
                "description": suggestion.get("description", ""),
                "priority": suggestion["priority"],
                "analysis_type": suggestion.get("type", "business_analysis"),
                "files_used": [os.path.basename(f) for f in relevant_files],
                "data_sources": relevant_files,
                "confidence": confidence_score,
                "confidence_score": confidence_score,  # Alias for database compatibility
                
                # Core analysis results
                "metrics": analysis_results.get("metrics", {}),
                "key_findings": analysis_results.get("key_findings", []),
                "recommendations": analysis_results.get("recommendations", []),
                "visualizations": analysis_results.get("visualizations", []),
                
                # Business insights
                "executive_summary": business_insights.get("executive_summary", ""),
                "business_findings": business_insights.get("key_findings", []),
                "business_recommendations": business_insights.get("recommendations", []),
                "next_steps": business_insights.get("next_steps", []),
                
                # Metadata for database storage
                "generated_at": datetime.now().isoformat(),
                "status": "success" if "error" not in analysis_results else "error",
                "error_message": analysis_results.get("error") if "error" in analysis_results else None,
                "execution_time": analysis_results.get("execution_time"),
                
                # Legacy fields for backward compatibility
                "analysis_results": analysis_results,
                "insights": business_insights
            }
            
            final_insights.append(insight)
            logger.info(f"✅ Completed analysis for {title}")
        
        logger.info(f"🎉 Generated {len(final_insights)} complete insights")
        return {
            **state, 
            "final_insights": final_insights, 
            "current_step": "insights_complete"
        }
        
    except Exception as e:
        logger.error(f"❌ Insights generation failed: {e}")
        return {
            **state, 
            "final_insights": final_insights,  # Return partial results
            "current_step": "insights_error"
        }
