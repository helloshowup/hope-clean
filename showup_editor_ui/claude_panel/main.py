#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main entry point for the modular Output Library Editor application.
This module initializes the main application window and starts the GUI.
"""

import importlib.util
import logging
import os
import sys
import tkinter as tk
from tkinter import ttk

from .path_utils import get_project_root

# Add parent directory to path to allow importing from sibling modules
sys.path.append(os.path.join(str(get_project_root()), "showup-editor-ui"))


# Append showup_tools to sys.path if the package is not installed
if importlib.util.find_spec("showup_tools") is None:
    project_root = str(get_project_root())
    tools_path = os.path.join(project_root, "showup_tools")
    if tools_path not in sys.path:
        sys.path.insert(0, tools_path)

# Append showup-core to sys.path if the package is not installed
if importlib.util.find_spec("showup_core") is None:
    core_path = os.path.join(str(get_project_root()), "showup-core")
    if core_path not in sys.path:
        sys.path.insert(0, core_path)

# Import the main panel class
from claude_panel.main_panel import ClaudeAIPanel

# Configure logging
log_file = os.path.join(str(get_project_root()), 'showup-editor-ui', 'output_library_editor.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file)
    ]
)

# Get logger
logger = logging.getLogger("output_library_editor")

# Create important application directories
def ensure_app_directories():
    """Ensure all required application directories exist"""
    base_dir = os.path.join(str(get_project_root()), "showup-editor-ui")
    
    # Critical directories
    directories = [
        os.path.join(base_dir, "profiles"),
        os.path.join(base_dir, "cache"),
        os.path.join(base_dir, "output"),
        os.path.join(base_dir, "resources")
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                logger.info(f"Created directory: {directory}")
            except Exception as e:
                logger.error(f"Failed to create directory {directory}: {str(e)}")


def main():
    """
    Main function to initialize and run the application.
    """
    # Ensure all required directories exist
    ensure_app_directories()
    
    # Create the main window
    root = tk.Tk()
    root.title("Output Library Editor")
    root.geometry("1200x800")
    
    # Add app icon if available
    icon_path = os.path.join(str(get_project_root()), "showup-editor-ui", "resources", "app_icon.ico")
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)
    
    # Configure the style
    style = ttk.Style()
    style.theme_use('clam')  # Use a modern theme
    
    # Create and initialize the main application
    logger.info("Starting Output Library Editor GUI with enhanced context generation...")
    app = ClaudeAIPanel(root, root)
    app.pack(fill="both", expand=True)  # Make the panel visible in the window
    
    # Display welcome message
    welcome_text = """
MULTI-FILE EDITING:
* Select multiple files using Ctrl+click or Shift+click
* Use one custom prompt and learner profile for all selected files
* Process all files in a batch with progress tracking

ENHANCED CONTEXT GENERATION:
* Select previous context files in the "Previous Context" tab
* System analyzes previous files to prevent example repetition
* Content is enhanced with awareness of previously generated material
* Improves coherence and prevents redundancy across multiple files

CONTENT GENERATION:
* Generate supplementary content like glossaries, summaries, and quizzes
* Use custom prompts or select from templates
* Save generated content to specified directories
* Provides educational resources from existing lesson content
"""
    print(welcome_text)
    
    # Start the main event loop
    root.mainloop()


if __name__ == "__main__":
    main()
