"""
CSV parsing utilities for ShowupSquared.

This module provides functions to extract lesson and step information from CSV files,
with intelligent column identification for flexible CSV formats.
"""

import csv
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("csv_parser")

def extract_lessons_and_steps_from_csv(csv_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract both lesson and step information from a CSV file.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        Dictionary with module-lesson keys and lists of step dictionaries as values
    """
    logger.info(f"Extracting lessons and steps from CSV: {csv_path}")
    lessons_with_steps = {}  # Dict to hold module-lesson mapping to steps
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            logger.info(f"Read {len(rows)} rows from CSV")
            
            # First pass: Get column names to understand the CSV structure
            if not rows:
                logger.warning("CSV contains no data rows")
                return lessons_with_steps
                
            columns = list(rows[0].keys())
            logger.info(f"CSV Parser found columns: {', '.join(columns)}")
            
            # Log the actual columns found for debugging
            logger.debug(f"CSV columns found: {', '.join(columns)}")
            
            # Identify column names for module, lesson, step information
            module_cols = [col for col in columns if any(term in col.lower() for term in
                          ['module', 'unit', 'section'])]
            lesson_cols = [col for col in columns if 'lesson' in col.lower() and not any(term in col.lower() for term in
                          ['step', 'objective'])]
            step_number_cols = []  # Will handle step numbers differently
            step_title_cols = [col for col in columns if any(term in col.lower() for term in
                              ['step title', 'step name', 'step_title', 'step'])]
            step_type_cols = [col for col in columns if any(term in col.lower() for term in
                             ['step type', 'step_type', 'content type', 'format', 'type'])]
            template_type_cols = [col for col in columns if any(term in col.lower() for term in
                                 ['template type', 'template_type', 'template'])]
            
            logger.debug(f"Module columns: {module_cols}")
            logger.debug(f"Lesson columns: {lesson_cols}")
            logger.debug(f"Step title columns: {step_title_cols}")
            logger.debug(f"Step type columns: {step_type_cols}")
            logger.debug(f"Template type columns: {template_type_cols}")
            step_rationale_cols = [col for col in columns if any(term in col.lower() for term in
                                  ['rationale', 'reasoning', 'purpose'])]
            step_content_cols = [col for col in columns if any(term in col.lower() for term in
                                ['content outline', 'content_outline', 'outline', 'content description'])]
            step_hours_cols = [col for col in columns if any(term in col.lower() for term in
                              ['notional hours', 'hours', 'duration', 'time'])]
            
            logger.debug(f"Identified data columns: Module: {module_cols}, Lesson: {lesson_cols}, Step Number: {step_number_cols}")
            
            # Process all rows
            for i, row in enumerate(rows):
                logger.debug(f"Processing row {i+1}/{len(rows)}")
                
                # Try both direct column access and parsing from column names
                # Direct column names (if they exist)
                module_id = row.get('Module', None)
                lesson_id = row.get('Lesson', None)
                
                # If direct access fails, try the identified columns
                if not module_id and module_cols:
                    module_id = get_first_non_empty_col_value(row, module_cols)
                
                if not lesson_id and lesson_cols:
                    lesson_id = get_first_non_empty_col_value(row, lesson_cols)
                
                # Default values if still not found
                module_id = module_id or "Module 1"
                lesson_id = lesson_id or "Lesson 1"
                
                # For step number, try to extract from step title if needed
                step_num = i + 1  # Default to row index if nothing else works
                step_title = get_first_non_empty_col_value(row, step_title_cols)
                
                # Get step type
                step_type = get_first_non_empty_col_value(row, step_type_cols) or "Article"
                
                # Get template type
                template_type = get_first_non_empty_col_value(row, template_type_cols) or None
                
                # Get rationale and content
                step_rationale = get_first_non_empty_col_value(row, step_rationale_cols) or ""
                step_content = get_first_non_empty_col_value(row, step_content_cols) or ""
                
                # Convert values to strings for consistent handling
                module_id = str(module_id).strip()
                lesson_id = str(lesson_id).strip()
                
                logger.debug(f"Extracted: Module={module_id}, Lesson={lesson_id}, Title={step_title}, Type={step_type}")
                
                # Fix: Just to make sure we have valid values
                if not step_title:
                    step_title = f"Step {step_num}"
                
                # Create unique key for this module-lesson combination
                module_lesson_key = f"{module_id}_{lesson_id}"
                
                # Create step data
                step_data = {
                    'module': module_id,
                    'lesson': lesson_id,
                    'step_number': str(step_num),
                    'step_title': step_title or f"Step {step_num}",
                    'step_type': step_type,
                    'template_type': template_type,
                    'step_rationale': step_rationale,
                    'step_content': step_content,
                    'step_hours': get_first_non_empty_col_value(row, step_hours_cols) or "1",
                    'raw_data': row  # Store original row for reference
                }
                
                # Add to collection
                if module_lesson_key not in lessons_with_steps:
                    lessons_with_steps[module_lesson_key] = []
                    
                lessons_with_steps[module_lesson_key].append(step_data)
                
            # Sort steps in each lesson by step number
            for module_lesson, steps in lessons_with_steps.items():
                lessons_with_steps[module_lesson] = sorted(
                    steps, 
                    key=lambda x: int(''.join(filter(str.isdigit, x['step_number'])) or 0)
                )
                
            logger.info(f"Extracted {len(lessons_with_steps)} module-lesson combinations with steps")
            return lessons_with_steps
            
    except Exception as e:
        logger.error(f"Error extracting lessons from CSV {csv_path}: {str(e)}")
        return {}

def extract_lessons_from_csv(csv_path: str) -> List[Dict[str, Any]]:
    """
    Extract only lesson information from a CSV file.
    
    Args:
        csv_path: Path to the CSV file
        
    Returns:
        List of lesson dictionaries with metadata
    """
    logger.info(f"Extracting lessons from CSV: {csv_path}")
    
    try:
        # Extract the full data first
        lessons_with_steps = extract_lessons_and_steps_from_csv(csv_path)
        
        # Compile lesson information
        lessons = []
        for module_lesson_key, steps in lessons_with_steps.items():
            if not steps:
                continue
                
            # Use the first step in each lesson for metadata
            first_step = steps[0]
            
            # Create lesson data
            lesson_data = {
                'module': first_step['module'],
                'lesson': first_step['lesson'],
                'module_lesson_key': module_lesson_key,
                'step_count': len(steps),
                'steps': [step['step_title'] for step in steps],
                'step_types': [step['step_type'] for step in steps],
                'template_types': [step.get('template_type') for step in steps],
                'total_hours': sum(float(step['step_hours']) for step in steps if step['step_hours'].replace('.', '', 1).isdigit()),
            }
            
            lessons.append(lesson_data)
        
        # Sort lessons by module then lesson
        def sort_key(lesson):
            module_num = int(''.join(filter(str.isdigit, lesson['module'])) or 0)
            lesson_num = int(''.join(filter(str.isdigit, lesson['lesson'])) or 0)
            return (module_num, lesson_num)
            
        lessons = sorted(lessons, key=sort_key)
        
        logger.info(f"Extracted {len(lessons)} lessons from CSV")
        return lessons
        
    except Exception as e:
        logger.error(f"Error extracting lessons from CSV {csv_path}: {str(e)}")
        return []

def get_first_non_empty_col_value(row: Dict[str, str], columns: List[str]) -> Optional[str]:
    """
    Get the first non-empty value from a list of possible columns.
    
    Args:
        row: Dictionary representing a CSV row
        columns: List of column names to check
        
    Returns:
        First non-empty value found or None
    """
    # Log debug info at the highest verbosity level
    logger.debug(f"Checking columns: {columns}")
    
    # Case-insensitive match - create a map of lowercase keys to actual keys
    lc_map = {k.lower(): k for k in row.keys()}
    
    # First, try exact matches
    for col in columns:
        if col in row and row[col] and str(row[col]).strip():
            logger.debug(f"Found direct match for '{col}'")
            return str(row[col]).strip()
    
    # Then try case-insensitive matches
    for col in columns:
        col_lower = col.lower()
        if col_lower in lc_map:
            actual_key = lc_map[col_lower]
            if row[actual_key] and str(row[actual_key]).strip():
                logger.debug(f"Found case-insensitive match: '{col}' -> '{actual_key}'")
                return str(row[actual_key]).strip()
    
    # Partial matching as a last resort
    for col in columns:
        col_lower = col.lower()
        for key in row.keys():
            key_lower = key.lower()
            if col_lower in key_lower or key_lower in col_lower:
                if row[key] and str(row[key]).strip():
                    logger.debug(f"Found partial match: '{col}' ~ '{key}'")
                    return str(row[key]).strip()
    
    logger.debug(f"No match found for columns: {columns}")
    return None

def ensure_ai_phrases_file(file_path: str = "data/config/ai_phrases.json") -> bool:
    """
    Ensure the AI phrases file exists, creating it with default content if needed.
    
    Args:
        file_path: Path to the AI phrases file
        
    Returns:
        True if file exists or was created, False on error
    """
    from .file_utils import file_exists, safe_write_file
    
    logger.info(f"Ensuring AI phrases file exists at {file_path}")
    
    if file_exists(file_path):
        logger.info(f"AI phrases file already exists at {file_path}")
        return True
        
    # Default AI phrases to detect
    default_phrases = {
        "phrases": [
            "I'll explain",
            "In this article",
            "As an AI language model",
            "As a language model",
            "Based on my training",
            "I don't have personal",
            "I cannot browse",
            "I don't have the ability to",
            "My knowledge is limited",
            "My training includes",
            "Let me think about this",
            "I'm not able to",
            "I don't have access to",
            "I was trained on",
            "I can't provide",
            "I'd be happy to",
            "I'd be glad to",
            "I can't browse",
            "I can help you with that",
            "Let me explain"
        ],
        "updated": "2024-03-25"
    }
    
    # Create the file
    success, message = safe_write_file(
        file_path, 
        content=json.dumps(default_phrases, indent=2),
        encoding='utf-8'
    )
    
    if success:
        logger.info(f"Created default AI phrases file at {file_path}")
        return True
    else:
        logger.error(f"Failed to create AI phrases file: {message}")
        return False

# Import needed at the bottom to avoid circular import issues
import json