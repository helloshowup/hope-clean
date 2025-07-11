"""Markdown Tools Module for ClaudeAIPanel"""

import os
import logging
import re
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import traceback

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
            "ensure_heading_spacing": {
                "name": "Ensure Space Between Numbered Headings",
                "description": "Ensures there's a blank line between numbered headings (e.g., # 7.3) and subsequent headings",
                "function": self.ensure_heading_spacing
            },
            "remove_heading_bold": {
                "name": "Remove Bold Formatting from Headings",
                "description": "Removes redundant bold formatting (** **) from all heading levels",
                "function": self.remove_heading_bold
            },
            "standardize_key_takeaways": {
                "name": "Standardize Key Takeaways to H2",
                "description": "Ensures 'Key Takeaways' headings are always H2 (##) level",
                "function": self.standardize_key_takeaways
            },
            "standardize_learning_objectives": {
                "name": "Standardize Learning Objectives to H2",
                "description": "Ensures 'Learning Objectives' headings are always H2 (##) level",
                "function": self.standardize_learning_objectives
            },
            "remove_stop_reflect_headings": {
                "name": "Remove Stop and Reflect Headings",
                "description": "Removes '# Stop and reflect' headings from within stopandreflect sections",
                "function": self.remove_stop_reflect_headings
            },
            "standardize_podcast_headings": {
                "name": "Standardize Podcast Headings to H2",
                "description": "Ensures 'Lesson Podcast Discussion:' headings are always H2 (##) level",
                "function": self.standardize_podcast_headings
            },
            "add_keytakeaways_markers": {
                "name": "Add Key Takeaways Markers",
                "description": "Adds marker tags around Key Takeaways sections and ensures proper spacing",
                "function": self.add_keytakeaways_markers
            },
            "ensure_bullet_list_spacing": {
                "name": "Ensure Space Before Bullet Lists",
                "description": "Ensures there's a blank line between text and bullet lists for proper HTML formatting",
                "function": self.ensure_bullet_list_spacing
            },
            "convert_asterisk_to_dash": {
                "name": "Convert Asterisk Bullets to Dash",
                "description": "Converts asterisk bullets (*) to dash bullets (-) while preserving bold formatting",
                "function": self.convert_asterisk_to_dash
            },
            "fix_indented_lists": {
                "name": "Fix Indented Markdown Lists",
                "description": "Removes extra spacing before list items to ensure proper markdown formatting",
                "function": self.fix_indented_lists
            },
            "fix_extra_indented_bullets": {
                "name": "Fix Extra Indented Bullet Points",
                "description": "Removes extra spacing before bullet points that follow text lines",
                "function": self.fix_extra_indented_bullets
            },
            "add_br_tags_at_blank_lines": {
                "name": "Add <br/> Tags at Blank Lines",
                "description": "Adds <br/> tags at blank lines between paragraphs for proper HTML formatting",
                "function": self.add_br_tags_at_blank_lines
            }
            # Additional tools will be added here in the future
        }
    
    def setup_markdown_tools_tab(self):
        """Set up the markdown tools tab with tools and file selection."""
        # Create main frame
        main_frame = ttk.Frame(self.tools_tab, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Create tools frame
        tools_frame = ttk.LabelFrame(main_frame, text="Markdown Tools")
        tools_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Tools section with description and checkboxes
        tools_description = ttk.Label(tools_frame, text="Select a markdown tool to apply to the selected files:")
        tools_description.pack(anchor="w", padx=5, pady=5)
        
        # Add instruction label for file selection
        selection_instructions = ttk.Label(tools_frame, text="Note: Select files in the library panel on the left before processing.", 
                                       font=("Arial", 9, "italic"), foreground="#555555")
        selection_instructions.pack(anchor="w", padx=5, pady=0)
        
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
    
    def process_files(self):
        """Process selected files with the selected tools."""
        try:
            # Get selected files from the main library panel
            selected_files = self.parent.get_selected_files()
            self.selected_files = selected_files
            
            # Check if files are selected
            if not self.selected_files:
                messagebox.showwarning("No Files Selected", "Please select files in the library panel to process.")
                return
            
            # Log the selected files
            logger.info(f"Processing {len(self.selected_files)} files with Markdown Tools")
            for file_path in self.selected_files[:5]:  # Log first 5 for debugging
                logger.info(f"Selected file: {file_path}")
            
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
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error starting file processing: {error_msg}")
            logger.error(traceback.format_exc())
            messagebox.showerror("Error", f"Failed to process files: {error_msg}")
            self.status_var.set(f"Error: {error_msg}")
            self.progress_var.set(0)
            self.process_btn.config(state="normal")
    
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
        try:
            # Make sure the widget is in the correct state for modification
            current_state = str(self.results_text.cget("state"))
            if current_state == "disabled":
                self.results_text.config(state="normal")
                
            # Update content
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, results_text)
            
            # Restore original state if it was disabled
            if current_state == "disabled":
                self.results_text.config(state="disabled")
            
            # Scroll to the top
            self.results_text.see("1.0")
            
            # Update UI - this will happen on the main thread
            self.parent.update_idletasks()
        except Exception as e:
            logger.error(f"Error updating results text: {str(e)}")
    
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
        But only convert the first heading after each numbered heading.
        
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
        looking_for_next_heading = False
        
        for i in range(len(lines)):
            # Check for numbered heading like # 7.4
            if re.match(r'^# \d+\.\d+', lines[i]):
                looking_for_next_heading = True
                continue
            
            # If we're looking for the next heading and find an H2, convert it to H1
            if looking_for_next_heading and lines[i].startswith('## '):
                lines[i] = '# ' + lines[i][3:]
                modified = True
                looking_for_next_heading = False  # Reset flag after converting
                logger.info(f"Converted H2 to H1 at line {i+1} in {file_name}")
            # If we find any heading, reset the flag (we've passed the immediate next heading)
            elif looking_for_next_heading and lines[i].startswith('#'):
                looking_for_next_heading = False
        
        # Join the lines back together
        modified_content = '\n'.join(lines)
        return modified_content, modified

    def ensure_heading_spacing(self, content, file_path=None):
        """
        Ensure there's a blank line between numbered headings and subsequent headings.
        
        Args:
            content: The markdown content to process
            file_path: Optional file path for logging
            
        Returns:
            tuple: (modified_content, was_modified)
        """
        file_name = os.path.basename(file_path) if file_path else "unknown"
        logger.info(f"Ensuring heading spacing in {file_name}")
        
        # Split content into lines
        lines = content.split('\n')
        modified = False
        
        # Process the lines
        i = 0
        while i < len(lines) - 1:
            # Check for numbered heading like # 7.3
            if re.match(r'^# \d+\.\d+', lines[i]):
                # Check if the next line is a heading without a blank line in between
                if i + 1 < len(lines) and lines[i+1].startswith('#'):
                    # Insert a blank line between the numbered heading and the following heading
                    lines.insert(i + 1, '')
                    modified = True
                    logger.info(f"Added spacing after numbered heading at line {i+1} in {file_name}")
                    i += 1  # Skip the newly added line
            i += 1
        
        # Join the lines back together
        modified_content = '\n'.join(lines)
        return modified_content, modified

    def remove_heading_bold(self, content, file_path=None):
        """
        Remove bold formatting (** **) from all headings.
        
        Args:
            content: The markdown content to process
            file_path: Optional file path for logging
            
        Returns:
            tuple: (modified_content, was_modified)
        """
        file_name = os.path.basename(file_path) if file_path else "unknown"
        logger.info(f"Removing bold formatting from headings in {file_name}")
        
        # Split content into lines
        lines = content.split('\n')
        modified = False
        
        # Regular expression to match bold headings
        # This matches lines that start with #, followed by any number of spaces, 
        # then ** at the beginning of the heading text and ** at the end
        bold_heading_pattern = re.compile(r'^(#+)\s+\*\*(.+?)\*\*$')
        
        # Process each line
        for i in range(len(lines)):
            line = lines[i]
            # Check if this line is a heading with bold formatting
            match = bold_heading_pattern.match(line)
            if match:
                # Get the heading level (#, ##, etc) and the content
                heading_level = match.group(1)
                heading_content = match.group(2)
                
                # Create new heading without bold formatting
                lines[i] = f"{heading_level} {heading_content}"
                modified = True
                logger.info(f"Removed bold formatting from heading at line {i+1} in {file_name}")
        
        # Join the lines back together
        modified_content = '\n'.join(lines)
        return modified_content, modified

    def standardize_key_takeaways(self, content, file_path=None):
        """
        Ensure 'Key Takeaways' headings are always at H2 (##) level.
        
        Args:
            content: The markdown content to process
            file_path: Optional file path for logging
            
        Returns:
            tuple: (modified_content, was_modified)
        """
        file_name = os.path.basename(file_path) if file_path else "unknown"
        logger.info(f"Standardizing 'Key Takeaways' headings in {file_name}")
        
        # Split content into lines
        lines = content.split('\n')
        modified = False
        
        # Regular expression to match 'Key Takeaways' headings at any level
        # This matches lines that start with any number of #, then 'Key Takeaways'
        key_takeaways_pattern = re.compile(r'^(#+)\s+Key\s+Takeaways\s*$', re.IGNORECASE)
        
        # Process each line
        for i in range(len(lines)):
            line = lines[i]
            # Check if this line is a 'Key Takeaways' heading
            match = key_takeaways_pattern.match(line)
            if match:
                # If the heading is not already H2 (##), convert it
                if match.group(1) != '##':
                    lines[i] = '## Key Takeaways'
                    modified = True
                    logger.info(f"Standardized 'Key Takeaways' heading to H2 at line {i+1} in {file_name}")
        
        # Join the lines back together
        modified_content = '\n'.join(lines)
        return modified_content, modified

    def standardize_learning_objectives(self, content, file_path=None):
        """
        Ensure 'Learning Objectives' headings are always at H2 (##) level.
        
        Args:
            content: The markdown content to process
            file_path: Optional file path for logging
            
        Returns:
            tuple: (modified_content, was_modified)
        """
        file_name = os.path.basename(file_path) if file_path else "unknown"
        logger.info(f"Standardizing 'Learning Objectives' headings in {file_name}")
        
        # Split content into lines
        lines = content.split('\n')
        modified = False
        
        # Regular expression to match 'Learning Objectives' headings at any level
        # This matches lines that start with any number of #, then 'Learning Objectives'
        learning_objectives_pattern = re.compile(r'^(#+)\s+Learning\s+Objectives\s*$', re.IGNORECASE)
        
        # Process each line
        for i in range(len(lines)):
            line = lines[i]
            # Check if this line is a 'Learning Objectives' heading
            match = learning_objectives_pattern.match(line)
            if match:
                # If the heading is not already H2 (##), convert it
                if match.group(1) != '##':
                    lines[i] = '## Learning Objectives'
                    modified = True
                    logger.info(f"Standardized 'Learning Objectives' heading to H2 at line {i+1} in {file_name}")
        
        # Join the lines back together
        modified_content = '\n'.join(lines)
        return modified_content, modified

    def remove_stop_reflect_headings(self, content, file_path=None):
        """
        Remove '# Stop and reflect' headings from within stopandreflect sections.
        
        Args:
            content: The markdown content to process
            file_path: Optional file path for logging
            
        Returns:
            tuple: (modified_content, was_modified)
        """
        file_name = os.path.basename(file_path) if file_path else "unknown"
        logger.info(f"Removing 'Stop and reflect' headings in {file_name}")
        
        # Look for stopandreflect sections
        start_pattern = r'---stopandreflect---'
        end_pattern = r'---stopandreflectEND---'
        heading_pattern = r'#+\s+Stop\s+and\s+reflect\s*$'
        
        # Check if the content contains stopandreflect sections
        if not re.search(start_pattern, content) or not re.search(end_pattern, content):
            return content, False
        
        # Split content into lines for easier processing
        lines = content.split('\n')
        modified = False
        inside_sr_section = False
        result_lines = []
        
        for line in lines:
            # Track when we enter/exit stopandreflect sections
            if re.match(start_pattern, line):
                inside_sr_section = True
                result_lines.append(line)
                continue
            elif re.match(end_pattern, line):
                inside_sr_section = False
                result_lines.append(line)
                continue
            
            # If inside a stopandreflect section, look for the heading to remove
            if inside_sr_section and re.match(heading_pattern, line, re.IGNORECASE):
                # Skip this line (don't add it to result_lines)
                modified = True
                logger.info(f"Removed 'Stop and reflect' heading in stopandreflect section in {file_name}")
            else:
                # Keep the line
                result_lines.append(line)
        
        # Join the lines back together
        modified_content = '\n'.join(result_lines)
        return modified_content, modified

    def standardize_podcast_headings(self, content, file_path=None):
        """
        Ensure 'Lesson Podcast Discussion:' headings are always at H2 (##) level.
        
        Args:
            content: The markdown content to process
            file_path: Optional file path for logging
            
        Returns:
            tuple: (modified_content, was_modified)
        """
        file_name = os.path.basename(file_path) if file_path else "unknown"
        logger.info(f"Standardizing podcast headings in {file_name}")
        
        # Split content into lines
        lines = content.split('\n')
        modified = False
        
        # Regular expression to match 'Lesson Podcast Discussion:' headings at any level
        # This matches lines that start with any number of #, then 'Lesson Podcast Discussion:'
        # The pattern accounts for possible additional text after the colon
        podcast_pattern = re.compile(r'^(#+)\s+Lesson\s+Podcast\s+Discussion:\s*(.*)$', re.IGNORECASE)
        
        # Process each line
        for i in range(len(lines)):
            line = lines[i]
            # Check if this line is a podcast heading
            match = podcast_pattern.match(line)
            if match:
                # If the heading is not already H2 (##), convert it
                if match.group(1) != '##':
                    # Preserve any text that comes after 'Lesson Podcast Discussion:'
                    additional_text = match.group(2)
                    if additional_text:
                        lines[i] = f"## Lesson Podcast Discussion: {additional_text}"
                    else:
                        lines[i] = "## Lesson Podcast Discussion:"
                    modified = True
                    logger.info(f"Standardized podcast heading to H2 at line {i+1} in {file_name}")
        
        # Join the lines back together
        modified_content = '\n'.join(lines)
        return modified_content, modified
        
    def add_keytakeaways_markers(self, content, file_path=None):
        """
        Add marker tags around Key Takeaways sections and ensure proper spacing.
        
        Args:
            content: The markdown content to process
            file_path: Optional file path for logging
            
        Returns:
            tuple: (modified_content, was_modified)
        """
        file_name = os.path.basename(file_path) if file_path else "unknown"
        logger.info(f"Adding markers to Key Takeaways sections in {file_name}")
        
        # Check if the file already has keytakeaways markers
        if "---keytakeaways---" in content:
            logger.info(f"File {file_name} already has keytakeaways markers")
            return content, False
        
        # Split content into lines for easier processing
        lines = content.split('\n')
        result_lines = []
        modified = False
        i = 0
        
        while i < len(lines):
            # Check for Key Takeaways heading
            if i < len(lines) and re.match(r'^#+\s+Key\s+Takeaways\s*$', lines[i], re.IGNORECASE):
                # Make sure there's a blank line before the markers if this isn't the first line
                if i > 0 and result_lines and result_lines[-1].strip() != "":
                    result_lines.append("")
                
                # Add the start marker
                result_lines.append("---keytakeaways---")
                
                # Add the Key Takeaways heading
                kt_start_index = i
                result_lines.append(lines[i])  # Add the heading line
                i += 1
                
                # Collect bullet points and content until we hit another heading or run out of content
                content_lines = []
                while i < len(lines) and not lines[i].startswith('#'):
                    # Only add non-empty lines or lines that are part of the content
                    if lines[i].strip() or content_lines:  # Add empty lines only if we've already added content
                        content_lines.append(lines[i])
                    i += 1
                
                # Remove any trailing empty lines
                while content_lines and content_lines[-1].strip() == "":
                    content_lines.pop()
                
                # Add the content lines
                result_lines.extend(content_lines)
                
                # Add the end marker immediately after the last content line (no blank line)
                result_lines.append("---keytakeawaysEND---")
                modified = True
                logger.info(f"Added markers around Key Takeaways section at line {kt_start_index+1} in {file_name}")
                continue  # Skip incrementing i as we've already advanced it in the inner loop
            
            # Add any other line as is
            result_lines.append(lines[i])
            i += 1
        
        # Join the lines back together
        modified_content = '\n'.join(result_lines)
        return modified_content, modified

    def ensure_bullet_list_spacing(self, content, file_path=None):
        """
        Ensure there's a blank line between text and bullet lists for proper HTML formatting.
        
        Args:
            content: The markdown content to process
            file_path: Optional file path for logging
            
        Returns:
            tuple: (modified_content, was_modified)
        """
        file_name = os.path.basename(file_path) if file_path else "unknown"
        logger.info(f"Ensuring spacing before bullet lists in {file_name}")
        
        # Split content into lines
        lines = content.split('\n')
        modified = False
        
        # Process the lines
        i = 0
        while i < len(lines) - 1:
            current_line = lines[i].strip()
            next_line = lines[i+1].strip()
            
            # Check for a line that ends with a colon or other text
            # followed by a bullet point on the next line (without a blank line in between)
            if (current_line and 
                next_line and 
                (next_line.startswith('-') or next_line.startswith('*')) and
                not current_line.startswith('-') and 
                not current_line.startswith('*')):
                
                # Insert a blank line between the text and the bullet list
                lines.insert(i + 1, '')
                modified = True
                logger.info(f"Added spacing before bullet list at line {i+2} in {file_name}")
                i += 1  # Skip the newly added line
            
            i += 1
        
        # Join the lines back together
        modified_content = '\n'.join(lines)
        return modified_content, modified

    def convert_asterisk_to_dash(self, content, file_path=None):
        """
        Convert asterisk bullets (*) to dash bullets (-) while preserving bold formatting.
        
        Args:
            content: The markdown content to process
            file_path: Optional file path for logging
            
        Returns:
            tuple: (modified_content, was_modified)
        """
        file_name = os.path.basename(file_path) if file_path else "unknown"
        logger.info(f"Converting asterisk bullets to dash bullets in {file_name}")
        
        # Split content into lines
        lines = content.split('\n')
        modified = False
        
        # Regular expression to match markdown bullet points that start with asterisk
        # It looks for:  whitespace + asterisk + whitespace + content
        bullet_pattern = re.compile(r'^(\s*)\*(\s+)(.+)$')
        
        # Process each line
        for i in range(len(lines)):
            line = lines[i]
            # Check if this line is a bullet point starting with asterisk
            match = bullet_pattern.match(line)
            if match:
                # Extract the components of the line
                indent = match.group(1)  # Leading whitespace
                space_after_bullet = match.group(2)  # Space after the bullet
                content = match.group(3)  # The actual content
                
                # Replace with dash bullet
                lines[i] = f"{indent}-{space_after_bullet}{content}"
                modified = True
                logger.info(f"Converted asterisk bullet to dash bullet at line {i+1} in {file_name}")
        
        # Join the lines back together
        modified_content = '\n'.join(lines)
        return modified_content, modified

    def fix_indented_lists(self, content, file_path=None):
        """
        Remove extra spacing before list items to ensure proper markdown formatting.
        Fixes patterns like indented list items with 3 or more spaces before the dash.
        
        Args:
            content: The markdown content to process
            file_path: Optional file path for logging
            
        Returns:
            tuple: (modified_content, was_modified)
        """
        file_name = os.path.basename(file_path) if file_path else "unknown"
        logger.info(f"Fixing indented lists in {file_name}")
        
        # Split content into lines
        lines = content.split('\n')
        modified = False
        
        # Regular expression to match indented list items
        # This will match lines with spaces followed by a dash or asterisk
        indented_list_pattern = re.compile(r'^(\s{3,})(-|\*)(\s.+)$')
        
        # Process the lines
        for i in range(len(lines)):
            line = lines[i]
            # Check for indented list items using regex
            match = indented_list_pattern.match(line)
            if match:
                # Replace with proper markdown list formatting (single space after dash/asterisk)
                marker = match.group(2)  # - or *
                content = match.group(3)  # The text after the marker
                lines[i] = f"{marker}{content}"
                modified = True
                logger.info(f"Fixed indented list at line {i+1} in {file_name}")
        
        # Join the lines back together
        modified_content = '\n'.join(lines)
        return modified_content, modified

    def fix_extra_indented_bullets(self, content, file_path=None):
        """
        Removes extra spacing before bullet points that follow text lines.
        Fixes patterns like:
        **Ball Skills**: 
          - Setup: Find a ball...
        
        To become:
        **Ball Skills**: 
        - Setup: Find a ball...
        
        Args:
            content: The markdown content to process
            file_path: Optional file path for logging
            
        Returns:
            tuple: (modified_content, was_modified)
        """
        file_name = os.path.basename(file_path) if file_path else "unknown"
        logger.info(f"Fixing extra indented bullet points in {file_name}")
        
        # Split content into lines for easier processing
        lines = content.split('\n')
        modified = False
        
        # Process each line
        for i in range(len(lines) - 1):
            # Check if current line is text (not a bullet point) and next line is an indented bullet
            current_line = lines[i]
            next_line = lines[i+1]
            
            # Check if next line is an indented bullet point
            bullet_match = re.match(r'^(\s{2,})([-*+]\s.*)', next_line)
            if bullet_match and not current_line.strip().startswith(('-', '*', '+')):
                # Get the indentation and the bullet content
                indentation = bullet_match.group(1)
                bullet_content = bullet_match.group(2)
                
                # Fix the indentation - keep just one space if there was any text on the previous line
                if current_line.strip():  # If previous line has content
                    # Replace with proper bullet format
                    lines[i+1] = "- " + bullet_content.lstrip('-* ').strip()
                    modified = True
                    logger.info(f"Fixed indented bullet at line {i+2} in {file_name}")
        
        # Join the lines back together
        modified_content = '\n'.join(lines)
        return modified_content, modified

    def add_br_tags_at_blank_lines(self, content, file_path=None):
        """
        Adds <br/> tags at blank lines between paragraphs for proper HTML formatting.
        Avoids adding tags before or after headings, lists, code blocks, or other special elements.
        
        Args:
            content: The markdown content to process
            file_path: Optional file path for logging
            
        Returns:
            tuple: (modified_content, was_modified)
        """
        file_name = os.path.basename(file_path) if file_path else "unknown"
        logger.info(f"Adding <br/> tags at blank lines in {file_name}")
        
        # Split content into lines
        lines = content.split('\n')
        modified = False
        result_lines = []
        
        # Process lines
        for i in range(len(lines)):
            current_line = lines[i].strip()
            
            # Add the current line to the result
            result_lines.append(lines[i])
            
            # Check if this is a blank line followed by non-blank line (paragraph break)
            # But don't add <br/> tags at the very end of the document
            if (i < len(lines) - 1 and 
                current_line == "" and 
                lines[i+1].strip() != "" and
                # Avoid adding <br/> before headings, lists, code blocks or existing tags
                not lines[i+1].strip().startswith(('#', '-', '*', '```', '<', '|'))):
                
                # Also avoid adding <br/> tags after headings or list items (previous non-blank line)
                prev_non_blank = None
                for j in range(i-1, -1, -1):
                    if lines[j].strip() != "":
                        prev_non_blank = lines[j].strip()
                        break
                
                # Only add <br/> if previous non-blank line is not a heading or list item
                if (prev_non_blank is None or 
                    not (prev_non_blank.startswith('#') or 
                         prev_non_blank.startswith('-') or 
                         prev_non_blank.startswith('*') or
                         prev_non_blank.startswith('```'))):
                    result_lines.append("<br/>")
                    modified = True
                    logger.info(f"Added <br/> tag after line {i+1} in {file_name}")
        
        # Join the lines back together
        modified_content = '\n'.join(result_lines)
        return modified_content, modified
