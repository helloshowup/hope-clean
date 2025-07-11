"""
Storage utility functions for centralized management of API JSON files.

This module provides functions to manage the storage of API request/response JSON files
in a centralized location, making it easier to track and analyze API interactions.

Usage:
    from showup_core.core.storage_utils import get_api_storage_path
    
    # Get path for storing API response JSON
    path = get_api_storage_path('core', 'response_123.json')
    with open(path, 'w') as f:
        json.dump(response_data, f)
"""

from pathlib import Path


def get_api_storage_path(module_name: str, filename: str) -> Path:
    """
    Get the path for storing API-related JSON files in a centralized location.
    
    Args:
        module_name: The name of the module or subproject (e.g., 'core', 'claude_panel', 'tools')
        filename: The name of the JSON file to be stored
        
    Returns:
        Path object pointing to the storage location for the specified JSON file
        
    Example:
        >>> path = get_api_storage_path('core', 'claude_response.json')
        >>> with open(path, 'w') as f:
        >>>     json.dump(response_data, f)
    """
    root = Path(__file__).parents[2] / "data" / "stored_api_calls" / module_name
    root.mkdir(parents=True, exist_ok=True)
    return root / filename
