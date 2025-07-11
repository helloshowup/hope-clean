#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Extension for the Claude AI Panel to support integration with the Podcast Generator
"""

import os
import logging

logger = logging.getLogger("podcast_integration")

# Ensure the data directory exists
data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(data_dir, exist_ok=True)


def extend_claude_ai_panel(cls):
    """
    Extends the ClaudeAIPanel class with methods to support podcast integration
    
    Args:
        cls: The ClaudeAIPanel class to extend
    
    Returns:
        The extended ClaudeAIPanel class
    """
    
    # Store the original __init__ method
    original_init = cls.__init__
    
    # Define a new __init__ method
    def new_init(self, parent, main_app, *args, **kwargs):
        # Set a flag to indicate we're operating in podcast mode
        self.podcast_mode = True
        
        # Call the original __init__ method
        original_init(self, parent, main_app, *args, **kwargs)
        
        # Initialize additional attributes for podcast integration
        self.podcast_files = []
        logger.info("ClaudeAIPanel extended with podcast integration")
        
        # Setup tab visibility management
        self._setup_podcast_tab_visibility()
    
    # Define a method to handle tab visibility in podcast mode
    def _setup_podcast_tab_visibility(self):
        """Setup tab visibility for podcast mode"""
        try:
            if hasattr(self, 'tab_manager'):
                # Use a separate config file for podcast mode
                self.tab_manager.config_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), 
                    "data", 
                    "podcast_tab_visibility.json"
                )
                # Reload settings
                self.tab_manager._load_tab_visibility()
                self.tab_manager._apply_tab_visibility()
                
                # Initially show all tabs
                self.tab_manager._show_all_tabs()
                
                logger.info("Podcast tab visibility setup complete")
        except Exception as e:
            logger.error(f"Error setting up podcast tab visibility: {str(e)}")
    
    # Replace the __init__ method
    cls.__init__ = new_init
    
    # Add the new tab visibility method
    cls._setup_podcast_tab_visibility = _setup_podcast_tab_visibility
    
    # Add new methods to support podcast integration
    def _clear_selection(self):
        """
        Clear the current file selection
        """
        self.podcast_files = []
        logger.info("Cleared file selection in ClaudeAIPanel")
    
    def _add_file_to_selection(self, file_path: str):
        """
        Add a file to the selection
        
        Args:
            file_path: Path to the file to add
        """
        if os.path.exists(file_path):
            self.podcast_files.append(file_path)
            logger.info(f"Added file to selection: {file_path}")
            
            # If we have a file tree, try to select the file there
            if hasattr(self, 'file_tree') and self.file_tree is not None:
                try:
                    # Try to find and select the file in the file tree
                    # This depends on how the file tree is structured in the original class
                    # We'll make a best effort to find and select it
                    self._select_file_in_tree(file_path)
                except Exception as e:
                    logger.error(f"Error selecting file in tree: {str(e)}")
    
    def _select_file_in_tree(self, file_path: str):
        """
        Select a file in the file tree
        
        Args:
            file_path: Path to the file to select
        """
        # Implementation depends on the original file tree structure
        # If there's a refresh method, call it first
        if hasattr(self, '_refresh_library'):
            self._refresh_library()
        
        # Try to select the file in the tree
        # This is a placeholder implementation
        logger.info(f"Selecting file in tree: {file_path}")
    
    # Add the new methods to the class
    cls._clear_selection = _clear_selection
    cls._add_file_to_selection = _add_file_to_selection
    cls._select_file_in_tree = _select_file_in_tree
    
    return cls
