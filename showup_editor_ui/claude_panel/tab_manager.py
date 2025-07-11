"""Tab Manager Module for ClaudeAIPanel"""

import os
import json
import logging
import tkinter as tk
from tkinter import ttk
from typing import Dict, Set

# Get logger
logger = logging.getLogger("output_library_editor")

class TabManager:
    """Manages tab visibility in the ClaudeAIPanel interface."""
    
    def __init__(self, parent, notebook: ttk.Notebook):
        """
        Initialize the tab manager.
        
        Args:
            parent: The parent ClaudeAIPanel instance
            notebook: The ttk.Notebook instance containing the tabs
        """
        self.parent = parent
        self.notebook = notebook
        self.tab_vars: Dict[int, tk.BooleanVar] = {}
        self.tab_frames: Dict[int, ttk.Frame] = {}
        self.tab_names: Dict[int, str] = {}
        self.hidden_tabs: Set[int] = set()
        self.config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                      "data", "tab_visibility.json")
        
    def create_tab_manager_frame(self, container: ttk.Frame) -> ttk.Frame:
        """
        Create the tab manager frame with visibility checkboxes.
        
        Args:
            container: The container frame to hold the tab manager
            
        Returns:
            ttk.Frame: The created tab manager frame
        """
        # Create main frame
        tab_manager_frame = ttk.LabelFrame(container, text="Tab Visibility")
        
        # Create frame for checkboxes in a grid layout
        self.checkbox_frame = ttk.Frame(tab_manager_frame)
        self.checkbox_frame.pack(side="top", fill="both", expand=True, padx=5, pady=5)
        
        # Load saved visibility settings
        self._load_tab_visibility()
        
        # Populate the checkboxes
        self._populate_tab_checkboxes()
        
        # Apply initial visibility
        self._apply_tab_visibility()
        
        # Create restore defaults button
        button_frame = ttk.Frame(tab_manager_frame)
        button_frame.pack(side="bottom", fill="x", padx=5, pady=5)
        
        restore_btn = ttk.Button(
            button_frame, 
            text="Show All Tabs", 
            command=self._show_all_tabs
        )
        restore_btn.pack(side="right", padx=5, pady=5)
        
        # Store frame reference for potential refreshes
        self.tab_manager_frame = tab_manager_frame
        
        return tab_manager_frame
        
    def _populate_tab_checkboxes(self):
        """Populate the checkbox frame with tab visibility controls"""
        # Clear existing checkboxes if any
        for widget in self.checkbox_frame.winfo_children():
            widget.destroy()
            
        # Get current tab count
        tab_count = self.notebook.index("end")
        
        # Calculate grid layout (3 columns)
        columns = 3
        
        # Create checkbox for each tab
        for i, tab_id in enumerate(range(tab_count)):
            # Skip if the tab doesn't exist anymore
            if tab_id >= len(self.notebook.winfo_children()):
                continue
                
            tab_frame = self.notebook.winfo_children()[tab_id]
            tab_text = self.notebook.tab(tab_id, "text")
            self.tab_frames[tab_id] = tab_frame
            self.tab_names[tab_id] = tab_text
            
            # Create variable and set initial state if it doesn't exist
            if tab_id not in self.tab_vars:
                var = tk.BooleanVar(value=tab_id not in self.hidden_tabs)
                self.tab_vars[tab_id] = var
            
            # Calculate grid position
            row = i // columns
            col = i % columns
            
            # Create checkbox with tab name
            checkbox = ttk.Checkbutton(
                self.checkbox_frame, 
                text=tab_text,
                variable=self.tab_vars[tab_id],
                command=lambda t=tab_id: self._toggle_tab_visibility(t)
            )
            checkbox.grid(row=row, column=col, sticky="w", padx=10, pady=2)
    
    def refresh_tab_visibility(self):
        """Refresh the tab visibility controls to include any new tabs"""
        # Repopulate checkboxes
        self._populate_tab_checkboxes()
        
        # Apply visibility settings
        self._apply_tab_visibility()
        
        # Force update of the UI
        self.tab_manager_frame.update()
    
    def _toggle_tab_visibility(self, tab_id: int) -> None:
        """
        Toggle a tab's visibility based on its checkbox state.
        
        Args:
            tab_id: The ID of the tab to toggle
        """
        is_visible = self.tab_vars[tab_id].get()
        
        if is_visible and tab_id in self.hidden_tabs:
            # Show the tab
            self.hidden_tabs.remove(tab_id)
            self._apply_tab_visibility()
            logger.info(f"Showing tab: {self.tab_names[tab_id]}")
        elif not is_visible and tab_id not in self.hidden_tabs:
            # Hide the tab
            self.hidden_tabs.add(tab_id)
            self._apply_tab_visibility()
            logger.info(f"Hiding tab: {self.tab_names[tab_id]}")
        
        # Save the current visibility settings
        self._save_tab_visibility()
    
    def _apply_tab_visibility(self) -> None:
        """
        Apply the current visibility settings to the notebook.
        """
        # First, remove all tabs
        for tab_id in range(len(self.tab_frames)):
            try:
                self.notebook.forget(self.tab_frames[tab_id])
            except:
                # Tab might not be in the notebook
                pass
        
        # Then add back the visible ones in the correct order
        for tab_id in sorted([i for i in range(len(self.tab_frames)) if i not in self.hidden_tabs]):
            self.notebook.add(self.tab_frames[tab_id], text=self.tab_names[tab_id])
    
    def _show_all_tabs(self) -> None:
        """
        Show all tabs.
        """
        # Set all checkboxes to checked
        for tab_id, var in self.tab_vars.items():
            var.set(True)
        
        # Clear hidden tabs list
        self.hidden_tabs.clear()
        
        # Apply visibility
        self._apply_tab_visibility()
        
        # Save settings
        self._save_tab_visibility()
        
        logger.info("Showing all tabs")
    
    def _save_tab_visibility(self) -> None:
        """
        Save the current tab visibility settings to a JSON file.
        """
        try:
            # Create data structure
            data = {
                "hidden_tabs": list(self.hidden_tabs),
                "tab_names": {str(k): v for k, v in self.tab_names.items()}
            }
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            # Write to file
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Tab visibility settings saved to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error saving tab visibility settings: {str(e)}")
    
    def _load_tab_visibility(self) -> None:
        """
        Load the tab visibility settings from a JSON file.
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load hidden tabs
                self.hidden_tabs = set(data.get("hidden_tabs", []))
                logger.info(f"Loaded tab visibility settings from {self.config_path}")
            else:
                # Default to showing all tabs
                self.hidden_tabs = set()
                logger.info("No saved tab visibility settings found, showing all tabs")
                
        except Exception as e:
            # Default to showing all tabs on error
            self.hidden_tabs = set()
            logger.error(f"Error loading tab visibility settings: {str(e)}")
