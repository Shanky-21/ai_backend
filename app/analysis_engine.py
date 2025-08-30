import pandas as pd
import numpy as np
import base64
from io import BytesIO
import matplotlib.pyplot as plt
import sys
from typing import Dict, List, Any

from .utils import safe_json_parse, setup_logger

# Setup logger
logger = setup_logger(__name__)

def get_data_structure_info(relevant_files: List[str], file_metadata: Dict) -> str:
    """Format file metadata for LLM consumption."""
    data_info = ""
    for file_path in relevant_files:
        if file_path in file_metadata:
            metadata = file_metadata[file_path]
            if "error" not in metadata:
                data_info += f"""
File: {metadata['filename']}
Columns: {metadata['columns']}
Shape: {metadata['shape']}
Data Types: {metadata['data_types']}
Sample Data: {metadata['sample_rows'][:2]}
Numeric Columns: {metadata['numeric_columns']}
Categorical Columns: {metadata['categorical_columns']}
---
"""
    return data_info

def generate_analysis_code(suggestion: Dict, data_info: str, llm) -> str:
    """Generate Python analysis code using LLM."""
    
    prompt = f"""Generate Python code to analyze data for this business insight:

INSIGHT: {suggestion['title']}
DESCRIPTION: {suggestion['description']}

DATA AVAILABLE:
{data_info}

Generate a complete analyze_data function that:
1. Loads files from file_paths parameter
2. Performs business-relevant analysis for this specific insight
3. Calculates meaningful metrics
4. Creates 1 simple visualization using matplotlib
5. Returns structured results

CODE TEMPLATE:
```python
def analyze_data(file_paths):
    results = {{
        'metrics': {{}},
        'key_findings': [],
        'visualizations': [],
        'recommendations': []
    }}
    
    try:
        # Load data
        dfs = []
        for path in file_paths:
            if path.endswith('.csv'):
                df = pd.read_csv(path)
            else:
                df = pd.read_excel(path)
            dfs.append(df)
        
        main_df = dfs[0] if dfs else pd.DataFrame()
        
        # YOUR ANALYSIS CODE HERE - be specific to the insight
        
        # Example metrics (replace with actual analysis):
        # results['metrics']['total_records'] = len(main_df)
        
        # Example findings (replace with actual insights):
        # results['key_findings'].append("Key insight from analysis")
        
        # Create one simple visualization
        import matplotlib.pyplot as plt
        plt.figure(figsize=(8, 6))
        # Add your plot code here
        plt.title("{suggestion['title']}")
        
        # Save plot (keep this part)
        import base64
        from io import BytesIO
        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        plot_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()
        
        results['visualizations'].append({{
            'title': '{suggestion['title']} Chart',
            'type': 'analysis',
            'data': plot_base64
        }})
        
        # Add recommendations
        # results['recommendations'].append("Specific actionable recommendation")
        
        return results
        
    except Exception as e:
        results['error'] = str(e)
        return results
```
Generate ONLY the complete Python code with actual analysis logic. No explanations."""

    try:
        response = llm.invoke(prompt)
        return extract_code_from_response(response.content)
    except Exception as e:
        logger.error(f"❌ Code generation failed: {e}")
        return create_fallback_analysis_code(suggestion)

def extract_code_from_response(llm_response: str) -> str:
    """Extract Python code from LLM response."""
    if "```python" in llm_response:
        code = llm_response.split("```python")[1].split("```")[0]
    elif "```" in llm_response:
        code = llm_response.split("```")[1].split("```")[0]
    else:
        code = llm_response

    return code.strip()

def create_fallback_analysis_code(suggestion: Dict) -> str:
    """Create basic fallback analysis code."""
    return f'''
def analyze_data(file_paths):
    results = {{
        'metrics': {{}},
        'key_findings': [],
        'visualizations': [],
        'recommendations': []
    }}

    try:
        import pandas as pd
        
        dfs = []
        for path in file_paths:
            if path.endswith('.csv'):
                df = pd.read_csv(path)
            else:
                df = pd.read_excel(path)
            dfs.append(df)
        
        main_df = dfs[0] if dfs else pd.DataFrame()
        
        results['metrics']['total_records'] = len(main_df)
        results['key_findings'].append("Basic analysis completed")
        results['recommendations'].append("Review data for insights")
        
        return results
        
    except Exception as e:
        results['error'] = str(e)
        return results
'''

def get_safe_builtins() -> Dict:
    """Return restricted builtins for safe code execution."""
    return {
        'len': len, 'range': range, 'enumerate': enumerate,
        'zip': zip, 'sum': sum, 'max': max, 'min': min,
        'abs': abs, 'round': round, 'str': str, 'int': int,
        'float': float, 'list': list, 'dict': dict,
        'print': print, 'sorted': sorted, 'any': any, 'all': all,
        '__import__': __import__, '__name__': '__main__'
    }

def execute_analysis_code(code: str, file_paths: List[str]) -> Dict:
    """Safely execute generated analysis code."""
    logger.info("🔧 Executing analysis code...")
    
    try:
        # Create safe execution environment
        safe_globals = {
            'pandas': pd,
            'pd': pd,
            'numpy': np,
            'np': np,
            'matplotlib': plt,
            'plt': plt,
            'base64': base64,
            'BytesIO': BytesIO,
            '__builtins__': get_safe_builtins()
        }
        
        safe_locals = {'file_paths': file_paths}
        
        # Capture stdout
        old_stdout = sys.stdout
        from io import StringIO
        sys.stdout = captured_output = StringIO()
        
        try:
            # Execute the generated code
            exec(code, safe_globals, safe_locals)
            
            # Call the analyze_data function
            if 'analyze_data' in safe_locals:
                results = safe_locals['analyze_data'](file_paths)
                logger.info("✅ Code executed successfully")
                return results
            else:
                logger.error("❌ analyze_data function not found")
                return {"error": "analyze_data function not found in generated code"}
                
        finally:
            sys.stdout = old_stdout
            
    except Exception as e:
        logger.error(f"❌ Code execution failed: {e}")
        return {
            "error": f"Execution failed: {str(e)}",
            "metrics": {},
            "key_findings": ["Analysis could not be completed due to execution error"],
            "visualizations": [],
            "recommendations": ["Please check data format and try again"]
        }

def generate_insight_summary(suggestion: Dict, analysis_results: Dict, llm) -> Dict:
    """Generate business summary from technical analysis results."""
    
    if 'error' in analysis_results:
        return {
            "executive_summary": f"Analysis for {suggestion['title']} encountered issues",
            "key_findings": ["Technical analysis could not be completed"],
            "recommendations": ["Please check data quality and format"],
            "next_steps": ["Verify data integrity and retry analysis"]
        }
    
    try:
        prompt = f"""Convert these technical analysis results into clear business insights:

ANALYSIS FOR: {suggestion['title']}
DESCRIPTION: {suggestion['description']}

TECHNICAL RESULTS:
- Metrics: {analysis_results.get('metrics', {})}
- Findings: {analysis_results.get('key_findings', [])}
- Recommendations: {analysis_results.get('recommendations', [])}

Provide business-friendly summary as JSON:
{{
    "executive_summary": "2-3 sentence business summary",
    "key_findings": ["business insight 1", "business insight 2"],
    "recommendations": ["actionable step 1", "actionable step 2"],
    "next_steps": ["immediate action 1", "immediate action 2"]
}}"""

        response = llm.invoke(prompt)
        business_insights = safe_json_parse(response.content, {
            "executive_summary": f"Analysis completed for {suggestion['title']}",
            "key_findings": analysis_results.get('key_findings', ["Analysis in progress"]),
            "recommendations": analysis_results.get('recommendations', ["Review results"]),
            "next_steps": ["Continue monitoring", "Implement recommendations"]
        })
        
        return business_insights
        
    except Exception as e:
        logger.error(f"❌ Insight summary generation failed: {e}")
        return {
            "executive_summary": f"Technical analysis completed for {suggestion['title']}",
            "key_findings": analysis_results.get('key_findings', ["Analysis completed"]),
            "recommendations": analysis_results.get('recommendations', ["Review technical results"]),
            "next_steps": ["Analyze results", "Take action based on findings"]
        }
