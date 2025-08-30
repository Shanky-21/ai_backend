import pandas as pd
import os
import json
import logging
import tempfile
from io import BytesIO
from typing import List, Dict, Any, Optional, Union

def detect_file_type(filename: str) -> str:
    """Detect file type from extension."""
    ext = filename.lower().split('.')[-1]
    if ext == 'csv':
        return 'csv'
    elif ext in ['xlsx', 'xls']:
        return 'excel'
    else:
        return 'unknown'

def load_dataframe_from_bytes(file_data: bytes, filename: str) -> pd.DataFrame:
    """Load DataFrame from bytea data."""
    try:
        if not file_data:
            raise ValueError("File data is empty")
            
        file_type = detect_file_type(filename)
        buffer = BytesIO(file_data)
        
        if file_type == 'csv':
            return pd.read_csv(buffer)
        elif file_type == 'excel':
            return pd.read_excel(buffer)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")
    except Exception as e:
        raise Exception(f"Failed to load {filename} from bytes: {str(e)}")

def load_dataframe_from_file_object(file_obj: Dict[str, Any]) -> pd.DataFrame:
    """Load DataFrame from file object (supports both bytea data and file path)."""
    try:
        # Prioritize bytea data if available
        if file_obj.get('files_data'):
            return load_dataframe_from_bytes(
                file_obj['files_data'], 
                file_obj.get('original_name', file_obj.get('filename', 'unknown.csv'))
            )
        # Fallback to file path
        elif file_obj.get('file_path'):
            return load_dataframe(file_obj['file_path'])
        else:
            raise ValueError("No file data or path available in file object")
    except Exception as e:
        raise Exception(f"Failed to load file object: {str(e)}")

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

def create_temp_file_from_bytes(file_data: bytes, filename: str) -> str:
    """Create a temporary file from bytea data and return the path."""
    try:
        # Get file extension
        _, ext = os.path.splitext(filename)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
            tmp_file.write(file_data)
            temp_path = tmp_file.name
            
        return temp_path
    except Exception as e:
        raise Exception(f"Failed to create temp file from bytes: {str(e)}")

def file_objects_to_temp_paths(file_objects: List[Dict[str, Any]]) -> List[str]:
    """Convert file objects to temporary file paths for backward compatibility."""
    temp_paths = []
    
    for file_obj in file_objects:
        try:
            # If bytea data is available, create temp file
            if file_obj.get('files_data'):
                filename = file_obj.get('original_name', file_obj.get('filename', 'unknown.csv'))
                temp_path = create_temp_file_from_bytes(file_obj['files_data'], filename)
                temp_paths.append(temp_path)
            # Fallback to existing file path
            elif file_obj.get('file_path'):
                temp_paths.append(file_obj['file_path'])
            else:
                raise ValueError(f"No data available for file {file_obj.get('id', 'unknown')}")
                
        except Exception as e:
            # Log error but continue with other files
            logger = setup_logger(__name__)
            logger.error(f"❌ Failed to process file object: {e}")
            continue
    
    return temp_paths

def cleanup_temp_files(file_paths: List[str]) -> None:
    """Clean up temporary files created from bytea data."""
    logger = setup_logger(__name__)
    
    for file_path in file_paths:
        try:
            # Only delete files in temp directory to be safe
            if '/tmp/' in file_path or 'temp' in file_path.lower():
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.debug(f"🗑️ Cleaned up temp file: {file_path}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to clean up temp file {file_path}: {e}")

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
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    return logger
