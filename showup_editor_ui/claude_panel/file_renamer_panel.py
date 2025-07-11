"""File Renamer Panel Module for ClaudeAIPanel"""

import os
import re
import logging
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import traceback
from datetime import datetime
import shutil
from typing import List, Dict, Tuple, Optional

# Get logger
logger = logging.getLogger("output_library_editor")


class FileRenamerPanel:
    """Handles file renaming functionality for standardizing markdown filenames."""
    
    def __init__(self, parent):
        """
        Initialize the file renamer panel.
        
        Args:
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        self.is_renaming = False
        self.files_to_rename = []
        self.rename_thread = None
        self.preview_data = []
    
    def setup_renamer_tab(self):
        """Set up the file renamer tab."""
        # Use the existing tab from the parent instead of creating a new one
        tab = self.parent.file_renamer_tab
        
        # Set up main frame with padding
        main_frame = ttk.Frame(tab, padding="10 10 10 10")
        main_frame.pack(fill="both", expand=True)
        
        # Controls frame
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(side="top", fill="x", expand=False, pady=(0, 10))
        
        # Files section
        files_frame = ttk.LabelFrame(controls_frame, text="Files to Rename")
        files_frame.pack(fill="x", expand=False, pady=(0, 10))
        
        self.file_count_var = tk.StringVar(value="No files selected")
        file_count_label = ttk.Label(files_frame, textvariable=self.file_count_var)
        file_count_label.pack(pady=5, padx=5, anchor="w")
        
        select_btn = ttk.Button(
            files_frame, 
            text="Select MD Files from Library", 
            command=lambda: self.update_file_list([f for f in self.parent.get_selected_files() if f.lower().endswith('.md')])
        )
        select_btn.pack(fill="x", padx=5, pady=5)
        
        # Options section
        options_frame = ttk.LabelFrame(controls_frame, text="Renaming Options")
        options_frame.pack(fill="x", expand=False, pady=(0, 10))
        
        # Create backup option
        self.backup_var = tk.BooleanVar(value=True)
        backup_cb = ttk.Checkbutton(
            options_frame, 
            text="Create backup of original files", 
            variable=self.backup_var
        )
        backup_cb.pack(anchor="w", padx=5, pady=5)
        
        # Buttons frame
        buttons_frame = ttk.Frame(controls_frame)
        buttons_frame.pack(fill="x", expand=False, pady=(0, 10))
        
        # Action buttons
        self.preview_btn = ttk.Button(
            buttons_frame, 
            text="Preview Renaming", 
            command=self.preview_rename_files,
            state=tk.DISABLED
        )
        self.preview_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.rename_btn = ttk.Button(
            buttons_frame, 
            text="Rename Files", 
            command=self.rename_files,
            state=tk.DISABLED
        )
        self.rename_btn.pack(side="left", fill="x", expand=True, padx=(5, 5))
        
        self.cancel_btn = ttk.Button(
            buttons_frame, 
            text="Cancel", 
            command=self.cancel_renaming,
            state=tk.DISABLED
        )
        self.cancel_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # Status and progress
        status_frame = ttk.Frame(controls_frame)
        status_frame.pack(fill="x", expand=False, pady=(0, 10))
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_label.pack(side="top", anchor="w", padx=5, pady=5)
        
        self.progress_bar = ttk.Progressbar(status_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", padx=5, pady=5)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(main_frame, text="Rename Preview")
        preview_frame.pack(side="top", fill="both", expand=True)
        
        # Set up the preview treeview
        columns = ("original", "new", "status")
        self.preview_tree = ttk.Treeview(preview_frame, columns=columns, show="headings")
        
        # Set column headings
        self.preview_tree.heading("original", text="Original Filename")
        self.preview_tree.heading("new", text="New Filename")
        self.preview_tree.heading("status", text="Status")
        
        # Set column widths
        self.preview_tree.column("original", width=300)
        self.preview_tree.column("new", width=300)
        self.preview_tree.column("status", width=100)
        
        # Add scrollbars
        preview_scrollbar_y = ttk.Scrollbar(preview_frame, orient="vertical", command=self.preview_tree.yview)
        self.preview_tree.configure(yscrollcommand=preview_scrollbar_y.set)
        
        preview_scrollbar_x = ttk.Scrollbar(preview_frame, orient="horizontal", command=self.preview_tree.xview)
        self.preview_tree.configure(xscrollcommand=preview_scrollbar_x.set)
        
        # Pack the treeview and scrollbars
        self.preview_tree.pack(side="left", fill="both", expand=True)
        preview_scrollbar_y.pack(side="right", fill="y")
        preview_scrollbar_x.pack(side="bottom", fill="x")
    
    def extract_module_info(self, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract module number and title from the markdown file."""
        try:
            # Initialize variables
            module_number = None
            module_title = None
            
            # First check the content of the file for a heading - this is the primary source
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
                # Pattern for title/heading at the beginning of the document
                title_pattern = r'^\s*#\s+(.*?)(?:\n|$)'
                title_match = re.search(title_pattern, content)
                
                if title_match:
                    heading_title = title_match.group(1).strip()
                    
                    # Try to extract module number if it exists in the heading - look for X.Y format
                    heading_pattern = r'(\d+)\.(\d+)\s+'
                    heading_match = re.search(heading_pattern, heading_title)
                    
                    if heading_match:
                        # Extract chapter and section numbers
                        chapter = heading_match.group(1)
                        section = heading_match.group(2)
                        module_number = f"{chapter}.{section}"
                        
                        # Remove module number from title for cleaner naming
                        clean_title = re.sub(r'\d+\.\d+\s+', '', heading_title).strip()
                        if clean_title:  # Only use if we have something meaningful
                            module_title = clean_title
                    else:
                        # Try alternative format with just a module number
                        alt_pattern = r'(\d+)[_\s]+(\d+)\s+'
                        alt_match = re.search(alt_pattern, heading_title)
                        
                        if alt_match:
                            chapter = alt_match.group(1)
                            section = alt_match.group(2)
                            module_number = f"{chapter}.{section}"
                            
                            # Remove module number from title
                            clean_title = re.sub(r'\d+[_\s]+\d+\s+', '', heading_title).strip()
                            if clean_title:  # Only use if we have something meaningful
                                module_title = clean_title
                        else:
                            # Last attempt - look for single number
                            single_number_pattern = r'(?:module|lesson|unit|section|chapter)?\s*(\d+)\s+'
                            single_match = re.search(single_number_pattern, heading_title, re.IGNORECASE)
                            
                            if single_match:
                                module_number = single_match.group(1)
                                
                                # Remove number from title
                                clean_title = re.sub(r'(?:module|lesson|unit|section|chapter)?\s*\d+\s+', '', heading_title, flags=re.IGNORECASE).strip()
                                if clean_title:  # Only use if we have something meaningful
                                    module_title = clean_title
                    
                    # If we have a heading but couldn't extract a module number or title, use the full heading as title
                    if not module_title:
                        module_title = heading_title
                
            # Only fall back to filename if we couldn't extract from the heading
            if not module_number or not module_title:
                basename = os.path.basename(file_path)
                filename_without_ext = os.path.splitext(basename)[0]
                
                # Check for patterns like 1_8_ in the filename
                filename_pattern = r'^(\d+)_(\d+)_'
                filename_match = re.search(filename_pattern, filename_without_ext)
                
                if filename_match and not module_number:
                    chapter = filename_match.group(1)
                    section = filename_match.group(2)
                    module_number = f"{chapter}.{section}"
                
                # If we still don't have a title, use the filename as a last resort
                if not module_title:
                    # Extract title from filename by removing the numbering prefix if present
                    if filename_match:
                        module_title = re.sub(r'^\d+_\d+_', '', filename_without_ext)
                    else:
                        module_title = filename_without_ext
                    # Replace underscores with spaces for better readability
                    module_title = module_title.replace('_', ' ')
            
            return module_number, module_title
                
        except Exception as e:
            logger.error(f"Error extracting info from {file_path}: {str(e)}")
            return None, None

    def generate_standard_filename(self, module_number: Optional[str], module_title: str, original_path: str) -> str:
        """Generate a standardized filename from module info."""
        # Clean up the title for use in filename
        clean_title = re.sub(r'[^\w\s-]', '', module_title).strip()  # Remove special chars
        clean_title = re.sub(r'\s+', '_', clean_title)  # Replace spaces with underscores
        
        # Get original file extension
        _, ext = os.path.splitext(original_path)
        
        # Generate filename with module number prefix if available
        if module_number:
            if '.' in module_number:
                # Handle X.Y format
                chapter, section = module_number.split('.')
                # Format as XX.YY (ensuring section is 2 digits but not adding leading zeros to section numbers > 9)
                formatted_number = f"{int(chapter):02d}.{int(section):02d}"
                return f"{formatted_number}_{clean_title}{ext}"
            else:
                # Handle single number format
                # Ensure module number has leading zero for single digits
                module_number = module_number.zfill(2) if len(module_number) == 1 else module_number
                return f"{module_number}_{clean_title}{ext}"
        else:
            return f"{clean_title}{ext}"
    
    def preview_rename_files(self):
        """Preview the renaming of selected files."""
        if not self.files_to_rename:
            messagebox.showinfo("No Files Selected", "Please select files to rename first.")
            return
        
        # Clear the preview treeview
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        
        self.preview_data = []
        for file_path in self.files_to_rename:
            try:
                # Skip if file doesn't exist
                if not os.path.exists(file_path):
                    continue
                
                # Get file directory and basename
                file_dir = os.path.dirname(file_path)
                basename = os.path.basename(file_path)
                
                # Extract module info from file
                module_number, module_title = self.extract_module_info(file_path)
                
                # Generate new filename
                new_filename = self.generate_standard_filename(module_number, module_title, file_path)
                
                # Check for naming conflicts
                new_path = os.path.join(file_dir, new_filename)
                
                # Determine status
                if new_filename == basename:
                    status = "No change"
                elif os.path.exists(new_path) and new_path != file_path:
                    status = "Conflict"
                else:
                    status = "Ready"
                
                # Store rename data
                self.preview_data.append({
                    "original_path": file_path,
                    "new_filename": new_filename,
                    "new_path": new_path,
                    "status": status
                })
                
                # Add to preview treeview
                self.preview_tree.insert(
                    "", "end", values=(basename, new_filename, status)
                )
                
            except Exception as e:
                logger.error(f"Error previewing {file_path}: {str(e)}")
                logger.error(traceback.format_exc())
        
        # Enable the rename button if there are files to rename
        if self.preview_data:
            self.rename_btn.config(state=tk.NORMAL)
    
    def rename_files(self):
        """Start the file renaming process."""
        if not self.preview_data:
            messagebox.showinfo("No Files to Rename", "Please preview the files first.")
            return
        
        # Confirm renaming
        confirm = messagebox.askyesno(
            "Confirm Renaming", 
            f"Are you sure you want to rename {len(self.preview_data)} files? This action cannot be undone."
        )
        
        if not confirm:
            return
        
        # Update UI
        self.is_renaming = True
        self.preview_btn.config(state=tk.DISABLED)
        self.rename_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress_bar.config(value=0)
        self.update_status("Starting renaming...")
        
        # Start renaming in a separate thread
        self.rename_thread = threading.Thread(
            target=self.run_renaming,
            args=(self.preview_data, self.backup_var.get())
        )
        self.rename_thread.daemon = True
        self.rename_thread.start()
    
    def run_renaming(self, rename_data: List[Dict], create_backup: bool):
        """Run the file renaming process in a separate thread."""
        try:
            # Initialize variables
            total_files = len(rename_data)
            renamed_count = 0
            skipped_count = 0
            error_count = 0
            
            # Process each file
            for i, data in enumerate(rename_data):
                # Check if renaming was cancelled
                if not self.is_renaming:
                    self.update_status("Renaming cancelled.")
                    break
                
                original_path = data["original_path"]
                new_path = data["new_path"]
                status = data["status"]
                
                # Skip if no change or conflict
                if status != "Ready":
                    skipped_count += 1
                    continue
                
                try:
                    # Create backup if requested
                    if create_backup:
                        from showup_core.file_utils import create_timestamped_backup

                        backup_dir = os.path.join(os.path.dirname(original_path), "_backups")
                        create_timestamped_backup(original_path, backup_dir)
                    
                    # Rename the file
                    os.rename(original_path, new_path)
                    renamed_count += 1
                    logger.info(f"Renamed: {os.path.basename(original_path)} -> {os.path.basename(new_path)}")
                    
                except Exception as e:
                    error_count += 1
                    logger.error(f"Error renaming {original_path}: {str(e)}")
                
                # Update progress
                progress = int(((i + 1) / total_files) * 100)
                self.update_progress(progress)
            
            # Final status update
            status_message = f"Renaming complete. Renamed: {renamed_count}, Skipped: {skipped_count}, Errors: {error_count}"
            self.update_status(status_message)
            logger.info(status_message)
            
            # Reset UI and refresh file tree
            self.parent.after(0, self.reset_ui)
            self.parent.after(0, self.parent.refresh_file_tree)
            
        except Exception as e:
            logger.error(f"Renaming error: {str(e)}")
            logger.error(traceback.format_exc())
            self.update_status(f"Error: {str(e)}")
            self.parent.after(0, self.reset_ui)
    
    def update_file_list(self, files=None):
        """Update the file count label."""
        if files is not None:
            self.files_to_rename = [f for f in files if f.lower().endswith(".md")]
        
        if not self.files_to_rename:
            self.file_count_var.set("No files selected")
            self.preview_btn.config(state=tk.DISABLED)
        elif len(self.files_to_rename) == 1:
            self.file_count_var.set(f"1 file selected: {os.path.basename(self.files_to_rename[0])}")
            self.preview_btn.config(state=tk.NORMAL)
        else:
            self.file_count_var.set(f"{len(self.files_to_rename)} files selected")
            self.preview_btn.config(state=tk.NORMAL)
    
    def update_status(self, message):
        """Update status label from any thread."""
        self.parent.after(0, lambda: self.status_var.set(message))
    
    def update_progress(self, value):
        """Update progress bar from any thread."""
        self.parent.after(0, lambda: self.progress_bar.config(value=value))
    
    def reset_ui(self):
        """Reset UI after renaming."""
        self.is_renaming = False
        self.preview_btn.config(state=tk.NORMAL)
        self.rename_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.DISABLED)
    
    def cancel_renaming(self):
        """Cancel the ongoing renaming process."""
        if self.is_renaming:
            self.is_renaming = False
            self.update_status("Cancelling renaming...")
            logger.info("User cancelled renaming")
