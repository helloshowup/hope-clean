"""Context Generator Module for ClaudeAIPanel"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
from .path_utils import get_project_root

# Import Claude API functionality
sys.path.append(os.path.join(str(get_project_root()), "showup-editor-ui"))
from claude_api import generate_with_claude_haiku
from cache_utils import get_cache_instance

# Get logger
logger = logging.getLogger("output_library_editor")

class ContextGenerator:
    """Handles context generation for the ClaudeAIPanel."""
    
    def __init__(self, parent):
        """Initialize the context generator.
        
        Args:
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        self.context = ""
        self.context_thread = None
        
    def setup_context_tab(self):
        """Set up the context generation tab."""
        tab = self.parent.context_tab
        
        # Create top frame for controls
        control_frame = ttk.Frame(tab)
        control_frame.pack(fill="x", pady=5)
        
        # Add generate button
        self.generate_btn = ttk.Button(control_frame, text="Generate Context", command=self.generate_context)
        self.generate_btn.pack(side="left", padx=5)
        
        # Add status label
        self.status_label = ttk.Label(control_frame, text="Ready")
        self.status_label.pack(side="left", padx=5)
        
        # Add progress bar
        self.progress = ttk.Progressbar(control_frame, mode="indeterminate")
        self.progress.pack(side="left", fill="x", expand=True, padx=5)
        
        # Create frame for context display
        context_frame = ttk.LabelFrame(tab, text="Generated Context")
        context_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Add context display text area
        self.context_display = scrolledtext.ScrolledText(context_frame, wrap=tk.WORD)
        self.context_display.pack(fill="both", expand=True, padx=5, pady=5)
        
    def generate_context(self):
        """Generate context using Claude Haiku API."""
        # Get current file content from main app
        file_content = self.parent.main_app.get_current_editor_content()
        if not file_content:
            messagebox.showinfo("No Content", "Please open a file first.")
            return
        
        # Get selected prompt file
        custom_prompt = None
        if hasattr(self.parent, 'prompt_manager') and self.parent.prompt_manager.selected_prompt:
            prompt_path = os.path.join(self.parent.prompt_manager.prompts_dir, 
                                    self.parent.prompt_manager.selected_prompt)
            with open(prompt_path, 'r', encoding='utf-8') as f:
                custom_prompt = f.read()
        
        # Get selected learner profile
        learner_profile = None
        if hasattr(self.parent, 'prompt_manager') and self.parent.prompt_manager.selected_profile:
            profile_path = os.path.join(self.parent.prompt_manager.profiles_dir, 
                                      self.parent.prompt_manager.selected_profile)
            with open(profile_path, 'r', encoding='utf-8') as f:
                learner_profile = f.read()
        
        # Update UI
        self.status_label.config(text="Generating context...")
        self.progress.start()
        self.generate_btn.config(state="disabled")
        self.context_display.config(state="normal")
        self.context_display.delete(1.0, tk.END)
        self.context_display.insert(tk.END, "Generating context... Please wait.")
        self.context_display.config(state="disabled")
        
        # Start generation thread
        self.parent.analyzing_context = True
        self.context_thread = threading.Thread(
            target=self._generate_context_thread,
            args=(file_content, custom_prompt, learner_profile)
        )
        self.context_thread.daemon = True
        self.context_thread.start()
    
    def _generate_context_thread(self, file_content, custom_prompt, learner_profile):
        """Thread function for generating context."""
        try:
            # Check cache first
            cache = get_cache_instance()
            cached_context = cache.get_context_cache(file_content, custom_prompt, learner_profile)
            
            if cached_context:
                logger.info("Using cached context")
                context = cached_context
            else:
                # Generate new context
                logger.info("Generating new context")
                custom_system_prompt = learner_profile if learner_profile else ""
                full_prompt = f"CONTENT:\n{file_content}\n\nPROMPT:\n{custom_prompt}"
                context = generate_with_claude_haiku(prompt=full_prompt, system_prompt=custom_system_prompt)
                
                # Save to cache
                if context:
                    cache.save_context_cache(file_content, custom_prompt, learner_profile, context)
            
            # Store context for later use
            self.context = context
            
            # Update UI with result
            self.parent.after(0, lambda: self._update_context_ui(context))
            
        except Exception as e:
            logger.error(f"Error generating context: {str(e)}")
            self.parent.after(0, lambda: self._update_context_ui(None, error=True))
        finally:
            self.parent.analyzing_context = False
    
    def _update_context_ui(self, context, error=False):
        """Update the context display UI after generation."""
        self.progress.stop()
        self.generate_btn.config(state="normal")
        
        if error:
            self.status_label.config(text="Error generating context")
            self.context_display.config(state="normal")
            self.context_display.delete(1.0, tk.END)
            self.context_display.insert(tk.END, "Error generating context. Please try again.")
            self.context_display.config(state="disabled")
            return
        
        self.status_label.config(text="Context generated successfully")
        self.context_display.config(state="normal")
        self.context_display.delete(1.0, tk.END)
        self.context_display.insert(tk.END, context if context else "No context generated.")
        self.context_display.config(state="disabled")
    
    def _generate_context_thread_for_batch(self, file_content, custom_prompt, learner_profile):
        """Generate context for a file in batch mode."""
        try:
            # Check cache first
            cache = get_cache_instance()
            cached_context = cache.get_context_cache(file_content, custom_prompt, learner_profile)
            
            if cached_context:
                logger.info("Using cached context for batch")
                return cached_context
            else:
                # Generate new context
                logger.info("Generating new context for batch")
                custom_system_prompt = learner_profile if learner_profile else ""
                full_prompt = f"CONTENT:\n{file_content}\n\nPROMPT:\n{custom_prompt}"
                context = generate_with_claude_haiku(prompt=full_prompt, system_prompt=custom_system_prompt)
                
                # Save to cache
                if context:
                    cache.save_context_cache(file_content, custom_prompt, learner_profile, context)
                
                return context
                
        except Exception as e:
            logger.error(f"Error generating context for batch: {str(e)}")
            return None
