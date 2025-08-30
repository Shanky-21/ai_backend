from typing_extensions import TypedDict
from typing import List, Dict, Any

class InsightState(TypedDict):
    files: List[str]
    business_description: str
    file_metadata: Dict[str, Any]
    business_understanding: str
    help_suggestions: List[Dict[str, Any]]
    file_mappings: Dict[str, List[str]]
    final_insights: List[Dict[str, Any]]
    current_step: str
