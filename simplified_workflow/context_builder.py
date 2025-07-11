"""
Context Builder Module for the Simplified Workflow.

This module handles building educational continuity context from adjacent steps in the CSV.
"""

import logging
from typing import Dict, List, Any, Optional

# Set up logger
logger = logging.getLogger("simplified_workflow.context_builder")

def build_context_from_adjacent_steps(csv_rows: List[Dict[str, str]], 
                                     current_row_index: int) -> str:
    """
    Build educational continuity context from adjacent steps in the CSV.
    
    Args:
        csv_rows: List of dictionaries representing rows in the CSV file
        current_row_index: Index of the current row being processed
        
    Returns:
        Formatted context string with information about previous and next steps
    """
    logger.info(f"Building context from adjacent steps for row {current_row_index}")
    
    if not csv_rows or current_row_index < 0 or current_row_index >= len(csv_rows):
        logger.warning(f"Invalid row index {current_row_index} for context building")
        return ""
    
    current_row = csv_rows[current_row_index]
    current_module = current_row.get("Module", "")
    current_lesson = current_row.get("Lesson", "")
    
    # Get previous step (prioritize same module/lesson)
    previous_context = ""
    if current_row_index > 0:
        for i in range(current_row_index - 1, -1, -1):
            prev_row = csv_rows[i]
            prev_module = prev_row.get("Module", "")
            prev_lesson = prev_row.get("Lesson", "")
            
            # Check if it's in the same module and lesson
            if prev_module == current_module and prev_lesson == current_lesson:
                previous_context = _format_step_context(prev_row, "Previous step")
                break
            
            # If we can't find a step in the same module/lesson, use the immediately previous step
            if i == current_row_index - 1:
                previous_context = _format_step_context(prev_row, "Previous step (different lesson)")
    
    # Get next step (prioritize same module/lesson)
    next_context = ""
    if current_row_index < len(csv_rows) - 1:
        for i in range(current_row_index + 1, len(csv_rows)):
            next_row = csv_rows[i]
            next_module = next_row.get("Module", "")
            next_lesson = next_row.get("Lesson", "")
            
            # Check if it's in the same module and lesson
            if next_module == current_module and next_lesson == current_lesson:
                next_context = _format_step_context(next_row, "Next step")
                break
            
            # If we can't find a step in the same module/lesson, use the immediately next step
            if i == current_row_index + 1:
                next_context = _format_step_context(next_row, "Next step (different lesson)")
    
    # Combine contexts
    context_parts = []
    if previous_context:
        context_parts.append(previous_context)
    if next_context:
        context_parts.append(next_context)
    
    if not context_parts:
        logger.info("No adjacent steps found for context building")
        return ""
    
    formatted_context = "\n\n".join(context_parts)
    logger.info(f"Built context with {len(context_parts)} adjacent steps")
    
    return formatted_context

def _format_step_context(row: Dict[str, str], prefix: str) -> str:
    """
    Format a step's information for use in context.
    
    Args:
        row: Dictionary representing a row from the CSV file
        prefix: Prefix to use (e.g., "Previous step", "Next step")
        
    Returns:
        Formatted context string for the step
    """
    step_title = row.get("Step title", "")
    rationale = row.get("What is the rationale for this step", "")
    content_outline = row.get("Content Outline", "")
    
    # Combine rationale and content outline
    content = ""
    if rationale:
        content += rationale
    if content_outline:
        if content:
            content += ". "
        content += content_outline
    
    if not content:
        content = "No content available"
    
    return f"{prefix}: {step_title}\n{content}"

def build_context_for_comparison(csv_rows: List[Dict[str, str]], 
                               current_row_index: int) -> Dict[str, str]:
    """
    Build context information for the content comparison step.
    
    Args:
        csv_rows: List of dictionaries representing rows in the CSV file
        current_row_index: Index of the current row being processed
        
    Returns:
        Dictionary with context information for comparison
    """
    logger.info(f"Building comparison context for row {current_row_index}")
    
    # Get educational continuity context
    continuity_context = build_context_from_adjacent_steps(csv_rows, current_row_index)
    
    # Get current row information
    current_row = csv_rows[current_row_index]
    module = current_row.get("Module", "")
    lesson = current_row.get("Lesson", "")
    step_number = current_row.get("Step number", "")
    step_title = current_row.get("Step title", "")
    
    # Build template context
    template_context = (
        f"This content is for Module {module}, Lesson {lesson}, Step {step_number}: {step_title}. "
        f"The content should follow the educational content template structure with appropriate "
        f"headings, examples, and engagement opportunities."
    )
    
    # Combine contexts
    context = {
        "TEMPLATE": template_context
    }
    
    if continuity_context:
        context["CONTEXT"] = continuity_context
    
    logger.info(f"Built comparison context with {len(context)} elements")
    return context