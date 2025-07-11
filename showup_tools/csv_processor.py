"""
CSV Processing Module for the Simplified Workflow.

This module handles reading CSV files and extracting variables needed for content generation.
"""

import csv
import logging
import os
from typing import Dict, List, Any, Optional

# Set up logger
logger = logging.getLogger("simplified_workflow.csv_processor")

def read_csv(csv_path: str) -> List[Dict[str, str]]:
    """
    Read CSV file and return rows as a list of dictionaries.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        List of dictionaries representing rows in the CSV file
        
    Raises:
        FileNotFoundError: If the CSV file does not exist
        ValueError: If the CSV file is empty or has invalid format
    """
    logger.info(f"Reading CSV file: {csv_path}")
    
    if not os.path.exists(csv_path):
        error_msg = f"CSV file not found: {csv_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        if not rows:
            error_msg = f"CSV file is empty: {csv_path}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Check for required columns with flexible matching
        required_columns = [
            "Module", "Lesson", "Step number", "Step title", "Template Type"
        ]
        
        # Check for rationale column with or without question mark
        rationale_columns = ["What is the rationale for this step", "What is the rationale for this step?"]
        has_rationale = any(col in rows[0] for col in rationale_columns)
        if not has_rationale:
            required_columns.append("What is the rationale for this step")
        
        # Check for content outline column
        content_columns = ["Content Outline"]
        has_content = any(col in rows[0] for col in content_columns)
        if not has_content:
            required_columns.append("Content Outline")
        
        # Validate required columns
        missing_columns = [col for col in required_columns if col not in rows[0] and col not in rationale_columns]
        if missing_columns:
            error_msg = f"CSV file missing required columns: {', '.join(missing_columns)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Normalize column names for consistent access
        normalized_rows = []
        for row in rows:
            normalized_row = {}
            for key, value in row.items():
                # Normalize rationale column
                if key in rationale_columns:
                    normalized_row["What is the rationale for this step"] = value
                else:
                    normalized_row[key] = value
            normalized_rows.append(normalized_row)
        
        logger.info(f"Successfully read {len(normalized_rows)} rows from CSV file")
        return normalized_rows
        
    except Exception as e:
        error_msg = f"Error reading CSV file: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

def extract_variables(row: Dict[str, str], course_name: str, learner_profile: str) -> Dict[str, str]:
    """
    Extract variables from CSV row and settings for use in templates.
    
    Args:
        row: Dictionary representing a row from the CSV file
        course_name: Name of the course (e.g., photography, interior design)
        learner_profile: Description of the target learner
        
    Returns:
        Dictionary with variables for template substitution
    """
    logger.info(f"Extracting variables for module {row.get('Module', 'unknown')}, "
                f"lesson {row.get('Lesson', 'unknown')}, "
                f"step {row.get('Step number', 'unknown')}")
    
    # Extract rationale and content outline as separate variables
    rationale = row.get("What is the rationale for this step", "").strip()
    content_outline = row.get("Content Outline", "").strip()
    
    # Create a default objective if neither is available
    if not rationale and not content_outline:
        objective = f"Learn about {row.get('Step title', 'this topic')}"
    else:
        # Keep a simple objective based on the step title
        objective = f"Learn about {row.get('Step title', 'this topic')}"
    
    # Create variables dictionary
    variables = {
        "topic": course_name,
        "objective": objective,
        "rationale": rationale,  # Keep rationale as a separate variable
        "content_outline": content_outline,  # Keep content outline as a separate variable
        "target_learner": learner_profile,
        "course_name": course_name,
        "module": row.get("Module", ""),
        "lesson": row.get("Lesson", ""),
        "step_number": row.get("Step number", ""),
        "step_title": row.get("Step title", ""),
        "template_type": row.get("Template Type", "")
    }
    
    # Replace any non-breaking hyphens (‑) with regular hyphens to avoid encoding issues in console output
    safe_step_title = variables['step_title'].replace('‑', '-')
    safe_template_type = variables['template_type'].replace('‑', '-')
    
    logger.info(f"Extracted variables: topic={course_name}, "
                f"step_title={safe_step_title}, "
                f"template_type={safe_template_type}")
    
    return variables

def process_csv(csv_path: str, course_name: str, learner_profile: str) -> List[Dict[str, str]]:
    """
    Process a CSV file and extract variables for each row, for use in content generation workflows.

    Args:
        csv_path: Path to the CSV file
        course_name: Name of the course (e.g., photography, interior design)
        learner_profile: Description of the target learner

    Returns:
        List of dictionaries, each containing variables for a workflow step.
    """
    rows = read_csv(csv_path)
    result = []
    for row in rows:
        variables = extract_variables(row, course_name, learner_profile)
        result.append(variables)
    return result

def get_output_path(row: Dict[str, str], base_output_dir: str) -> str:
    """
    Generate output file path based on module, lesson, and step information.
    
    Args:
        row: Dictionary representing a row from the CSV file
        base_output_dir: Base directory for output files
        
    Returns:
        Path where the output file should be saved
    """
    module = row.get("Module", "unknown_module")
    lesson = row.get("Lesson", "unknown_lesson")
    step_number = row.get("Step number", "unknown_step")
    step_title = row.get("Step title", "unknown_title")
    
    # Create sanitized filename
    sanitized_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in step_title)
    filename = f"{step_number}_{sanitized_title.strip()}.md"
    
    # Create directory path - organize by module within the base output directory
    dir_path = os.path.join(base_output_dir, module)
    os.makedirs(dir_path, exist_ok=True)
    
    # Full file path
    file_path = os.path.join(dir_path, filename)
    
    logger.info(f"Generated output path: {file_path}")
    return file_path