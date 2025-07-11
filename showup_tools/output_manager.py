"""
Output Manager Module for the Simplified Workflow.

This module handles saving content as markdown files.
"""

import logging
import os
import datetime
from typing import Dict, Any, Optional

# Set up logger
logger = logging.getLogger("simplified_workflow.output_manager")

def save_as_markdown(content: str, metadata: Dict[str, Any], output_path: str) -> str:
    """
    Save content as markdown file.
    
    Args:
        content: Content to save
        metadata: Dictionary with metadata about the content
        output_path: Path where the file should be saved
        
    Returns:
        Path to the saved file
    """
    logger.info(f"Saving content as markdown to {output_path}")
    
    if not content:
        error_msg = "No content provided to save"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Format content with metadata
        formatted_content = _format_markdown_with_metadata(content, metadata)
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(formatted_content)
        
        logger.info(f"Successfully saved content to {output_path}")
        return output_path
        
    except Exception as e:
        error_msg = f"Error saving content: {str(e)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

def _format_markdown_with_metadata(content: str, metadata: Dict[str, Any]) -> str:
    """
    Format content with metadata as markdown.
    
    Args:
        content: Content to format
        metadata: Dictionary with metadata about the content
        
    Returns:
        Formatted markdown string
    """
    logger.info("Formatting content with metadata")
    
    # Extract metadata
    module = metadata.get("module", "")
    lesson = metadata.get("lesson", "")
    step_number = metadata.get("step_number", "")
    step_title = metadata.get("step_title", "").strip()
    template_type = metadata.get("template_type", "")
    
    # Process target_learner field to avoid including the full profile text in the frontmatter
    target_learner = metadata.get("target_learner", "")
    if isinstance(target_learner, str) and len(target_learner) > 500:
        # If target_learner is too long, use a placeholder
        target_learner = "See separate learner profile document"  
    
    # Get generation info
    generation_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Create YAML frontmatter
    frontmatter = f"""---
module: "{module}"
lesson: "{lesson}"
step_number: "{step_number}"
step_title: "{step_title}"
template_type: "{template_type}"
target_learner: "{target_learner}"
generation_date: "{generation_date}"
---

"""
    
    # Add title
    title = f"# {step_title}\n\n"
    
    # Combine frontmatter, title, and content
    formatted_content = frontmatter + title + content
    
    return formatted_content

def create_output_directory(base_dir: str, course_name: str) -> str:
    """
    Create output directory for a course.
    
    Args:
        base_dir: Base directory for output
        course_name: Name of the course
        
    Returns:
        Path to the created directory
    """
    logger.info(f"Creating output directory for course {course_name}")
    
    # Sanitize course name for directory
    sanitized_name = "".join(c if c.isalnum() or c in " -_" else "_" for c in course_name)
    
    # Create directory path with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_path = os.path.join(base_dir, f"{sanitized_name}_{timestamp}")
    
    # Create directory
    os.makedirs(dir_path, exist_ok=True)
    
    logger.info(f"Created output directory: {dir_path}")
    return dir_path

def save_generation_summary(output_dir: str, summary: Dict[str, Any]) -> str:
    """
    Save generation summary as JSON file.
    
    Args:
        output_dir: Directory to save the summary
        summary: Dictionary with generation summary
        
    Returns:
        Path to the saved file
    """
    import json
    
    logger.info("Saving generation summary")
    
    # Create summary file path
    summary_path = os.path.join(output_dir, "generation_summary.json")
    
    try:
        # Write summary to file
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Successfully saved generation summary to {summary_path}")
        return summary_path
        
    except Exception as e:
        error_msg = f"Error saving generation summary: {str(e)}"
        logger.error(error_msg)
        return ""

def save_workflow_log(output_dir: str, log_entries: list) -> str:
    """
    Save workflow log as markdown file.
    
    Args:
        output_dir: Directory to save the log
        log_entries: List of log entries
        
    Returns:
        Path to the saved file
    """
    logger.info("Saving workflow log")
    
    # Create log file path
    log_path = os.path.join(output_dir, "workflow_log.md")
    
    try:
        # Format log entries
        log_content = "# Workflow Log\n\n"
        log_content += "| Timestamp | Step | Status | Message |\n"
        log_content += "|-----------|------|--------|--------|\n"
        
        for entry in log_entries:
            timestamp = entry.get("timestamp", "")
            step = entry.get("step", "")
            status = entry.get("status", "")
            message = entry.get("message", "")
            
            log_content += f"| {timestamp} | {step} | {status} | {message} |\n"
        
        # Write log to file
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        logger.info(f"Successfully saved workflow log to {log_path}")
        return log_path
        
    except Exception as e:
        error_msg = f"Error saving workflow log: {str(e)}"
        logger.error(error_msg)
        return ""