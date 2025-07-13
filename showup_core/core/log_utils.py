"""
Logging Utilities for ShowupSquared System.

This module provides standardized logging utilities for the ShowupSquared system,
ensuring that all log files are created in a consistent, well-structured location.

Usage:
    from showup_core.core.log_utils import get_log_path
    
    # Get a log path for a specific module
    log_file = get_log_path('batch_processor')
    
    # Use with Python's logging module
    handler = logging.FileHandler(log_file)
    logger.addHandler(handler)
    
    # Or use directly with open()
    with open(log_file, 'w') as f:
        f.write('Log entry')
"""

import os
import logging


def get_log_path(module_name: str) -> str:
    """
    Get a standardized log file path for a specific module.
    
    This function ensures all logs are stored in a consistent location
    under the central data/logs directory. It automatically creates
    any necessary subdirectories.
    
    Args:
        module_name: Name of the module (e.g., 'batch_processor', 'claude_panel')
                    This will be used both for the subdirectory and the log filename.
    
    Returns:
        str: A string path pointing to the log file location
    
    Example:
        log_path = get_log_path('batch_processor')
        # Returns: C:/Users/User/Documents/showup-v4/showup-data/logs/batch_processor/batch_processor.log
    """
    # Define the root log directory explicitly
    log_root = "C:/Users/User/Documents/showup-v4/showup-data/logs"
    
    # Create the complete path
    module_dir = os.path.join(log_root, module_name)
    log_file = os.path.join(module_dir, f"{module_name}.log")
    
    # Create the directory if it doesn't exist
    os.makedirs(module_dir, exist_ok=True)
    
    # Return the full path to the log file as a string
    return log_file


def get_specialized_log_path(module_name: str, log_name: str) -> str:
    """
    Get a specialized log file path for a specific module and log name.
    
    Similar to get_log_path, but allows specifying a different filename
    than the module name for cases where a module needs multiple log files.
    
    Args:
        module_name: Name of the module (for the subdirectory)
        log_name: Name of the log file (without extension)
    
    Returns:
        str: A string path pointing to the log file location
    
    Example:
        log_path = get_specialized_log_path('batch_processor', 'error_log')
        # Returns: C:/Users/User/Documents/showup-v4/showup-data/logs/batch_processor/error_log.log
    """
    # Define the root log directory explicitly
    log_root = "C:/Users/User/Documents/showup-v4/showup-data/logs"
    
    # Create the complete path
    module_dir = os.path.join(log_root, module_name)
    log_file = os.path.join(module_dir, f"{log_name}.log")
    
    # Create the directory if it doesn't exist
    os.makedirs(module_dir, exist_ok=True)
    
    # Return the full path to the log file as a string
    return log_file


def configure_file_logger(logger_name: str, module_name: str = None, 
                         log_name: str = None, level=None) -> None:
    """
    Configure a logger with a file handler using the standardized log path.
    
    This is a convenience function that sets up a logger with a file handler
    pointing to the standardized log location.
    
    Args:
        logger_name: Name of the logger to configure
        module_name: Name of the module (defaults to first part of logger_name)
        log_name: Name of the log file (defaults to module_name)
        level: Logging level (defaults to INFO)
    
    Example:
        configure_file_logger('batch_processor.manager')
        # Sets up a logger that writes to data/logs/batch_processor/batch_processor.log
    """
    # Default to INFO level if not specified
    if level is None:
        level = logging.INFO
        
    # If module_name not provided, use the first part of the logger_name
    if module_name is None:
        module_name = logger_name.split('.')[0]
        
    # If log_name not provided, use the module_name
    if log_name is None:
        log_name = module_name
        
    # Get the logger
    logger = logging.getLogger(logger_name)
    
    # Don't add handlers if they already exist
    if logger.handlers:
        return
        
    # Set the level
    logger.setLevel(level)
    
    # Get the log path
    log_path = get_specialized_log_path(module_name, log_name)
    
    # Create a file handler - log_path is now a string, no need to convert
    handler = logging.FileHandler(log_path)
    
    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(handler)
