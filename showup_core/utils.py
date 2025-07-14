"""
General utility functions for ShowupSquared.

This module provides general-purpose utility functions that don't fit
in other more specific modules.
"""

import importlib
import logging
import os
from typing import Any, List


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
        required_modules = ['streamlit', 'pandas']
        
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


def get_project_root() -> str:
    """Returns the absolute path to the project root."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_prompt(prompt_name: str) -> str:
    """Load a prompt from the /prompts directory.

    Args:
        prompt_name: Path to the prompt file relative to the /prompts directory
                      (e.g., 'planning/lesson_plan').

    Returns:
        The content of the prompt file as a string. Returns an empty string if
        the file cannot be found.
    """
    root_dir = get_project_root()
    prompt_path = os.path.join(root_dir, 'prompts', f"{prompt_name}.txt")
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Prompt file not found at {prompt_path}")
        return ""