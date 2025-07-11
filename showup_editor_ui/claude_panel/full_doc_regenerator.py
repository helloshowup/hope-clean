"""Full Document Regeneration Module for ClaudeAIPanel"""

import os
import sys
import time
import logging
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import json
import threading
from .path_utils import get_project_root

# Add the parent directory to the system path for absolute imports
parent_dir = os.path.join(str(get_project_root()), "showup-editor-ui")
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import Claude API functions directly from the module
from claude_api import (
    regenerate_markdown_with_claude,
    generate_with_claude_haiku,
    CONTEXT_SYSTEM_PROMPT,
    CONTEXT_USER_PROMPT_TEMPLATE,
)

# Import cache utility from root directory
# Cache utilities
from cache_utils import get_cache_instance

# Get logger
logger = logging.getLogger("output_library_editor")


class FullDocRegenerator:
    """Handles batch processing of files for full document regeneration."""

    def __init__(self, full_regen_tab, parent):
        """
        Initialize the full document regenerator.
        
        Args:
            full_regen_tab: The full document regeneration tab
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        self.full_regen_tab = full_regen_tab
        self.batch_files = []  # List to store batch file paths
        self.batch_results = {}  # Dictionary to store batch results
        self.processing_batch = False  # Flag to indicate batch processing
        self.batch_thread = None
    
    def setup_full_regen_tab(self):
        """Set up the full document regeneration tab with a simplified interface."""
        # Create the main frame for this tab
        main_frame = ttk.Frame(self.full_regen_tab, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Create side-by-side layout
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left pane for file selection
        file_frame = ttk.LabelFrame(paned_window, text="Files")
        paned_window.add(file_frame, weight=1)
        
        # Right pane for configuration
        config_frame = ttk.LabelFrame(paned_window, text="Full Document Regeneration")
        paned_window.add(config_frame, weight=1)
        
        # File selection components
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        add_files_btn = ttk.Button(btn_frame, text="Add Files", command=self.select_files_for_batch)
        add_files_btn.pack(side=tk.LEFT, padx=5)
        
        add_dir_btn = ttk.Button(btn_frame, text="Add Directory", command=self.select_directory_for_batch)
        add_dir_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = ttk.Button(btn_frame, text="Clear", command=self.clear_batch)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Files listbox
        self.batch_files_listbox = tk.Listbox(file_frame, selectmode=tk.EXTENDED, height=15)
        self.batch_files_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(self.batch_files_listbox, orient="vertical", command=self.batch_files_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.batch_files_listbox.config(yscrollcommand=scrollbar.set)
        
        # Configuration components - Description
        description_frame = ttk.Frame(config_frame)
        description_frame.pack(fill="x", padx=5, pady=5)
        
        title = ttk.Label(description_frame, text="Full Document Regeneration Mode", font=("Helvetica", 10, "bold"))
        title.pack(anchor="w")
        
        description = ttk.Label(description_frame, text="Unlike line-by-line editing, this mode regenerates the entire document:")
        description.pack(anchor="w", pady=(5, 0))
        
        bullet_frame = ttk.Frame(description_frame)
        bullet_frame.pack(fill="x", padx=20, pady=5)
        
        bullet1 = ttk.Label(bullet_frame, text="• Uses the prompt from the 'Prompt Config' tab")
        bullet1.pack(anchor="w")
        
        bullet2 = ttk.Label(bullet_frame, text="• Uses the learner profile from the 'Prompt Config' tab")
        bullet2.pack(anchor="w")
        
        bullet3 = ttk.Label(bullet_frame, text="• Generates a completely new document for each file")
        bullet3.pack(anchor="w")
        
        bullet4 = ttk.Label(bullet_frame, text="• Minimal creativity to follow instructions precisely")
        bullet4.pack(anchor="w")
        
        bullet5 = ttk.Label(bullet_frame, text="• Original files will be backed up with .bak extension")
        bullet5.pack(anchor="w")
        
        # Temperature setting for creativity control
        temp_frame = ttk.Frame(config_frame)
        temp_frame.pack(fill="x", padx=5, pady=(10, 5))
        
        temp_label = ttk.Label(temp_frame, text="Temperature (creativity)")
        temp_label.pack(side=tk.LEFT, padx=5)
        
        self.temperature_var = tk.DoubleVar(value=0.0)
        self.temperature_scale = ttk.Scale(temp_frame, from_=0.0, to=1.0, 
                                         orient=tk.HORIZONTAL, variable=self.temperature_var,
                                         length=150)
        self.temperature_scale.pack(side=tk.LEFT, fill="x", expand=True, padx=5)
        
        self.temp_value_label = ttk.Label(temp_frame, text="0.0")
        self.temp_value_label.pack(side=tk.LEFT, padx=5)
        
        # Update temperature label when scale changes
        self.temperature_var.trace_add("write", self._update_temp_label)
        
        # View prompt button
        view_prompt_btn = ttk.Button(config_frame, text="View Current Prompt", command=self._show_current_prompt)
        view_prompt_btn.pack(pady=10)
        
        # Process button
        process_frame = ttk.Frame(config_frame)
        process_frame.pack(fill="x", padx=5, pady=10)
        
        self.process_btn = ttk.Button(process_frame, text="Process Batch", command=self.process_batch_regeneration)
        self.process_btn.pack(side=tk.LEFT, padx=5)
        
        self.cancel_btn = ttk.Button(process_frame, text="Cancel", command=self.cancel_batch_processing, state="disabled")
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Add status text at the bottom
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var)
        self.status_label.pack(pady=5)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        
        # Log setup completion
        logger.info("Full document regenerator tab setup")
    
    def _update_temp_label(self, *args):
        """Update the temperature value label."""
        value = self.temperature_var.get()
        self.temp_value_label.config(text=f"{value:.1f}")
    
    def prepare_batch_edit(self, files):
        """Prepare the batch edit panel with selected files."""
        # Clear existing batch files
        self.batch_files = []
        self.batch_files_listbox.delete(0, tk.END)
        
        # Add the new files
        self.batch_files = files
        for f in files:
            self.batch_files_listbox.insert(tk.END, f)
        
        # Log how many files are selected
        logger.info(f"Selected {len(files)} files for full document regeneration")
    
    def process_batch_regeneration(self):
        """Process all selected files with full document regeneration using the current prompt and configuration."""
        # Check if there are files to process
        batch_files = self.get_batch_files()
        if not batch_files:
            messagebox.showwarning("No Files", "Please select files to process.")
            return
        
        # Get current prompt from the prompt manager
        if not hasattr(self.parent, "prompt_manager") or not self.parent.prompt_manager.selected_prompt:
            messagebox.showwarning("No Prompt", "Please select a prompt in the Prompt Config tab.")
            return
            
        # Get prompt content
        prompt_text = ""
        if self.parent.prompt_manager.selected_prompt == "[Custom Prompt]":
            # Get custom prompt from text editor
            prompt_text = self.parent.prompt_manager.prompt_content.get(1.0, tk.END).strip()
        else:
            prompt_name = self.parent.prompt_manager.selected_prompt
            if prompt_name in self.parent.prompt_manager.prompts:
                # Access the content key from the prompt dictionary
                prompt_text = self.parent.prompt_manager.prompts[prompt_name]["content"]
            
        if not prompt_text or not prompt_text.strip():
            messagebox.showwarning("Empty Prompt", "The selected prompt is empty. Please select a different prompt.")
            return
        
        # Get learner profile from the prompt manager - profiles are stored in parent.profiles
        selected_profile = self.parent.prompt_manager.selected_profile
        learner_profile = ""
        
        if selected_profile and selected_profile in self.parent.profiles:
            # Access the system field from the profile dictionary
            learner_profile = self.parent.profiles[selected_profile]["system"]
        
        # Get temperature value
        temperature = self.temperature_var.get()
        
        # Log batch processing start
        logger.info(f"Starting full document regeneration with prompt '{self.parent.prompt_manager.selected_prompt}' and profile '{selected_profile}'")
        logger.info(f"Processing {len(batch_files)} files with temperature: {temperature}")
        
        # Set UI state for processing
        self.processing_batch = True
        self.progress_var.set(0)
        self.status_var.set("Starting batch regeneration...")
        self.process_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        
        # Start processing in a thread
        self.batch_thread = threading.Thread(
            target=self._process_files, 
            args=(batch_files, prompt_text, learner_profile, temperature)
        )
        self.batch_thread.daemon = True
        self.batch_thread.start()
    
    def cancel_batch_processing(self):
        """Cancel batch processing."""
        if self.processing_batch and self.batch_thread and self.batch_thread.is_alive():
            self.processing_batch = False
            logger.info("Batch regeneration cancelled")
            self.status_var.set("Cancelling...")
            self.cancel_btn.config(state="disabled")
    
    def _update_progress(self, index, total):
        """Update progress bar and status."""
        progress = (index / total) * 100
        self.progress_var.set(progress)
        self.status_var.set(f"Processing {index} of {total} files...")
    
    def _process_files(self, files, prompt, learner_profile, temperature):
        """Process each file in the batch with the given prompt, learner profile and temperature.
        
        Args:
            files (list): List of file paths to process
            prompt (str): Enhancement prompt to use
            learner_profile (str): Target learner profile to use
            temperature (float): Temperature setting for generation
        """
        # Begin batch processing
        logger.info(f"Starting batch regeneration of {len(files)} files with prompt '{prompt[:50]}...'")
        
        # Track progress
        start_time = time.time()
        total_files = len(files)
        processed_files = 0
        failed_files = 0
        
        # Process each file
        for i, file_path in enumerate(files):
            # Check if processing was cancelled
            if not self.processing_batch:
                logger.info("Batch regeneration cancelled")
                break
            
            # Update progress
            self.progress_var.set((i / total_files) * 100)
            self.status_var.set(f"Processing file {i+1} of {total_files}: {os.path.basename(file_path)}")
            self.parent.update_idletasks()
            
            try:
                # Log file processing start
                logger.info(f"Processing file {i+1}/{total_files}: {file_path}")
                
                # Read the file
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Skip empty files
                if not file_content.strip():
                    logger.warning(f"Skipping empty file: {file_path}")
                    continue
                    
                # First generate context based on the learner profile
                context = ""
                if learner_profile:
                    logger.info(f"Generating context for {os.path.basename(file_path)}...")
                    
                    # Replace hardcoded template with the imported template using .format()
                    full_prompt = CONTEXT_USER_PROMPT_TEMPLATE.format(
                        prompt=prompt,
                        learner_profile=learner_profile,
                        file_content=file_content
                    )
                    
                    try:
                        # Log context generation step
                        logger.info(f"Calling Claude Haiku for context generation: {os.path.basename(file_path)}")
                        
                        # Generate context using specific model for context generation
                        context = generate_with_claude_haiku(
                            prompt=full_prompt,
                            system_prompt=CONTEXT_SYSTEM_PROMPT,
                            max_tokens=2000
                        )
                        
                        # Log success
                        context_size = len(context)
                        logger.info(f"Generated context of {context_size} chars for {os.path.basename(file_path)}")
                        
                        # Save the context response for debugging
                        context_response_data = {
                            "file": os.path.basename(file_path),
                            "request_type": "context_generation",
                            "prompt": full_prompt,
                            "response": context
                        }
                        self._save_api_response_to_log(context_response_data)
                        
                    except Exception as e:
                        logger.error(f"Error generating context: {str(e)}")
                        context = ""
                
                # Now regenerate the entire content
                logger.info(f"Regenerating content for {os.path.basename(file_path)}...")
                
                # Generate regenerated content using the regenerate function
                regenerated_content = regenerate_markdown_with_claude(
                    markdown_text=file_content,
                    instructions=prompt,
                    context=context,
                    temperature=temperature
                )
                
                # Log regeneration response for debugging
                regenerate_response_data = {
                    "file": os.path.basename(file_path),
                    "request_type": "regenerate_markdown",
                    "markdown_text": file_content,
                    "instructions": prompt,
                    "context": context,
                    "temperature": temperature,
                    "response": regenerated_content
                }
                self._save_api_response_to_log(regenerate_response_data)
                
                # Save the regenerated content
                if regenerated_content:
                    # Create backup file
                    from showup_core.file_utils import create_timestamped_backup

                    create_timestamped_backup(file_path)
                    
                    # Save the regenerated content over the original file
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(regenerated_content)
                    
                    processed_files += 1
                    logger.info(f"Successfully processed {file_path}")
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
                failed_files += 1
            
        # Update UI when done
        elapsed_time = time.time() - start_time
        logger.info(
            f"Batch regeneration completed. Processed {processed_files} of {total_files} files in {elapsed_time:.2f}s. Failed: {failed_files}"
        )
        self.parent.after(
            0,
            lambda: self._update_batch_completed(
                processed_files,
                total_files,
                failed_files,
            ),
        )
    def _update_batch_completed(self, processed, total, failed=0):
        """Update UI when batch processing is completed."""
        status_message = (
            f"Batch regeneration completed: {processed} of {total} files processed"
        )
        if failed:
            status_message += f" \u2013 {failed} failed"
            self.status_label.config(foreground="red")
        else:
            self.status_label.config(foreground="black")
        self.status_var.set(status_message)
        self.progress_var.set(100)  # Set to 100% even if some failed
        self.process_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.processing_batch = False
    
    def _update_batch_cancelled(self, processed, total):
        """Update UI when batch processing is cancelled."""
        self.status_var.set(f"Batch regeneration cancelled: {processed} of {total} files processed")
        self.process_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.processing_batch = False
    
    def get_batch_files(self):
        """Return the list of files currently in the batch."""
        return [self.batch_files_listbox.get(i) for i in range(self.batch_files_listbox.size())]
    
    def _show_current_prompt(self):
        """Show the current prompt being used for batch regeneration."""
        if not hasattr(self.parent, "prompt_manager") or not self.parent.prompt_manager.selected_prompt:
            messagebox.showinfo("No Prompt Selected", "Please select a prompt in the Prompt Config tab.")
            return
        
        # Show the prompt dialog using the prompt manager's function
        self.parent.prompt_manager.show_full_prompt_dialog()
    
    def clear_batch(self):
        """Clear the batch files list."""
        self.batch_files = []
        self.batch_files_listbox.delete(0, tk.END)
        self.status_var.set("Ready")
        self.progress_var.set(0)
    
    def select_files_for_batch(self):
        """Select files manually for batch processing."""
        file_paths = filedialog.askopenfilenames(
            title="Select Files for Full Document Regeneration",
            filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        
        if file_paths:
            # Convert to list and store
            file_paths = list(file_paths)
            self.prepare_batch_edit(file_paths)
            
            # Log selected files
            logger.info(f"Selected {len(file_paths)} files for full document regeneration")
    
    def select_directory_for_batch(self):
        """Select a directory and add all files with the specified extensions."""
        extensions = (".md", ".txt", ".markdown")  # Extensions to filter
        
        # Show directory selection dialog
        dir_path = filedialog.askdirectory(title="Select Directory for Full Document Regeneration")
        
        if not dir_path:
            return
        
        # Find all markdown files in the directory (recursively)
        files = []
        for root, _, filenames in os.walk(dir_path):
            for filename in filenames:
                if filename.endswith(extensions):
                    file_path = os.path.join(root, filename)
                    files.append(file_path)
        
        if files:
            self.prepare_batch_edit(files)
            logger.info(f"Found {len(files)} markdown files in {dir_path}")
        else:
            messagebox.showinfo("No Files", f"No markdown files found in {dir_path}")
    
    def _save_api_response_to_log(self, response_data):
        """Save API response to a JSON file in the logs folder.
        
        Args:
            response_data (dict): Dictionary containing the response data to save
        """
        try:
            # Create logs directory if it doesn't exist
            logs_dir = os.path.join(str(get_project_root()), "showup-editor-ui", "logs", "api_responses")
            os.makedirs(logs_dir, exist_ok=True)
            
            # Create a timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{response_data['request_type']}_{os.path.splitext(response_data['file'])[0]}.json"
            file_path = os.path.join(logs_dir, filename)
            
            # Write the response data to a JSON file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, indent=2, ensure_ascii=False)
                
            logger.debug(f"Saved API response to {file_path}")
            
        except Exception as e:
            logger.error(f"Error saving API response to log: {str(e)}")
