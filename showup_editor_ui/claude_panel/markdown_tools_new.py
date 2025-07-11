"""Markdown Tools Module for ClaudeAIPanel"""

import os
import logging
import re
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading

# Get logger
logger = logging.getLogger("output_library_editor")

class MarkdownTools:
    """Provides batch markdown editing tools for the ClaudeAIPanel."""
    
    def __init__(self, tools_tab, parent):
        """
        Initialize the markdown tools manager.
        
        Args:
            tools_tab: The markdown tools tab
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        self.tools_tab = tools_tab
        self.selected_files = []
        self.processing = False
        self.current_task = None
        
        # Dictionary of available tools with their descriptions and functions
        self.available_tools = {
            "standardize_headings": {
                "name": "Standardize H2 to H1 After Numbered Headings",
                "description": "Converts all ## headings to # headings when following a numbered H1 (e.g., # 7.4)",
                "function": self.standardize_headings
            },
            # Additional tools will be added here in the future
        }
    
    def setup_markdown_tools_tab(self):
        """Set up the markdown tools tab with tools and file selection."""
        # Create main frame
        main_frame = ttk.Frame(self.tools_tab, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Create side-by-side layout with PanedWindow
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left pane for file selection
        file_frame = ttk.LabelFrame(paned_window, text="Files to Process")
        paned_window.add(file_frame, weight=1)
        
        # Right pane for tools
        tools_frame = ttk.LabelFrame(paned_window, text="Markdown Tools")
        paned_window.add(tools_frame, weight=2)
        
        # File selection components
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        select_files_btn = ttk.Button(btn_frame, text="Select Files", command=self.select_files)
        select_files_btn.pack(side=tk.LEFT, padx=5)
        
        select_dir_btn = ttk.Button(btn_frame, text="Select Directory", command=self.select_directory)
        select_dir_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = ttk.Button(btn_frame, text="Clear Selection", command=self.clear_selection)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Files listbox with scrollbar
        self.files_listbox = tk.Listbox(file_frame, selectmode=tk.EXTENDED, height=15)
        self.files_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(self.files_listbox, orient="vertical", command=self.files_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.files_listbox.config(yscrollcommand=scrollbar.set)
        
        # Tools section with description and checkboxes
        tools_description = ttk.Label(tools_frame, text="Select a markdown tool to apply to the selected files:")
        tools_description.pack(anchor="w", padx=5, pady=5)
        
        # Create tool checkboxes
        self.tool_vars = {}
        tools_checkframe = ttk.Frame(tools_frame)
        tools_checkframe.pack(fill="x", padx=5, pady=5)
        
        for tool_id, tool_info in self.available_tools.items():
            var = tk.BooleanVar(value=False)
            self.tool_vars[tool_id] = var
            
            tool_frame = ttk.Frame(tools_checkframe)
            tool_frame.pack(fill="x", pady=2)
            
            checkbox = ttk.Checkbutton(tool_frame, text=tool_info["name"], variable=var)
            checkbox.pack(side=tk.LEFT)
            
            info_label = ttk.Label(tool_frame, text=tool_info["description"], font=("Arial", 9, "italic"))
            info_label.pack(side=tk.LEFT, padx=10)
        
        # Divider
        ttk.Separator(tools_frame, orient="horizontal").pack(fill="x", padx=5, pady=10)
        
        # Process button
        self.process_btn = ttk.Button(tools_frame, text="Process Files", command=self.process_files)
        self.process_btn.pack(pady=5)
        
        # Progress section
        progress_frame = ttk.Frame(tools_frame)
        progress_frame.pack(fill="x", padx=5, pady=10)
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        status_label.pack(fill="x")
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.pack(fill="x", pady=5)
        
        # Results text area
        results_frame = ttk.LabelFrame(tools_frame, text="Results")
        results_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.results_text = scrolledtext.ScrolledText(results_frame, height=10, wrap=tk.WORD)
        self.results_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Log setup completed
        logger.info("Markdown tools tab setup complete")
    
    def select_files(self):
        """Select files to process."""
        file_paths = filedialog.askopenfilenames(
            title="Select Markdown Files",
            filetypes=[(
                "Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")
            ]
        )
        
        if file_paths:
            # Convert to list
            file_paths = list(file_paths)
            self.update_file_selection(file_paths)
    
    def select_directory(self):
        """Select a directory and add all markdown files."""
        dir_path = filedialog.askdirectory(title="Select Directory with Markdown Files")
        
        if dir_path:
            # Find all markdown files in the directory
            markdown_files = []
            for root, _, files in os.walk(dir_path):
                for file in files:
                    if file.endswith(".md") or file.endswith(".txt"):
                        full_path = os.path.join(root, file)
                        markdown_files.append(full_path)
            
            if markdown_files:
                self.update_file_selection(markdown_files)
            else:
                messagebox.showinfo("No Files Found", "No markdown files found in the selected directory.")
    
    def update_file_selection(self, file_paths):
        """Update the file selection listbox."""
        # Clear current selection
        self.clear_selection()
        
        # Add new files
        self.selected_files = file_paths
        for file_path in file_paths:
            self.files_listbox.insert(tk.END, file_path)
        
        self.status_var.set(f"Selected {len(file_paths)} files")
        logger.info(f"Selected {len(file_paths)} files for markdown tools")
    
    def clear_selection(self):
        """Clear the file selection."""
        self.selected_files = []
        self.files_listbox.delete(0, tk.END)
        self.status_var.set("Ready")
    
    def process_files(self):
        """Process selected files with the selected tools."""
        # Check if files are selected
        if not self.selected_files:
            messagebox.showwarning("No Files Selected", "Please select files to process.")
            return
        
        # Check if any tools are selected
        selected_tools = [tool_id for tool_id, var in self.tool_vars.items() if var.get()]
        if not selected_tools:
            messagebox.showwarning("No Tools Selected", "Please select at least one tool to apply.")
            return
        
        # Confirm processing
        if not messagebox.askyesno("Confirm", f"Process {len(self.selected_files)} files with the selected tools?\n\nThis will modify the files directly."):
            return
        
        # Start processing in a thread
        self.processing = True
        self.progress_var.set(0)
        self.status_var.set("Processing...")
        self.process_btn.config(state="disabled")
        self.results_text.delete(1.0, tk.END)
        
        processing_thread = threading.Thread(
            target=self._process_files_thread,
            args=(self.selected_files, selected_tools)
        )
        processing_thread.daemon = True
        processing_thread.start()
    
    def _process_files_thread(self, files, selected_tools):
        """Process files in a background thread."""
        total_files = len(files)
        processed = 0
        results = []
        
        try:
            for file_path in files:
                if not self.processing:
                    break
                
                # Update status
                file_name = os.path.basename(file_path)
                self.status_var.set(f"Processing {file_name}...")
                self.parent.update_idletasks()
                
                try:
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Make a backup copy
                    from showup_core.file_utils import create_timestamped_backup

                    backup_path = create_timestamped_backup(file_path)
                    
                    # Apply each selected tool
                    modified = False
                    for tool_id in selected_tools:
                        if tool_id in self.available_tools:
                            tool_function = self.available_tools[tool_id]["function"]
                            new_content, tool_modified = tool_function(content, file_path)
                            
                            if tool_modified:
                                content = new_content
                                modified = True
                    
                    # Save changes if modified
                    if modified:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        results.append(f"u2713 {file_name}: Modified")
                    else:
                        results.append(f"u25cb {file_name}: No changes needed")
                
                except Exception as e:
                    error_msg = str(e)
                    results.append(f"u2717 {file_name}: Error - {error_msg}")
                    logger.error(f"Error processing {file_path}: {error_msg}")
                
                # Update progress
                processed += 1
                progress = (processed / total_files) * 100
                self.progress_var.set(progress)
                
                # Update results text
                self.parent.after(0, lambda: self._update_results("\n".join(results)))
            
            # Processing complete
            self.parent.after(0, lambda: self._processing_complete(processed, total_files))
            
        except Exception as e:
            logger.error(f"Error in processing thread: {str(e)}")
            self.parent.after(0, lambda: self._processing_error(str(e)))
    
    def _update_results(self, results_text):
        """Update the results text area."""
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, results_text)
        self.results_text.see(tk.END)  # Scroll to the end
    
    def _processing_complete(self, processed, total):
        """Update UI when processing is complete."""
        self.processing = False
        self.status_var.set(f"Completed: {processed} of {total} files processed")
        self.progress_var.set(100)
        self.process_btn.config(state="normal")
    
    def _processing_error(self, error_msg):
        """Update UI when an error occurs."""
        self.processing = False
        self.status_var.set(f"Error: {error_msg}")
        self.process_btn.config(state="normal")
    
    def standardize_headings(self, content, file_path=None):
        """
        Convert H2 headings to H1 headings after numbered H1 headings.
        
        Args:
            content: The markdown content to process
            file_path: Optional file path for logging
            
        Returns:
            tuple: (modified_content, was_modified)
        """
        file_name = os.path.basename(file_path) if file_path else "unknown"
        logger.info(f"Standardizing headings in {file_name}")
        
        # Split content into lines
        lines = content.split('\n')
        modified = False
        in_numbered_section = False
        
        for i in range(len(lines)):
            # Check for numbered heading like # 7.4
            if re.match(r'^# \d+\.\d+', lines[i]):
                in_numbered_section = True
                continue
            
            # If we're in a numbered section and find an H2, convert it to H1
            if in_numbered_section and lines[i].startswith('## '):
                lines[i] = '# ' + lines[i][3:]
                modified = True
                logger.info(f"Converted H2 to H1 at line {i+1} in {file_name}")
        
        # Join the lines back together
        modified_content = '\n'.join(lines)
        return modified_content, modified
