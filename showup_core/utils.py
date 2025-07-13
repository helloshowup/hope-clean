"""
General utility functions for ShowupSquared.

This module provides general-purpose utility functions that don't fit
in other more specific modules.
"""

import importlib
import logging
from typing import Any, List

import claude_api
import cache_utils

logger = logging.getLogger("utils")

def check_dependencies(required_modules: List[str] = None) -> List[str]:
    """
    Check if all required modules are installed.
    
    Args:
        required_modules: List of module names to check, defaults to common dependencies
        
    Returns:
        List of missing module names
    """
    if required_modules is None:
        required_modules = ['streamlit', 'anthropic', 'pandas']
        
    missing = []
    logger.info(f"Checking dependencies: {', '.join(required_modules)}")
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            logger.info(f"✓ Module {module} is installed")
        except ImportError:
            missing.append(module)
            logger.warning(f"✗ Module {module} is missing")
            
    return missing

def safe_convert_to_int(value: Any, default: int = 1, context: str = "value") -> int:
    """
    Convert value to int with simple error handling.
    
    Args:
        value: Value to convert
        default: Default value to return if conversion fails
        context: Context string for logging
        
    Returns:
        Converted integer or default value
    """
    if value is None:
        logger.info(f"Converting None to default int ({default}) for {context}")
        return default
        
    try:
        result = int(value)
        logger.debug(f"Successfully converted {context} '{value}' to int: {result}")
        return result
    except (ValueError, TypeError):
        logger.warning(f"Couldn't convert {context} '{value}' to a number, using {default} instead")
        return default