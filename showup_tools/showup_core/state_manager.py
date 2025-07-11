"""
State management module for ShowupSquared.

This module provides functionality for tracking and managing the state of content
generation to avoid unnecessary regeneration of content.
"""

import os
import json
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, Tuple

# Import core components
from .config import DIRS

logger = logging.getLogger("state_manager")

def get_work_state(course_id: str) -> Dict[str, Any]:
    """
    Get current work state for a course.
    
    Args:
        course_id: Course identifier
        
    Returns:
        State dictionary for the course
    """
    state_path = os.path.join(DIRS['data']['settings'], f"{course_id}_state.json")
    if os.path.exists(state_path):
        try:
            with open(state_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading state file for {course_id}: {str(e)}")
            
    # Return empty state with timestamp if no state exists or error occurred
    return {"last_updated": datetime.now().isoformat(), "modules": {}}

def save_work_state(course_id: str, state: Dict[str, Any]) -> bool:
    """
    Save work state for a course.
    
    Args:
        course_id: Course identifier
        state: State dictionary to save
        
    Returns:
        True if successful, False otherwise
    """
    state_path = os.path.join(DIRS['data']['settings'], f"{course_id}_state.json")
    state["last_updated"] = datetime.now().isoformat()
    
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        
        with open(state_path, 'w') as f:
            json.dump(state, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving state for {course_id}: {str(e)}")
        return False

def calculate_file_hash(file_path: str) -> str:
    """
    Calculate a simple hash of file content for change detection.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MD5 hash of the file content
    """
    try:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {str(e)}")
        return ""

def update_module_state(course_id: str, module_num: int, result: Dict[str, Any], 
                       input_data: Dict[str, Any]) -> bool:
    """
    Update state after module generation.
    
    Args:
        course_id: Course identifier
        module_num: Module number
        result: Generation result
        input_data: Input data used for generation
        
    Returns:
        True if successful, False otherwise
    """
    state = get_work_state(course_id)
    
    # Calculate simple hash of CSV file for change detection
    csv_hash = ""
    if input_data.get('csv_path') and os.path.exists(input_data['csv_path']):
        csv_hash = calculate_file_hash(input_data['csv_path'])
    
    # Update module state
    if "modules" not in state:
        state["modules"] = {}
    
    # Extract info from generation result
    state["modules"][str(module_num)] = {
        "generated_at": datetime.now().isoformat(),
        "csv_file": os.path.basename(input_data.get('csv_path', '')),
        "csv_hash": csv_hash,
        "learner_profile": os.path.basename(input_data.get('learner_path', '')),
        "model_used": result.get('model_used', 'unknown'),
        "output_paths": {
            "module_analysis": result.get('module_analysis_path', ''),
            "lesson_flow": result.get('lesson_flow_path', ''),
            "course_outline": result.get('course_outline_path', '')
        },
        "quality_scores": {
            "module_analysis": result.get('module_analysis_quality', 0),
            "lesson_flow": result.get('lesson_flow_quality', 0)
        },
        "ai_writing_detection": {
            "module_analysis_refined": result.get('module_analysis_refined', False),
            "lesson_flow_refined": result.get('lesson_flow_refined', False)
        }
    }
    
    # Save updated state
    return save_work_state(course_id, state)

def update_lesson_state(course_id: str, module_num: int, lesson_num: int, 
                       result: Dict[str, Any]) -> bool:
    """
    Update state after lesson generation.
    
    Args:
        course_id: Course identifier
        module_num: Module number
        lesson_num: Lesson number
        result: Generation result
        
    Returns:
        True if successful, False otherwise
    """
    state = get_work_state(course_id)
    
    # Ensure module exists in state
    if "modules" not in state:
        state["modules"] = {}
    if str(module_num) not in state["modules"]:
        state["modules"][str(module_num)] = {
            "generated_at": datetime.now().isoformat(),
            "lessons": {}
        }
    
    # Update or add lesson state
    module_state = state["modules"][str(module_num)]
    if "lessons" not in module_state:
        module_state["lessons"] = {}
    
    module_state["lessons"][str(lesson_num)] = {
        "generated_at": datetime.now().isoformat(),
        "output_path": result.get('lesson_content_path', ''),
        "model_used": result.get('model_used', 'unknown'),
        "quality_score": result.get('lesson_quality', 0),
        "ai_writing_refined": result.get('lesson_content_refined', False)
    }
    
    # Save updated state
    return save_work_state(course_id, state)

def is_work_needed(course_id: str, module_num: int, csv_path: str, 
                  learner_path: str, force_regenerate: bool = False) -> Tuple[bool, str]:
    """
    Check if work generation is needed.
    
    Args:
        course_id: Course identifier
        module_num: Module number
        csv_path: Path to CSV file
        learner_path: Path to learner profile
        force_regenerate: Force regeneration regardless of state
        
    Returns:
        Tuple of (work_needed, reason)
    """
    # Always regenerate if forced
    if force_regenerate:
        return True, "Force regeneration requested"
    
    # Get current state
    state = get_work_state(course_id)
    
    # Check if module state exists
    if "modules" not in state or str(module_num) not in state["modules"]:
        return True, "No previous generation found"
    
    module_state = state["modules"][str(module_num)]
    
    # Check if input files exist
    if not os.path.exists(csv_path) or not os.path.exists(learner_path):
        return True, "Input files not found"
    
    # Check if input files have changed
    current_csv_hash = calculate_file_hash(csv_path)
    if current_csv_hash != module_state.get("csv_hash") and current_csv_hash != "":
        return True, "CSV file content has changed"
    
    # Check if CSV filename changed
    if os.path.basename(csv_path) != module_state.get("csv_file"):
        return True, "Different CSV file selected"
    
    # Check if learner profile changed
    if os.path.basename(learner_path) != module_state.get("learner_profile"):
        return True, "Different learner profile selected"
    
    # Check if output files exist
    for key, path in module_state.get("output_paths", {}).items():
        if not path or not os.path.exists(path):
            return True, f"Output file missing: {key}"
    
    # Work already done and inputs haven't changed
    return False, "Work already exists with current inputs"

def format_timestamp(timestamp_str: str) -> str:
    """
    Format a timestamp string to a human-readable format.
    
    Args:
        timestamp_str: ISO format timestamp string
        
    Returns:
        Human-readable timestamp string
    """
    try:
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime("%B %d, %Y at %I:%M %p")
    except Exception:
        return timestamp_str