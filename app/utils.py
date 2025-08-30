import pandas as pd
import os
import json
import logging
from typing import List, Dict, Any, Optional

def detect_file_type(filename: str) -> str:
    """Detect file type from extension."""
    ext = filename.lower().split('.')[-1]
    if ext == 'csv':
        return 'csv'
    elif ext in ['xlsx', 'xls']:
        return 'excel'
    else:
        return 'unknown'

def load_dataframe(file_path: str) -> pd.DataFrame:
    """Safely load DataFrame from various file formats."""
    try:
        file_type = detect_file_type(file_path)
        if file_type == 'csv':
            return pd.read_csv(file_path)
        elif file_type == 'excel':
            return pd.read_excel(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    except Exception as e:
        raise Exception(f"Failed to load {file_path}: {str(e)}")

def safe_json_parse(text: str, fallback: Dict = None) -> Dict:
    """Parse JSON with fallback handling."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return fallback or {}

def format_dataframe_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """Create comprehensive metadata summary of DataFrame."""
    try:
        return {
            "filename": "unknown",  # Will be set by caller
            "columns": list(df.columns),
            "shape": df.shape,
            "sample_rows": df.head(3).to_dict('records'),
            "data_types": df.dtypes.astype(str).to_dict(),
            "null_counts": df.isnull().sum().to_dict(),
            "numeric_columns": df.select_dtypes(include=['number']).columns.tolist(),
            "categorical_columns": df.select_dtypes(include=['object']).columns.tolist()
        }
    except Exception as e:
        return {"error": f"Failed to analyze DataFrame: {str(e)}"}

def setup_logger(name: str) -> logging.Logger:
    """Setup logger with proper formatting."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
