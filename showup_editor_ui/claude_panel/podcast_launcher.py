#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Podcast Launcher - A simple module to launch the original podcast generator
from within the modular editor without modification.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import logging
from .path_utils import get_project_root

# Get logger
logger = logging.getLogger("podcast_launcher")


class PodcastLauncherPanel(ttk.Frame):
    """Simple panel to launch the original podcast generator"""
    
    def __init__(self, parent, main_panel):
        ttk.Frame.__init__(self, parent, padding="10")
        self.parent = parent
        self.main_panel = main_panel
        
        # Create UI
        self._create_ui()
    
    def _create_ui(self):
        """Create the launcher UI"""
        # Header
        header = ttk.Label(self, text="Podcast & Voiceover Generators", font=("Arial", 16, "bold"))
        header.pack(pady=(0, 20))
        
        # Description
        description = ttk.Label(self, text=(
            "Launch audio generators to create content from selected files.\n"
            "The audio generators provide workflows to convert content into\n"
            "professionally narrated episodes with natural-sounding voices."
        ), justify="center")
        description.pack(pady=(0, 30))
        
        # Create generators frame for the buttons
        generators_frame = ttk.LabelFrame(self, text="Available Generators")
        generators_frame.pack(fill="x", padx=10, pady=10)
        
        # Create inner frame for the two buttons
        button_inner_frame = ttk.Frame(generators_frame)
        button_inner_frame.pack(fill="x", padx=10, pady=10)
        
        # Podcast Generator button
        podcast_button = ttk.Button(
            button_inner_frame, 
            text="Launch Podcast Generator", 
            command=self._launch_podcast_generator,
            style="Accent.TButton"
        )
        podcast_button.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        
        # Fitness Instructor Voiceover button
        fitness_button = ttk.Button(
            button_inner_frame, 
            text="Launch Fitness Instructor Voiceover", 
            command=self._launch_fitness_instructor_voiceover,
            style="Accent.TButton"
        )
        fitness_button.pack(side="right", padx=10, pady=10, expand=True, fill="x")
        
        # File selection frame
        file_frame = ttk.LabelFrame(self, text="Selected Files")
        file_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Selected files list
        selected_files_text = "No files selected"
        
        # Get selected files from the main panel
        try:
            selected_items = self.main_panel.file_tree.selection()
            if selected_items:
                files = []
                for item_id in selected_items:
                    # Get the item's values
                    item_values = self.main_panel.file_tree.item(item_id, "values")
                    if item_values and len(item_values) >= 2:
                        path = item_values[0]
                        item_type = item_values[1]
                        
                        # Only add files, not directories
                        if item_type.lower() == "file":
                            files.append(os.path.basename(path))
                
                if files:
                    selected_files_text = "\n".join(files)
        except Exception as e:
            logger.error(f"Error getting selected files: {str(e)}")
        
        self.selected_files = tk.Text(file_frame, height=10, width=60, wrap="word")
        self.selected_files.insert("1.0", selected_files_text)
        self.selected_files.config(state="disabled")
        self.selected_files.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Action buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", pady=20)
        
        refresh_btn = ttk.Button(button_frame, text="Refresh Selection", command=self._refresh_selection)
        refresh_btn.pack(side="left", padx=10)
        
        # Create accent style for the launch buttons
        style = ttk.Style()
        style.configure("Accent.TButton", font=("Arial", 10, "bold"))
    
    def _refresh_selection(self):
        """Refresh the list of selected files"""
        try:
            selected_items = self.main_panel.file_tree.selection()
            files = []
            
            if selected_items:
                for item_id in selected_items:
                    # Get the item's values
                    item_values = self.main_panel.file_tree.item(item_id, "values")
                    if item_values and len(item_values) >= 2:
                        path = item_values[0]
                        item_type = item_values[1]
                        
                        # Only add files, not directories
                        if item_type.lower() == "file":
                            files.append(os.path.basename(path))
            
            # Update the text widget
            self.selected_files.config(state="normal")
            self.selected_files.delete("1.0", tk.END)
            
            if files:
                self.selected_files.insert("1.0", "\n".join(files))
            else:
                self.selected_files.insert("1.0", "No files selected")
                
            self.selected_files.config(state="disabled")
            
        except Exception as e:
            logger.error(f"Error refreshing selected files: {str(e)}")
            messagebox.showerror("Error", f"Failed to refresh file selection: {str(e)}")
    
    def _launch_podcast_generator(self):
        """Launch the original podcast generator"""
        try:
            # Get the path to the podcast generator batch file
            base_dir = os.path.join(str(get_project_root()), "showup-editor-ui")
            batch_file = os.path.join(base_dir, "run_podcast_generator.bat")
            
            if not os.path.exists(batch_file):
                messagebox.showerror("Error", f"Podcast generator batch file not found: {batch_file}")
                return
            
            # Launch the batch file using subprocess
            subprocess.Popen([batch_file], cwd=base_dir, shell=True)
            
            # Show success message
            messagebox.showinfo("Success", "Podcast Generator launched successfully.")
            
        except Exception as e:
            logger.error(f"Error launching podcast generator: {str(e)}")
            messagebox.showerror("Error", f"Failed to launch podcast generator: {str(e)}")
    
    def _launch_fitness_instructor_voiceover(self):
        """Launch the fitness instructor voiceover generator"""
        try:
            # Get the path to the fitness instructor voiceover batch file
            base_dir = os.path.join(str(get_project_root()), "showup-editor-ui")
            batch_file = os.path.join(base_dir, "run_fitness_instructor_voiceover.bat")
            
            if not os.path.exists(batch_file):
                messagebox.showerror("Error", f"Fitness instructor voiceover batch file not found: {batch_file}")
                return
            
            # Launch the batch file using subprocess
            subprocess.Popen([batch_file], cwd=base_dir, shell=True)
            
            # Show success message
            messagebox.showinfo("Success", "Fitness Instructor Voiceover launched successfully.")
            
        except Exception as e:
            logger.error(f"Error launching fitness instructor voiceover: {str(e)}")
            messagebox.showerror("Error", f"Failed to launch fitness instructor voiceover: {str(e)}")


def setup_podcast_tab(podcast_tab: ttk.Frame, main_panel) -> ttk.Frame:
    """Setup the podcast launcher tab
    
    Args:
        podcast_tab: The frame to use for the podcast tab
        main_panel: The main ClaudeAIPanel instance
        
    Returns:
        The configured podcast tab frame
    """
    # Create the podcast launcher panel
    launcher_panel = PodcastLauncherPanel(podcast_tab, main_panel)
    launcher_panel.pack(fill="both", expand=True)
    
    return podcast_tab
