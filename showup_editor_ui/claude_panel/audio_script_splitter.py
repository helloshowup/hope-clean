"""Audio Script Splitter Module for ClaudeAIPanel"""

import os
import re
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import logging
from typing import List, Any, Optional

# Get logger
logger = logging.getLogger("output_library_editor")

class AudioScriptSplitter:
    """Handles splitting markdown files with multiple audio scripts into separate files."""
    
    def __init__(self, script_splitter_tab: ttk.Frame, parent: Any):
        """
        Initialize the audio script splitter.
        
        Args:
            script_splitter_tab: The script splitter tab
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        self.script_splitter_tab = script_splitter_tab
        self.source_files: List[str] = []
        self.processing_thread: Optional[threading.Thread] = None
        self.output_dir: str = ""
        self.script_separator = "---"
        
    def setup_audio_script_splitter_tab(self) -> None:
        """Set up the audio script splitter tab."""
        # Create the main frame for this tab
        main_frame = ttk.Frame(self.script_splitter_tab, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Create side-by-side layout
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left pane for source file selection
        source_frame = ttk.LabelFrame(paned_window, text="Source Files")
        paned_window.add(source_frame, weight=1)
        
        # Right pane for configuration and output
        config_frame = ttk.LabelFrame(paned_window, text="Split Configuration")
        paned_window.add(config_frame, weight=1)
        
        # Source file selection components
        btn_frame = ttk.Frame(source_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        add_files_btn = ttk.Button(btn_frame, text="Add Files", command=self.select_source_files)
        add_files_btn.pack(side=tk.LEFT, padx=5)
        
        add_dir_btn = ttk.Button(btn_frame, text="Add Directory", command=self.select_directory_for_sources)
        add_dir_btn.pack(side=tk.LEFT, padx=5)
        
        clear_btn = ttk.Button(btn_frame, text="Clear", command=self.clear_sources)
        clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Source files listbox
        self.source_files_listbox = tk.Listbox(source_frame, selectmode=tk.EXTENDED, height=15)
        self.source_files_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(self.source_files_listbox, orient="vertical", command=self.source_files_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.source_files_listbox.config(yscrollcommand=scrollbar.set)
        
        # Configuration components
        # Output directory frame
        output_dir_frame = ttk.Frame(config_frame)
        output_dir_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(output_dir_frame, text="Output Directory:").pack(side=tk.LEFT, padx=5)
        
        self.output_dir_var = tk.StringVar()
        output_dir_entry = ttk.Entry(output_dir_frame, textvariable=self.output_dir_var, width=30)
        output_dir_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=5)
        
        browse_btn = ttk.Button(output_dir_frame, text="Browse...", command=self._browse_output_dir)
        browse_btn.pack(side=tk.RIGHT, padx=5)
        
        # Separator configuration
        separator_frame = ttk.Frame(config_frame)
        separator_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(separator_frame, text="Script Separator:").pack(side=tk.LEFT, padx=5)
        
        self.separator_var = tk.StringVar(value="---")
        separator_entry = ttk.Entry(separator_frame, textvariable=self.separator_var, width=10)
        separator_entry.pack(side=tk.LEFT, padx=5)
        
        # File naming configuration
        naming_frame = ttk.Frame(config_frame)
        naming_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(naming_frame, text="Output File Suffix:").pack(side=tk.LEFT, padx=5)
        
        self.suffix_var = tk.StringVar(value="_Audio.md")
        suffix_entry = ttk.Entry(naming_frame, textvariable=self.suffix_var, width=15)
        suffix_entry.pack(side=tk.LEFT, padx=5)
        
        # Description of functionality
        description_frame = ttk.LabelFrame(config_frame, text="About")
        description_frame.pack(fill="x", padx=5, pady=5)
        
        description = ttk.Label(description_frame, text="This tool splits markdown files containing multiple audio scripts into separate files.\n\n• Each script section should be separated by '---'\n• Each script should have a 'File name:' line (e.g., 'File name: 2-1-1.mp3')\n• Output files will be named based on the audio filename (e.g., '2-1-1_Audio.md')")
        description.pack(padx=10, pady=10, fill="x")
        
        # Process button
        process_frame = ttk.Frame(config_frame)
        process_frame.pack(fill="x", padx=5, pady=10)
        
        self.process_btn = ttk.Button(process_frame, text="Split Files", command=self.split_files)
        self.process_btn.pack(side=tk.LEFT, padx=5)
        
        self.cancel_btn = ttk.Button(process_frame, text="Cancel", command=self.cancel_processing, state="disabled")
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(main_frame, text="Preview & Log")
        preview_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(preview_frame, wrap=tk.WORD, height=10)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_text.insert(tk.END, "Ready to split audio script files.\n")
        self.log_text.config(state="disabled")
        
        # Progress bar and status
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var)
        self.status_label.pack(pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        
        # Log setup completion
        logger.info("Audio script splitter tab setup")
    
    def select_source_files(self) -> None:
        """Select source files to process."""
        files = filedialog.askopenfilenames(
            title="Select Source Files",
            filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if files:
            for file in files:
                if file not in self.source_files:
                    self.source_files.append(file)
                    self.source_files_listbox.insert(tk.END, file)
            
            logger.info(f"Added {len(files)} source files")
            self._append_to_log(f"Added {len(files)} files to the queue.")
    
    def select_directory_for_sources(self) -> None:
        """Select a directory of source files to process."""
        directory = filedialog.askdirectory(title="Select Directory with Source Files")
        if directory:
            md_files = []
            for root, _, files in os.walk(directory):
                for file in files:
                    if file.lower().endswith('.md'):
                        full_path = os.path.join(root, file)
                        if full_path not in self.source_files:
                            md_files.append(full_path)
            
            if md_files:
                for file in md_files:
                    self.source_files.append(file)
                    self.source_files_listbox.insert(tk.END, file)
                
                logger.info(f"Added {len(md_files)} source files from directory")
                self._append_to_log(f"Added {len(md_files)} files from directory.")
            else:
                messagebox.showinfo("No Files", "No markdown files found in the selected directory.")
    
    def clear_sources(self) -> None:
        """Clear all source files."""
        self.source_files = []
        self.source_files_listbox.delete(0, tk.END)
        logger.info("Cleared source files")
        self._append_to_log("Cleared all source files.")
    
    def _browse_output_dir(self) -> None:
        """Browse for output directory."""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir_var.set(directory)
    
    def _append_to_log(self, message: str) -> None:
        """Append a message to the log text area."""
        try:
            # Make sure the widget is in the correct state for modification
            current_state = str(self.log_text.cget("state"))
            
            # Always set to normal temporarily for editing
            self.log_text.config(state="normal")
            
            # Update content
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)
            
            # Restore original state (typically 'disabled')
            if current_state == "disabled":
                self.log_text.config(state="disabled")
                
            logger.info(f"Log updated: {message}")
        except Exception as e:
            logger.error(f"Error updating log: {str(e)}")
    
    def split_files(self) -> None:
        """Split the selected markdown files into individual audio script files."""
        # Check if there are source files to process
        if not self.source_files:
            messagebox.showwarning("No Files", "Please select source files to process.")
            return
        
        # Check output directory
        output_dir = self.output_dir_var.get()
        if not output_dir:
            messagebox.showwarning("No Output Directory", "Please select an output directory.")
            return
            
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create output directory: {str(e)}")
                return
        
        # Get separator
        self.script_separator = self.separator_var.get()
        if not self.script_separator:
            self.script_separator = "---"  # Default separator
            self.separator_var.set(self.script_separator)
        
        # Start processing in a separate thread
        self.status_var.set("Splitting files...")
        self.process_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.progress_bar.start()
        
        self._append_to_log(f"Starting to split {len(self.source_files)} files...")
        
        self.processing_thread = threading.Thread(
            target=self._split_files_thread
        )
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def _split_files_thread(self) -> None:
        """Thread function to split the files."""
        try:
            total_files = len(self.source_files)
            processed_files = 0
            total_scripts = 0
            
            for file_path in self.source_files:
                try:
                    # Update progress
                    file_name = os.path.basename(file_path)
                    self.parent.after(0, lambda: self.status_var.set(f"Processing {file_name}..."))
                    self.parent.after(0, lambda p=processed_files, t=total_files: self.progress_var.set((p / t) * 100))
                    
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                    
                    # Split content by separator
                    scripts = content.split(self.script_separator)
                    scripts = [script.strip() for script in scripts if script.strip()]
                    
                    # Process each script
                    script_count = 0
                    for script in scripts:
                        # Extract file name using regex
                        file_name_match = re.search(r'File name:[ \t]*(.*?)(?:\n|$)', script)
                        if file_name_match:
                            audio_file_name = file_name_match.group(1).strip()
                            # Remove file extension if present
                            audio_base_name = os.path.splitext(audio_file_name)[0]
                            
                            # Create output file name
                            output_file_name = f"{audio_base_name}{self.suffix_var.get()}"
                            output_path = os.path.join(self.output_dir_var.get(), output_file_name)
                            
                            # Save script to file
                            with open(output_path, 'w', encoding='utf-8') as out_file:
                                out_file.write(script)
                            
                            script_count += 1
                            total_scripts += 1
                            
                            # Log the file creation
                            log_msg = f"Created: {output_file_name}"
                            logger.info(log_msg)
                            self.parent.after(0, lambda msg=log_msg: self._append_to_log(msg))
                        else:
                            # If no file name is found, create a generic name
                            base_file_name = os.path.splitext(os.path.basename(file_path))[0]
                            output_file_name = f"{base_file_name}_part{script_count + 1}.md"
                            output_path = os.path.join(self.output_dir_var.get(), output_file_name)
                            
                            # Save script to file
                            with open(output_path, 'w', encoding='utf-8') as out_file:
                                out_file.write(script)
                            
                            script_count += 1
                            total_scripts += 1
                            
                            # Log the file creation
                            log_msg = f"Created: {output_file_name} (no file name found in script)"
                            logger.info(log_msg)
                            self.parent.after(0, lambda msg=log_msg: self._append_to_log(msg))
                    
                    # Update progress
                    processed_files += 1
                    log_msg = f"Processed {os.path.basename(file_path)}: Split into {script_count} files"
                    logger.info(log_msg)
                    self.parent.after(0, lambda msg=log_msg: self._append_to_log(msg))
                    
                except Exception as file_error:
                    error_msg = f"Error processing {os.path.basename(file_path)}: {str(file_error)}"
                    logger.error(error_msg)
                    self.parent.after(0, lambda msg=error_msg: self._append_to_log(msg))
            
            # Final update
            completion_msg = f"Completed! Processed {processed_files} files and created {total_scripts} script files."
            logger.info(completion_msg)
            self.parent.after(0, lambda msg=completion_msg: self._append_to_log(msg))
            
        except Exception as general_error:
            error_msg = f"Error splitting files: {str(general_error)}"
            logger.error(error_msg)
            self.parent.after(0, lambda msg=error_msg: self._append_to_log(msg))
            
        finally:
            # Reset UI
            self.parent.after(0, self._reset_ui_after_processing)
    
    def _reset_ui_after_processing(self) -> None:
        """Reset the UI after processing is complete."""
        self.status_var.set("Processing complete")
        self.process_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.progress_bar.stop()
        self.progress_var.set(100)
        
        # Show completion message
        output_dir = self.output_dir_var.get()
        messagebox.showinfo("Complete", f"All files have been processed and saved to:\n{output_dir}")
        
        # Open output directory
        if messagebox.askyesno("Open Directory", "Would you like to open the output directory?"):
            try:
                os.startfile(output_dir)
            except Exception as e:
                logger.error(f"Error opening directory: {str(e)}")
                messagebox.showerror("Error", f"Error opening directory: {str(e)}")
    
    def cancel_processing(self) -> None:
        """Cancel the file processing."""
        if self.processing_thread and self.processing_thread.is_alive():
            # We can't directly stop the thread, but we can indicate it should stop
            self.status_var.set("Cancelling...")
            self._append_to_log("Cancelling processing...")
            # The thread will have to check a flag or we'll have to wait for it to complete
