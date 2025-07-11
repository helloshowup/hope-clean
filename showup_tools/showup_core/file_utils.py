"""
File utilities for the ShowupSquared system.

This module provides functions for file operations, including reading, writing,
archiving, and managing file paths.
"""

import os
import shutil
import json
import logging
import datetime
from typing import Tuple, Dict, Any, Optional, List
from showup_editor_ui.claude_panel.path_utils import get_project_root
from .config import DIRS, AVAILABLE_COURSES

# Configure logging
logger = logging.getLogger("file_utils")

def resolve_template_path(template_name, category=None):
    """
    Resolve a template name to its path using TemplateManager.
    
    Args:
        template_name: The template name or identifier
        category: Optional category to search in first
        
    Returns:
        The full path to the resolved template
    """
    from .prompt_manager import TemplateManager
    template_manager = TemplateManager()
    return template_manager.resolve_template_path(template_name, category)

# Configure logging
logger = logging.getLogger("file_utils")

def ensure_directory_exists(directory_path: str) -> None:
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to the directory to ensure exists
    """
    if not os.path.exists(directory_path):
        os.makedirs(directory_path, exist_ok=True)
        logger.info(f"Created directory: {directory_path}")

# Add alias for backward compatibility
ensure_directory = ensure_directory_exists

def safe_read_file(file_path: str, encodings: List[str] = None) -> Tuple[bool, str]:
    """
    Safely read a file, handling potential errors and trying multiple encodings.
    
    Args:
        file_path: Path to the file to read
        encodings: List of encodings to try (defaults to ['utf-8', 'latin1', 'cp1252'])
        
    Returns:
        A tuple of (success, content), where success is a boolean and
        content is either the file content or an error message.
    """
    if encodings is None:
        encodings = ['utf-8', 'latin1', 'cp1252']
        
    try:
        if not os.path.exists(file_path):
            return False, f"File does not exist: {file_path}"
            
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    content = file.read()
                logger.debug(f"Successfully read file {file_path} with encoding {encoding}")
                return True, content
            except UnicodeDecodeError:
                logger.debug(f"Failed to read file {file_path} with encoding {encoding}, trying next encoding")
                continue
                
        # If we get here, none of the encodings worked
        return False, f"Error reading file {file_path}: Unable to decode with any of the specified encodings"
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return False, f"Error reading file: {str(e)}"

def safe_write_file(file_path: str, content: str, encoding: str = 'utf-8') -> Tuple[bool, str]:
    """
    Safely write content to a file, handling potential errors.
    
    Args:
        file_path: Path to the file to write
        content: Content to write to the file
        encoding: Encoding to use (default: utf-8)
        
    Returns:
        A tuple of (success, message), where success is a boolean and
        message is either a success message or an error message.
    """
    try:
        # Ensure directory exists
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        with open(file_path, 'w', encoding=encoding) as file:
            file.write(content)
        return True, f"Successfully wrote to {file_path}"
    except Exception as e:
        logger.error(f"Error writing to file {file_path}: {str(e)}")
        return False, f"Error writing to file: {str(e)}"


def create_timestamped_backup(file_path: str, backup_dir: Optional[str] | None = None) -> Optional[str]:
    """Create a timestamped backup of *file_path*.

    The backup file name uses the pattern ``<file>.bak.<timestamp>``. If a file
    with that name already exists, an incremental suffix (``_1``, ``_2`` ...) is
    appended to ensure uniqueness.

    Args:
        file_path: Path to the file to back up.
        backup_dir: Directory where the backup will be placed. Defaults to the
            file's own directory.

    Returns:
        The full path to the created backup, or ``None`` if creation fails.
    """

    try:
        if not os.path.exists(file_path):
            return None

        if backup_dir is None:
            backup_dir = os.path.dirname(file_path)

        ensure_directory_exists(backup_dir)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{os.path.basename(file_path)}.bak.{timestamp}"
        backup_path = os.path.join(backup_dir, base_name)
        counter = 1
        while os.path.exists(backup_path):
            backup_path = os.path.join(backup_dir, f"{base_name}_{counter}")
            counter += 1

        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
        return backup_path
    except Exception as e:
        logger.warning(f"Could not create backup: {str(e)}")
        return None

def fix_file_encoding(file_path: str, from_encodings: List[str] = None, to_encoding: str = 'utf-8') -> Tuple[bool, str]:
    """
    Fix encoding issues in an existing file by reading with one encoding and writing with another.
    
    Args:
        file_path: Path to the file to fix
        from_encodings: List of encodings to try for reading (defaults to ['latin1', 'cp1252'])
        to_encoding: Encoding to use for writing (default: utf-8)
        
    Returns:
        A tuple of (success, message), where success is a boolean and
        message provides additional information.
    """
    if from_encodings is None:
        from_encodings = ['latin1', 'cp1252', 'iso-8859-1']
        
    try:
        if not os.path.exists(file_path):
            return False, f"File does not exist: {file_path}"
        
        # First try to read with each encoding
        content = None
        encoding_used = None
        
        for encoding in from_encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    encoding_used = encoding
                    logger.info(f"Successfully read file {file_path} with encoding {encoding}")
                    break
            except UnicodeDecodeError:
                logger.debug(f"Failed to read file {file_path} with encoding {encoding}")
                continue
        
        if content is None:
            return False, f"Unable to read file {file_path} with any of the specified encodings"
        
        # Create a backup before modifying
        create_timestamped_backup(file_path)
        
        # Write with the target encoding
        with open(file_path, 'w', encoding=to_encoding) as f:
            f.write(content)
            
        return True, f"Successfully fixed encoding of {file_path} (from {encoding_used} to {to_encoding})"
    except Exception as e:
        logger.error(f"Error fixing encoding of {file_path}: {str(e)}")
        return False, f"Error fixing encoding: {str(e)}"

def archive_file(file_path: str, archive_dir: Optional[str] = None) -> Tuple[bool, str]:
    """
    Archive a file by copying it to an archive directory with a timestamp.
    
    Args:
        file_path: Path to the file to archive
        archive_dir: Optional custom archive directory. If not provided,
                    a default archive directory is used.
                    
    Returns:
        A tuple of (success, message), where success is a boolean and
        message is either a success message or an error message.
    """
    try:
        if not os.path.exists(file_path):
            return False, f"File does not exist: {file_path}"
            
        # Determine archive directory
        if archive_dir is None:
            # Get the base directory (usually the project root)
            base_dir = str(get_project_root())
            
            # Default archive directory is data/archive
            archive_dir = os.path.join(base_dir, "data", "archive")
        
        # Ensure archive directory exists
        ensure_directory_exists(archive_dir)
        
        # Get relative path components
        file_name = os.path.basename(file_path)
        
        # Get parent directories to preserve structure
        rel_path = os.path.dirname(file_path)
        base_dir = str(get_project_root())
        if base_dir in rel_path:
            rel_path = os.path.relpath(rel_path, base_dir)
        
        # Create archive path, preserving directory structure
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Split filename to insert timestamp before extension
        name_parts = os.path.splitext(file_name)
        archived_filename = f"{name_parts[0]}_{timestamp}{name_parts[1]}"
        
        # Create full archive path preserving structure
        archive_path = os.path.join(archive_dir, rel_path, archived_filename)
        
        # Ensure archive subdirectory exists
        archive_subdir = os.path.dirname(archive_path)
        ensure_directory_exists(archive_subdir)
        
        # Copy the file to archive
        shutil.copy2(file_path, archive_path)
        
        return True, f"Archived {file_path} to {archive_path}"
    except Exception as e:
        logger.error(f"Error archiving file {file_path}: {str(e)}")
        return False, f"Error archiving file: {str(e)}"

def load_json_file(file_path: str, default_value: Optional[Dict] = None) -> Dict:
    """
    Load JSON data from a file, with a default value if the file doesn't exist.
    
    Args:
        file_path: Path to the JSON file
        default_value: Default value to return if the file doesn't exist or can't be read
        
    Returns:
        Parsed JSON data as a dictionary, or the default value
    """
    if default_value is None:
        default_value = {}
        
    try:
        if not os.path.exists(file_path):
            return default_value
            
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
    except Exception as e:
        logger.error(f"Error loading JSON from {file_path}: {str(e)}")
        return default_value

def save_json_file(file_path: str, data: Dict) -> Tuple[bool, str]:
    """
    Save data as JSON to a file.
    
    Args:
        file_path: Path to the JSON file
        data: Data to save as JSON
        
    Returns:
        A tuple of (success, message), where success is a boolean and
        message is either a success message or an error message.
    """
    try:
        # Ensure directory exists
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2)
        return True, f"Successfully saved JSON to {file_path}"
    except Exception as e:
        logger.error(f"Error saving JSON to {file_path}: {str(e)}")
        return False, f"Error saving JSON to file: {str(e)}"

def get_state_file_path(course_id: str) -> str:
    """
    Get the path to the state file for a course.
    
    Args:
        course_id: ID of the course
        
    Returns:
        Path to the state file
    """
    # Get the base directory (usually the project root)
    base_dir = str(get_project_root())
    
    # State files are stored in data/settings
    state_dir = os.path.join(base_dir, "data", "settings")
    ensure_directory_exists(state_dir)
    
    return os.path.join(state_dir, f"{course_id}_state.json")

def load_work_state(course_id: str) -> Dict:
    """
    Load the work state for a course.
    
    Args:
        course_id: ID of the course
        
    Returns:
        Work state as a dictionary
    """
    state_path = get_state_file_path(course_id)
    
    # Default state structure
    default_state = {
        "course_id": course_id,
        "last_updated": datetime.datetime.now().isoformat(),
        "modules": {}
    }
    
    return load_json_file(state_path, default_state)

def save_work_state(course_id: str, state: Dict) -> Tuple[bool, str]:
    """
    Save the work state for a course.
    
    Args:
        course_id: ID of the course
        state: Work state to save
        
    Returns:
        A tuple of (success, message), where success is a boolean and
        message is either a success message or an error message.
    """
    state_path = get_state_file_path(course_id)
    
    # Update last_updated timestamp
    state["last_updated"] = datetime.datetime.now().isoformat()
    
    return save_json_file(state_path, state)

def is_work_needed(existing_state: Dict, new_parameters: Dict) -> Tuple[bool, str]:
    """
    Determine if work needs to be redone based on state and parameters.
    
    Args:
        existing_state: Existing work state
        new_parameters: New parameters for the work
        
    Returns:
        A tuple of (needs_work, reason), where needs_work is a boolean and
        reason is a string explaining why work is needed or not.
    """
    # If no existing state, work is definitely needed
    if not existing_state:
        return True, "No existing work found"
        
    # Check if CSV file changed
    if existing_state.get("csv_file") != new_parameters.get("csv_file"):
        return True, "CSV file has changed"
        
    # Check if learner profile changed
    if existing_state.get("learner_profile") != new_parameters.get("learner_profile"):
        return True, "Learner profile has changed"
        
    # Check if model changed
    if existing_state.get("model_used") != new_parameters.get("model"):
        return True, "Different model selected"
        
    # Check if prompt engineering level changed
    if existing_state.get("prompt_engineering_level") != new_parameters.get("prompt_engineering_level"):
        return True, "Prompt engineering level has changed"
        
    # If existing output files are missing, regeneration is needed
    if "output_paths" in existing_state:
        for output_type, path in existing_state["output_paths"].items():
            if not os.path.exists(path):
                return True, f"Output file is missing: {path}"
    
    # If no reason to regenerate was found, work is not needed
    return False, "No changes detected, existing work can be reused"

def validate_csv_basics(file_path: str) -> Tuple[bool, str]:
    """
    Validate that a CSV file exists and has basic expected structure.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        A tuple of (is_valid, message), where is_valid is a boolean and
        message explains any issues found.
    """
    try:
        if not os.path.exists(file_path):
            return False, f"CSV file does not exist: {file_path}"
            
        # Check file extension
        if not file_path.lower().endswith('.csv'):
            return False, f"File does not have .csv extension: {file_path}"
            
        # Basic check: try to open and read a few lines
        with open(file_path, 'r', encoding='utf-8') as file:
            # Try to read first few lines
            header = file.readline().strip()
            if not header:
                return False, "CSV file appears to be empty"
                
            # Check for comma separation (basic check)
            if ',' not in header:
                return False, "CSV header does not contain commas, may not be a valid CSV"
                
            # Try to read a few data rows
            data_lines = [file.readline() for _ in range(3)]
            valid_lines = [line for line in data_lines if line.strip() and ',' in line]
            
            if not valid_lines and data_lines:
                return False, "CSV appears to have header but no valid data rows"
                
        return True, "CSV appears to be valid"
    except Exception as e:
        return False, f"Error validating CSV: {str(e)}"

def list_files(directory_path: str, pattern: str = "*", recursive: bool = False) -> List[str]:
    """
    List files in a directory matching a pattern.
    
    Args:
        directory_path: Path to the directory to list files from
        pattern: Optional file pattern to match (e.g., "*.csv", "*.md")
        recursive: Whether to recursively list files in subdirectories
        
    Returns:
        A list of file paths matching the pattern
    """
    import glob
    import os
    
    if not os.path.exists(directory_path):
        logger.warning(f"Directory does not exist: {directory_path}")
        return []
        
    # Construct the pattern
    if recursive:
        search_pattern = os.path.join(directory_path, "**", pattern)
    else:
        search_pattern = os.path.join(directory_path, pattern)
        
    # Use glob to find matching files
    files = glob.glob(search_pattern, recursive=recursive)
    
    # Filter out directories
    files = [f for f in files if os.path.isfile(f)]
    
    return files

def copy_file(source_path: str, dest_path: str, create_dirs: bool = True) -> Tuple[bool, str]:
    """
    Copy a file from source to destination path.
    
    Args:
        source_path: Path to the source file
        dest_path: Path to the destination file
        create_dirs: Whether to create any missing directories in the destination path
        
    Returns:
        A tuple of (success, message), where success is a boolean and
        message provides additional information.
    """
    try:
        # Check if source file exists
        if not os.path.exists(source_path):
            return False, f"Source file does not exist: {source_path}"
            
        # Ensure the destination directory exists if needed
        if create_dirs:
            dest_dir = os.path.dirname(dest_path)
            if dest_dir and not os.path.exists(dest_dir):
                os.makedirs(dest_dir, exist_ok=True)
                
        # Copy the file
        shutil.copy2(source_path, dest_path)
        
        return True, f"Successfully copied file from {source_path} to {dest_path}"
    except Exception as e:
        logger.error(f"Error copying file from {source_path} to {dest_path}: {str(e)}")
        return False, f"Error copying file: {str(e)}"

def read_json_file(file_path: str, default_value: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Read and parse a JSON file.
    
    Args:
        file_path: Path to the JSON file to read
        default_value: Default value to return if file doesn't exist or error occurs
            
    Returns:
        The parsed JSON content as a dictionary
    """
    return load_json_file(file_path, default_value)

def write_json_file(file_path: str, data: Dict) -> Tuple[bool, str]:
    """
    Write a dictionary to a JSON file.
    
    Args:
        file_path: Path to the JSON file to write
        data: Dictionary data to write as JSON
            
    Returns:
        A tuple of (success, message)
    """
    return save_json_file(file_path, data)

def file_exists(file_path: str) -> bool:
    """
    Check if a file exists.
    
    Args:
        file_path: Path to the file to check
            
    Returns:
        True if the file exists, False otherwise
    """
    return os.path.isfile(file_path)

def directory_exists(directory_path: str) -> bool:
    """
    Check if a directory exists.
    
    Args:
        directory_path: Path to the directory to check
            
    Returns:
        True if the directory exists, False otherwise
    """
    return os.path.isdir(directory_path)

def get_course_directory(course_id: str) -> str:
    """
    Get the directory for a specific course.
    
    Args:
        course_id: Course identifier
        
    Returns:
        Path to the course directory
    """
    if course_id not in AVAILABLE_COURSES:
        raise ValueError(f"Unknown course ID: {course_id}")
    
    course_name = AVAILABLE_COURSES[course_id]["name"]
    course_dir = os.path.join(DIRS['library']['root'], course_name)
    
    # Create directory if it doesn't exist
    os.makedirs(course_dir, exist_ok=True)
    
    return course_dir

def check_course_content_exists(course_id: str, module_id: str = None) -> Tuple[bool, str]:
    """
    Check if content exists for a specific course and optionally a module.
    
    Args:
        course_id: ID of the course
        module_id: Optional module ID to check
        
    Returns:
        A tuple of (exists, message), where exists is a boolean and
        message provides additional information.
    """
    try:
        # Get the base directory (usually the project root)
        base_dir = str(get_project_root())
        
        # Determine course directory
        course_dir = os.path.join(base_dir, "library", course_id)
        
        if not os.path.exists(course_dir):
            return False, f"Course directory does not exist: {course_dir}"
            
        # If module specified, check that directory
        if module_id:
            module_dir = os.path.join(course_dir, f"Module_{module_id}")
            if not os.path.exists(module_dir):
                return False, f"Module directory does not exist: {module_dir}"
            
            # Check if there are any content files in the module
            content_files = [f for f in os.listdir(module_dir) 
                          if os.path.isfile(os.path.join(module_dir, f)) and 
                          f.lower().endswith(('.md', '.html', '.txt'))]
            
            if not content_files:
                return False, f"No content files found in module: {module_dir}"
                
            return True, f"Found {len(content_files)} content files in module {module_id}"
            
        # Check for course-level content
        module_dirs = [d for d in os.listdir(course_dir) 
                     if os.path.isdir(os.path.join(course_dir, d)) and 
                     d.lower().startswith('module_')]
        
        if not module_dirs:
            return False, f"No module directories found in course: {course_dir}"
            
        return True, f"Found {len(module_dirs)} modules in course {course_id}"
    except Exception as e:
        return False, f"Error checking course content: {str(e)}"