#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Editor tab for the podcast generator application.

Integrates the modular Claude AI editor panel into the podcast generator.
"""

import os
import tkinter as tk
from tkinter import ttk
import logging
import json
from typing import List
from showup_editor_ui.claude_panel.path_utils import get_project_root

# Import for the modular editor panel
sys_path_addition = os.path.join(str(get_project_root()), "showup-editor-ui")

logger = logging.getLogger('podcast_generator')


class EditorTab:
    """Modular Editor Tab for advanced editing capabilities."""
    
    def __init__(self, parent: ttk.Frame, main_gui, extended_claude_panel_class):
        """Initialize the editor tab.
        
        Args:
            parent: The parent frame where this tab resides
            main_gui: Reference to the main GUI controller
            extended_claude_panel_class: The extended Claude AI panel class
        """
        self.parent = parent
        self.main_gui = main_gui
        self.frame = ttk.Frame(parent, padding="10")
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = ttk.Label(self.frame, text="Modular Editor", style="Header.TLabel")
        header.pack(fill=tk.X, pady=(0, 10))
        
        # Create a canvas with scrollbar for the editor panel
        canvas = tk.Canvas(self.frame)
        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Modular editor panel
        self.editor_panel = extended_claude_panel_class(scrollable_frame, main_gui.root)
        self.editor_panel.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure canvas scrolling
        canvas.bind('<Enter>', lambda e: canvas.bind_all("<MouseWheel>", 
                   lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units")))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all("<MouseWheel>"))
    
    def send_files(self, file_paths: List[str], target_learner: str):
        """Send selected files and target learner to the editor panel.
        
        Args:
            file_paths: List of file paths to send to the editor
            target_learner: Description of the target learner
        """
        if not file_paths:
            return
            
        # Read the contents of the selected files
        file_contents = ""
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                filename = os.path.basename(file_path)
                file_contents += f"\n\n### File: {filename} ###\n\n{content}"
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {str(e)}")
        
        if not file_contents:
            return

        # Load the custom prompt configuration (if it exists)
        prompt_config_path = os.path.join(
            str(get_project_root()),
            "showup-core",
            "data",
            "content_generation_config.json",
        )
        
        custom_prompt = ""
        try:
            if os.path.exists(prompt_config_path):
                with open(prompt_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Check if we have a system prompt
                if "system" in config:
                    # Use the custom system prompt from config
                    system_prompt = config["system"]
                    
                    # Format the actual content as a user message
                    content_msg = f"\n# Content to Enhance:\n\n{file_contents}\n\n"
                    
                    # If target learner is provided, add it to the prompt
                    if target_learner:
                        content_msg = f"Target Learner: {target_learner}\n" + content_msg
                    
                    # If the config has a model specified, set it in the editor panel if possible
                    if "model" in config and hasattr(self.editor_panel, "set_model"):
                        self.editor_panel.set_model(config["model"])
                    
                    # If the config has temperature specified, set it in the editor panel if possible
                    if "temperature" in config and hasattr(self.editor_panel, "set_temperature"):
                        self.editor_panel.set_temperature(config["temperature"])
                    
                    # Set the system prompt if the panel supports it
                    if hasattr(self.editor_panel, "set_system_prompt"):
                        self.editor_panel.set_system_prompt(system_prompt)
                        custom_prompt = content_msg
                    else:
                        # Fall back to combining system and user message if set_system_prompt is not available
                        custom_prompt = f"System: {system_prompt}\n\nUser: {content_msg}"
                else:
                    # No system prompt in config, fall back to basic prompt
                    custom_prompt = f"I'm creating educational content for {target_learner}. Here are materials:\n\n{file_contents}\n\nPlease help analyze and enhance this content."
            else:
                # No config file, fall back to basic prompt
                custom_prompt = f"I'm creating educational content for {target_learner}. Here are materials:\n\n{file_contents}\n\nPlease help analyze and enhance this content."
        except Exception as e:
            logger.error(f"Error loading prompt config: {str(e)}")
            # Fall back to basic prompt
            custom_prompt = f"I'm creating educational content for {target_learner}. Here are materials:\n\n{file_contents}\n\nPlease help analyze and enhance this content."
        
        # Send to editor panel
        self.editor_panel.set_text(custom_prompt)
        logger.info(f"Sent {len(file_paths)} files to modular editor")
