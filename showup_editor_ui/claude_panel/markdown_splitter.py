"""Markdown Splitter Module for ClaudeAIPanel"""

import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import logging

# Get logger
logger = logging.getLogger("output_library_editor")

class MarkdownSplitterPanel:
    """Handles markdown splitting functionality for the ClaudeAIPanel."""
    
    def __init__(self, parent):
        """
        Initialize the markdown splitter panel.
        
        Args:
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        self.processing = False
        
    def setup_splitter_tab(self):
        """Set up the markdown splitter tab with UI elements."""
        tab = self.parent.md_splitter_tab
        
        # Main frame for all controls
        main_frame = ttk.Frame(tab, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(main_frame, text="Splitting Configuration", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Instructions
        instructions = ttk.Label(config_frame, 
                              text="Select files in the library panel and use the 'Split Selected Files' button below.")
        instructions.pack(anchor="w", padx=5, pady=5)
        
        # Starting number input
        number_frame = ttk.Frame(config_frame)
        number_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(number_frame, text="Starting Number (e.g., 1.6):").pack(side=tk.LEFT, padx=5)
        
        self.start_number_var = tk.StringVar(value="1.1")
        ttk.Entry(number_frame, textvariable=self.start_number_var, width=10).pack(side=tk.LEFT, padx=5)
        
        # Output directory
        output_frame = ttk.Frame(config_frame)
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(output_frame, text="Output Directory:").pack(side=tk.LEFT, padx=5)
        
        self.output_dir_var = tk.StringVar()
        output_entry = ttk.Entry(output_frame, textvariable=self.output_dir_var, width=40)
        output_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Button(output_frame, text="Browse", command=self.browse_output_dir).pack(side=tk.LEFT, padx=5)
        
        # Control buttons
        button_frame = ttk.Frame(config_frame, padding=5)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.process_button = ttk.Button(
            button_frame, 
            text="Split Selected Files", 
            command=self.split_selected_files,
            style="Accent.TButton"
        )
        self.process_button.pack(side=tk.LEFT, padx=10)
        
        # Status display
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=10, wrap=tk.WORD)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def split_selected_files(self):
        """Process the files selected in the main library panel."""
        # Get files selected in the main library panel
        selected_files = []
        
        if hasattr(self.parent, "file_tree") and self.parent.file_tree:
            for item_id in self.parent.file_tree.selection():
                item_values = self.parent.file_tree.item(item_id, "values")
                if item_values and len(item_values) > 1:
                    path = item_values[0]
                    item_type = item_values[1] if len(item_values) > 1 else ""
                    
                    # Only process files, not directories
                    if item_type != "directory" and os.path.isfile(path) and path.lower().endswith(".md"):
                        selected_files.append(path)
        
        # Check if any markdown files were selected
        if not selected_files:
            messagebox.showinfo("No Files Selected", "Please select markdown (.md) files in the library panel first.")
            return
        
        # Get output directory
        output_dir = self.output_dir_var.get().strip()
        if not output_dir:
            # Use the same directory as the first file if no output directory specified
            output_dir = os.path.dirname(selected_files[0])
            self.output_dir_var.set(output_dir)
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                self.log_status(f"Created output directory: {output_dir}")
            except Exception as e:
                self.log_status(f"Error creating output directory: {str(e)}")
                return
        
        # Get starting number
        start_number = self.start_number_var.get().strip()
        if not re.match(r'^\d+(\.\d+)?$', start_number):
            messagebox.showerror("Invalid Number", "Please enter a valid starting number (e.g., 1.1)")
            return
        
        # Process each selected file
        self.clear_status()
        self.log_status(f"Processing {len(selected_files)} files...")
        
        for file_path in selected_files:
            self.process_markdown_file(file_path, output_dir, start_number)
            
        self.log_status("\nAll files processed successfully!")

    def process_markdown_file(self, file_path, output_dir, start_number):
        """Process a single markdown file."""
        try:
            self.log_status(f"\nProcessing: {file_path}")
            
            # Read markdown content
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Get base filename without extension
            base_name = os.path.basename(file_path)
            name_without_ext = os.path.splitext(base_name)[0]
            
            # Split the content by pagebreaks
            sections = self.split_by_headers(content)
            
            # Parse the starting number
            if '.' in start_number:
                main_num, sub_num = map(int, start_number.split('.'))
            else:
                main_num, sub_num = int(start_number), 1
            
            # Create files for each section
            file_count = 0
            for section in sections:
                if section.strip():
                    section_num = f"{main_num}.{sub_num}"
                    
                    # Extract title for naming the file
                    title = self.extract_main_title(section)
                    
                    # Remove any existing section numbering (like # 4.1 at the start)
                    section = re.sub(r'^# \d+\.\d+\s*$', '', section, flags=re.MULTILINE)
                    section = section.strip()
                    
                    # Add the section number at the top
                    section = f"# {section_num}\n{section}"
                    
                    # Create output filename
                    output_filename = f"{name_without_ext}_{section_num}.md"
                    output_file = os.path.join(output_dir, output_filename)
                    
                    with open(output_file, 'w', encoding='utf-8') as out_file:
                        out_file.write(section)
                    
                    self.log_status(f"Created: {os.path.basename(output_file)}")
                    file_count += 1
                    sub_num += 1
            
            self.log_status(f"Split into {file_count} files")
            return True
        except Exception as e:
            self.log_status(f"Error processing {file_path}: {str(e)}")
            return False

    def browse_output_dir(self):
        """Browse for an output directory."""
        output_dir = filedialog.askdirectory()
        if output_dir:
            self.output_dir_var.set(output_dir)

    def log_status(self, message):
        """Add a message to the status display."""
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.parent.update_status(message)

    def clear_status(self):
        """Clear the status display."""
        self.status_text.delete(1.0, tk.END)

    def split_by_headers(self, content):
        """Split markdown content by pagebreaks."""
        # Split the content by pagebreaks instead of main headers
        sections = re.split(r'---pagebreak---', content)
        
        # Process each section
        processed_sections = []
        
        for i, section in enumerate(sections):
            if section.strip():
                if i > 0:  # Not the first section
                    # Try to find a section title from the first heading
                    heading_match = re.search(r'## ([^\n]+)', section)
                    section_title = heading_match.group(1).strip() if heading_match else f"Untitled Section {i}"
                    
                    # Add the section title to the section content
                    section = f"# {section_title}\n\n{section}"
                
                processed_sections.append(section)
        
        return processed_sections

    def extract_main_title(self, content):
        """Extract the main title from the section content, skipping 'Learning Objectives'."""
        # First look for a heading that starts with '# **' (bolded main title)
        title_match = re.search(r'# \*\*([^\*]+)\*\*', content)
        if title_match:
            return title_match.group(1).strip()
            
        # Look for all headings
        headings = re.findall(r'## ([^\n]+)', content)
        for heading in headings:
            if "Learning Objectives" not in heading:
                return heading.strip()
        
        # If no suitable heading found, use the first heading of any kind
        any_heading = re.search(r'# ([^\n]+)', content)
        if any_heading:
            return any_heading.group(1).strip()
            
        return None
