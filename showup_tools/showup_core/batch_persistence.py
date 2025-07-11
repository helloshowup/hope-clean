"""
Batch Persistence Module for ShowupSquaredV4.

This module provides persistence capabilities for batch processing,
allowing the application to recover from restarts and continue processing batches.
"""

import os
import json
import glob
import logging
import datetime
import hashlib
from typing import Dict, List, Any, Optional

# Set up logger
logger = logging.getLogger("batch_persistence")

# Constants
BATCH_STATE_DIR = "data/batch_state"
BATCH_RESULTS_DIR = "data/batch_results"

def ensure_directories():
    """Ensure that the necessary directories exist."""
    os.makedirs(BATCH_STATE_DIR, exist_ok=True)
    os.makedirs(BATCH_RESULTS_DIR, exist_ok=True)
    logger.info(f"Ensured batch persistence directories exist: {BATCH_STATE_DIR}, {BATCH_RESULTS_DIR}")

def hash_row_data(row_data: Dict[str, Any]) -> str:
    """
    Create a hash of row data to uniquely identify it.
    
    Args:
        row_data: Dictionary containing row data
        
    Returns:
        String hash of the row data
    """
    # Convert row data to a stable string representation
    row_str = json.dumps(row_data, sort_keys=True)
    # Create a hash of the string
    return hashlib.md5(row_str.encode('utf-8')).hexdigest()

def save_batch_state(batch_id: str, row_data_list: List[Dict[str, Any]], 
                    selected_modules: Optional[List[str]] = None, 
                    selected_lessons: Optional[List[str]] = None,
                    csv_path: Optional[str] = None) -> str:
    """
    Save batch state to disk for potential recovery.
    
    Args:
        batch_id: ID of the batch
        row_data_list: List of row data dictionaries
        selected_modules: List of selected module names (optional)
        selected_lessons: List of selected lesson names (optional)
        csv_path: Path to the CSV file (optional)
        
    Returns:
        Path to the saved state file
    """
    ensure_directories()
    
    # Create state object
    state = {
        "batch_id": batch_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "row_count": len(row_data_list),
        "selected_modules": selected_modules,
        "selected_lessons": selected_lessons,
        "csv_path": csv_path,
        "row_data_hashes": [hash_row_data(row) for row in row_data_list],
        # Store a simplified version of row data for recovery
        "row_data_simple": [{
            "Module": row.get("Module", ""),
            "Lesson": row.get("Lesson", ""),
            "Step Number": row.get("Step Number", ""),
            "Step Title": row.get("Step Title", "")
        } for row in row_data_list]
    }
    
    # Save to a JSON file
    state_file = os.path.join(BATCH_STATE_DIR, f"batch_{batch_id}.json")
    
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)
    
    logger.info(f"Saved batch state for batch {batch_id} with {len(row_data_list)} rows to {state_file}")
    return state_file

def load_batch_state(batch_id: str) -> Optional[Dict[str, Any]]:
    """
    Load batch state from disk.
    
    Args:
        batch_id: ID of the batch
        
    Returns:
        Dictionary containing batch state, or None if not found
    """
    ensure_directories()
    
    # Check if state file exists
    state_file = os.path.join(BATCH_STATE_DIR, f"batch_{batch_id}.json")
    if not os.path.exists(state_file):
        logger.warning(f"No state file found for batch {batch_id}")
        return None
    
    try:
        # Load state from file
        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)
        
        logger.info(f"Loaded batch state for batch {batch_id} with {state.get('row_count', 0)} rows from {state_file}")
        return state
    except Exception as e:
        logger.error(f"Error loading batch state for batch {batch_id}: {str(e)}")
        return None

def find_batch_results(batch_id: str) -> List[str]:
    """
    Find all result files for a batch.
    
    Args:
        batch_id: ID of the batch
        
    Returns:
        List of paths to result files
    """
    # Look for batch results files in logs directory
    result_files = glob.glob(f"logs/batch_results_{batch_id}_*.txt")
    
    if result_files:
        logger.info(f"Found {len(result_files)} existing result files for batch {batch_id}")
    else:
        logger.warning(f"No result files found for batch {batch_id}")
    
    return result_files

def cache_batch_results(batch_id: str, custom_id: str, content: str) -> str:
    """
    Cache batch results for a specific request.
    
    Args:
        batch_id: ID of the batch
        custom_id: Custom ID of the request
        content: Content to cache
        
    Returns:
        Path to the cached result file
    """
    ensure_directories()
    
    # Create a unique filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = os.path.join(BATCH_RESULTS_DIR, f"result_{batch_id}_{custom_id}_{timestamp}.txt")
    
    # Save content to file
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"Cached result for batch {batch_id}, request {custom_id} to {result_file}")
    return result_file

def load_cached_results(batch_id: str) -> Dict[str, str]:
    """
    Load all cached results for a batch.
    
    Args:
        batch_id: ID of the batch
        
    Returns:
        Dictionary mapping custom IDs to content
    """
    ensure_directories()
    
    # Look for cached result files
    result_files = glob.glob(os.path.join(BATCH_RESULTS_DIR, f"result_{batch_id}_*.txt"))
    
    if not result_files:
        logger.warning(f"No cached results found for batch {batch_id}")
        return {}
    
    # Load results from files
    results = {}
    for file in result_files:
        try:
            # Extract custom ID from filename
            filename = os.path.basename(file)
            parts = filename.split('_')
            if len(parts) >= 3:
                custom_id = parts[2]
                
                # Load content from file
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                results[custom_id] = content
                logger.debug(f"Loaded cached result for batch {batch_id}, request {custom_id} from {file}")
        except Exception as e:
            logger.error(f"Error loading cached result from {file}: {str(e)}")
    
    logger.info(f"Loaded {len(results)} cached results for batch {batch_id}")
    return results

def extract_results_from_log(result_file: str) -> Dict[str, str]:
    """
    Extract results from a batch results log file.
    
    Args:
        result_file: Path to the batch results log file
        
    Returns:
        Dictionary mapping custom IDs to content
    """
    results = {}
    
    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if the file has the expected format
        if "=== INDIVIDUAL RESULTS ===" in content:
            # Split the file into individual results
            individual_results = content.split("--- RESULT ")[1:]  # Skip the first part
            
            for result_text in individual_results:
                try:
                    # Extract custom ID
                    id_start = result_text.find("(ID: ") + 5
                    id_end = result_text.find(")", id_start)
                    if id_start >= 5 and id_end > id_start:
                        custom_id = result_text[id_start:id_end]
                        
                        # Extract content
                        if "CONTENT:" in result_text:
                            content_start = result_text.find("CONTENT:") + 8
                            content_end = result_text.find("\n---", content_start)
                            if content_end == -1:  # If this is the last result
                                content_end = len(result_text)
                            
                            if content_start >= 8 and content_end > content_start:
                                content = result_text[content_start:content_end].strip()
                                results[custom_id] = content
                                logger.debug(f"Extracted result for request {custom_id} from {result_file}")
                except Exception as e:
                    logger.error(f"Error extracting individual result from {result_file}: {str(e)}")
        else:
            # Try parsing as JSONL
            for line in content.strip().split("\n"):
                try:
                    result = json.loads(line)
                    if "custom_id" in result and "result" in result and result["result"]["type"] == "succeeded":
                        custom_id = result["custom_id"]
                        message = result["result"]["message"]
                        if "content" in message and message["content"] and "text" in message["content"][0]:
                            content = message["content"][0]["text"]
                            results[custom_id] = content
                            logger.debug(f"Extracted result for request {custom_id} from {result_file} (JSONL format)")
                except json.JSONDecodeError:
                    pass  # Skip lines that aren't valid JSON
                except Exception as e:
                    logger.error(f"Error parsing JSONL line in {result_file}: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing batch results file {result_file}: {str(e)}")
    
    logger.info(f"Extracted {len(results)} results from {result_file}")
    return results

def process_existing_results(batch_id: str) -> Dict[str, str]:
    """
    Process existing results for a batch.
    
    Args:
        batch_id: ID of the batch
        
    Returns:
        Dictionary mapping custom IDs to content
    """
    # First check for cached results
    results = load_cached_results(batch_id)
    
    # If we don't have cached results, try extracting from log files
    if not results:
        result_files = find_batch_results(batch_id)
        
        for file in result_files:
            file_results = extract_results_from_log(file)
            results.update(file_results)
    
    logger.info(f"Processed a total of {len(results)} existing results for batch {batch_id}")
    return results

def clean_up_old_state_files(max_age_days: int = 7):
    """
    Clean up old state files.
    
    Args:
        max_age_days: Maximum age of files to keep in days
    """
    ensure_directories()
    
    # Get current time
    now = datetime.datetime.now()
    
    # Get all state files
    state_files = glob.glob(os.path.join(BATCH_STATE_DIR, "batch_*.json"))
    
    # Check each file
    for file in state_files:
        try:
            # Get file modification time
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file))
            
            # Check if file is older than max_age_days
            if (now - mtime).days > max_age_days:
                # Delete the file
                os.remove(file)
                logger.info(f"Deleted old state file: {file}")
        except Exception as e:
            logger.error(f"Error cleaning up state file {file}: {str(e)}")

def clean_up_old_result_files(max_age_days: int = 7):
    """
    Clean up old result files.
    
    Args:
        max_age_days: Maximum age of files to keep in days
    """
    ensure_directories()
    
    # Get current time
    now = datetime.datetime.now()
    
    # Get all result files
    result_files = glob.glob(os.path.join(BATCH_RESULTS_DIR, "result_*.txt"))
    
    # Check each file
    for file in result_files:
        try:
            # Get file modification time
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file))
            
            # Check if file is older than max_age_days
            if (now - mtime).days > max_age_days:
                # Delete the file
                os.remove(file)
                logger.info(f"Deleted old result file: {file}")
        except Exception as e:
            logger.error(f"Error cleaning up result file {file}: {str(e)}")

def find_batch_for_modules_lessons(selected_modules: Optional[List[str]] = None, 
                                 selected_lessons: Optional[List[str]] = None,
                                 csv_path: Optional[str] = None) -> Optional[str]:
    """
    Find a batch that matches the given modules and lessons.
    
    Args:
        selected_modules: List of selected module names (optional)
        selected_lessons: List of selected lesson names (optional)
        csv_path: Path to the CSV file (optional)
        
    Returns:
        Batch ID if found, None otherwise
    """
    ensure_directories()
    
    # Get all state files
    state_files = glob.glob(os.path.join(BATCH_STATE_DIR, "batch_*.json"))
    
    # Check each file
    for file in state_files:
        try:
            # Load state from file
            with open(file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # Check if this state matches our criteria
            matches = True
            
            # Check selected modules
            if selected_modules is not None:
                state_modules = state.get("selected_modules", [])
                if state_modules is None:
                    state_modules = []
                
                # If the state has no selected modules, it means all modules were selected
                if state_modules and set(selected_modules) != set(state_modules):
                    matches = False
            
            # Check selected lessons
            if matches and selected_lessons is not None:
                state_lessons = state.get("selected_lessons", [])
                if state_lessons is None:
                    state_lessons = []
                
                # If the state has no selected lessons, it means all lessons were selected
                if state_lessons and set(selected_lessons) != set(state_lessons):
                    matches = False
            
            # Check CSV path
            if matches and csv_path is not None:
                state_csv_path = state.get("csv_path")
                if state_csv_path != csv_path:
                    matches = False
            
            # If all criteria match, return the batch ID
            if matches:
                batch_id = state.get("batch_id")
                if batch_id:
                    logger.info(f"Found matching batch {batch_id} for selected modules/lessons")
                    return batch_id
        except Exception as e:
            logger.error(f"Error checking state file {file}: {str(e)}")
    
    logger.info("No matching batch found for selected modules/lessons")
    return None