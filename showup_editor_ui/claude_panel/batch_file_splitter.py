"""Batch File Splitter Module for ClaudeAIPanel"""

import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import logging
import glob

# Get logger
logger = logging.getLogger("output_library_editor")

class BatchFileSplitterPanel:
    """Handles batch markdown splitting functionality with custom numbering."""
    
    def __init__(self, parent):
        """
        Initialize the batch file splitter panel.
        
        Args:
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        self.processing = False
        
    def setup_batch_splitter_tab(self):
        """Set up the batch file splitter tab with UI elements."""
        tab = self.parent.batch_splitter_tab
        
        # Main frame for all controls
        main_frame = ttk.Frame(tab, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(main_frame, text="Batch Splitting Configuration", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Instructions
        instructions = ttk.Label(config_frame, 
                              text="Select a folder containing markdown files to batch split with sequential numbering.")
        instructions.pack(anchor="w", padx=5, pady=5)
        
        # Input directory
        input_frame = ttk.Frame(config_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(input_frame, text="Input Directory:").pack(side=tk.LEFT, padx=5)
        
        self.input_dir_var = tk.StringVar()
        input_entry = ttk.Entry(input_frame, textvariable=self.input_dir_var, width=40)
        input_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        ttk.Button(input_frame, text="Browse", command=self.browse_input_dir).pack(side=tk.LEFT, padx=5)
        
        # Starting number input
        number_frame = ttk.Frame(config_frame)
        number_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(number_frame, text="Starting Number (e.g., 5.1):").pack(side=tk.LEFT, padx=5)
        
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
        
        # Keep original files checkbox
        preserve_frame = ttk.Frame(config_frame)
        preserve_frame.pack(fill=tk.X, pady=5)
        
        self.preserve_original_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(preserve_frame, text="Keep original files", variable=self.preserve_original_var).pack(anchor="w", padx=5)
        
        # Control buttons
        button_frame = ttk.Frame(config_frame, padding=5)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.process_button = ttk.Button(
            button_frame, 
            text="Start Batch Processing", 
            command=self.process_batch_files,
            style="Accent.TButton"
        )
        self.process_button.pack(side=tk.LEFT, padx=10)
        
        # Status display
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=10, wrap=tk.WORD)
        self.status_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def browse_input_dir(self):
        """Browse for an input directory."""
        input_dir = filedialog.askdirectory()
        if input_dir:
            self.input_dir_var.set(input_dir)
            # Auto-set output to same directory if not specified
            if not self.output_dir_var.get():
                self.output_dir_var.set(input_dir)
    
    def browse_output_dir(self):
        """Browse for an output directory."""
        output_dir = filedialog.askdirectory()
        if output_dir:
            self.output_dir_var.set(output_dir)
    
    def process_batch_files(self):
        """Process all markdown files in the input directory."""
        input_dir = self.input_dir_var.get().strip()
        output_dir = self.output_dir_var.get().strip()
        start_number = self.start_number_var.get().strip()
        
        # Validate input
        if not input_dir or not os.path.isdir(input_dir):
            messagebox.showerror("Invalid Input", "Please select a valid input directory.")
            return
        
        if not output_dir:
            output_dir = input_dir
            self.output_dir_var.set(output_dir)
        
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                self.log_status(f"Created output directory: {output_dir}")
            except Exception as e:
                self.log_status(f"Error creating output directory: {str(e)}")
                return
        
        # Validate starting number
        if not re.match(r'^\d+(\.\d+)?$', start_number):
            messagebox.showerror("Invalid Number", "Please enter a valid starting number (e.g., 5.1)")
            return
        
        # Find all markdown files in the input directory
        md_files = glob.glob(os.path.join(input_dir, "*.md"))
        
        # Filter out backup files (*.md.bak)
        md_files = [f for f in md_files if not f.lower().endswith('.md.bak')]
        
        if not md_files:
            messagebox.showinfo("No Files Found", "No markdown files found in the input directory.")
            return
        
        # Sort files naturally (by lesson numbers if available)
        md_files = self.natural_sort_files(md_files)
        
        # Process files
        self.clear_status()
        self.log_status(f"Processing {len(md_files)} files...")
        self.log_status(f"Starting with number: {start_number}")
        
        # Parse the starting number
        if '.' in start_number:
            main_num, sub_num = map(int, start_number.split('.'))
        else:
            main_num, sub_num = int(start_number), 1
            
        # Process each file
        for file_path in md_files:
            main_num, sub_num = self.process_file_with_sections(file_path, output_dir, main_num, sub_num)
        
        self.log_status("\nBatch processing completed!")
    
    def natural_sort_files(self, file_list):
        """Sort files naturally by their lesson numbers."""
        def extract_lesson_num(filename):
            basename = os.path.basename(filename)
            match = re.search(r'lesson(\d+)', basename)
            if match:
                return int(match.group(1))
            return 0  # Default if no lesson number found
        
        return sorted(file_list, key=extract_lesson_num)
    
    def process_file_with_sections(self, file_path, output_dir, main_num, sub_num):
        """Process a single markdown file, splitting it into sections with appropriate numbering."""
        try:
            self.log_status(f"\nProcessing: {os.path.basename(file_path)}")
            
            # Read markdown content
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Get base filename without extension
            base_name = os.path.basename(file_path)
            name_without_ext = os.path.splitext(base_name)[0]
            
            # Split the content by pagebreaks
            sections = self.split_by_pagebreaks(content)
            
            if not sections:
                self.log_status(f"No content found or no pagebreaks in {base_name}")
                return main_num, sub_num + 1
            
            # Create files for each section
            file_count = 0
            for section in sections:
                if section.strip():
                    section_num = f"{main_num}.{sub_num}"
                    
                    # Extract title for naming the file
                    title = self.extract_title(section) or f"section{sub_num}"
                    title_slug = self.create_slug(title)
                    
                    # Remove any existing section numbering
                    section = re.sub(r'^# \d+\.\d+\s*$', '', section, flags=re.MULTILINE)
                    section = section.strip()
                    
                    # Add the section number at the top
                    section = f"# {section_num}\n{section}"
                    
                    # Create output filename
                    output_filename = f"{name_without_ext}_{section_num}_{title_slug}.md"
                    output_file = os.path.join(output_dir, output_filename)
                    
                    with open(output_file, 'w', encoding='utf-8') as out_file:
                        out_file.write(section)
                    
                    self.log_status(f"Created: {os.path.basename(output_file)}")
                    file_count += 1
                    sub_num += 1
            
            self.log_status(f"Split into {file_count} files")
            return main_num, sub_num
        except Exception as e:
            self.log_status(f"Error processing {file_path}: {str(e)}")
            return main_num, sub_num + 1
    
    def split_by_pagebreaks(self, content):
        """Split markdown content by pagebreaks."""
        sections = re.split(r'---pagebreak---', content)
        return [section for section in sections if section.strip()]
    
    def extract_title(self, content):
        """Extract a title from the content."""
        # First try to find a heading starting with #
        heading_match = re.search(r'##?\s+([^\n]+)', content)
        if heading_match:
            return heading_match.group(1).strip()
        
        # Otherwise use the first line
        first_line = content.strip().split('\n')[0]
        return first_line[:40]  # Truncate long lines
    
    def create_slug(self, text):
        """Create a slug from text for filenames."""
        # Remove special characters and replace spaces with underscores
        slug = re.sub(r'[^\w\s]', '', text.lower())
        slug = re.sub(r'\s+', '_', slug)
        # Truncate to a reasonable length
        return slug[:30]
    
    def log_status(self, message):
        """Add a message to the status display."""
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.parent.update_status(message)
    
    def clear_status(self):
        """Clear the status display."""
        self.status_text.delete(1.0, tk.END)
