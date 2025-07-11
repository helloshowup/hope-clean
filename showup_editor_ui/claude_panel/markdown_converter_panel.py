"""Markdown to HTML Converter Module for ClaudeAIPanel"""

import os
import re
import sys
import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import queue
import traceback

# Import markdown library for conversion
try:
    import markdown
except ImportError:
    logging.error("markdown library not found, attempting to install it")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "markdown"])
    import markdown

# Get logger
logger = logging.getLogger("output_library_editor")


class LoggingHandler(logging.Handler):
    """Custom logging handler that redirects logs to the GUI"""
    
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget
        self.log_queue = queue.Queue()
        self.text_widget.after(100, self.poll_log_queue)
    
    def emit(self, record):
        self.log_queue.put(record)
    
    def poll_log_queue(self):
        """Check for new log records and display them"""
        try:
            while True:
                record = self.log_queue.get_nowait()
                self.text_widget.configure(state="normal")
                self.text_widget.insert("end", self.format(record) + "\n")
                self.text_widget.see("end")
                self.text_widget.configure(state="disabled")
                self.text_widget.update_idletasks()
                self.log_queue.task_done()
        except queue.Empty:
            pass
        self.text_widget.after(100, self.poll_log_queue)


def markdown_to_html(markdown_content: str) -> str:
    """
    Convert Markdown to basic HTML suitable for LMS paste-in with proper paragraph spacing
    and special elements support
    
    Args:
        markdown_content: The markdown content to convert
        
    Returns:
        HTML content with properly formatted elements
    """
    # Extract first heading for display
    first_heading = ""
    heading_pattern = re.compile(r'^\s*#\s+(.*?)\s*$', re.MULTILINE)
    heading_match = heading_pattern.search(markdown_content)
    if heading_match:
        first_heading = heading_match.group(1).strip()
    
    # First handle the audio instructions directly before any other processing
    processed_md = pre_process_audio_instructions(markdown_content)
    
    # Pre-process numbered lists to ensure proper HTML formatting
    processed_md = pre_process_numbered_lists(processed_md)
    
    # Extract special sections (stop and reflect, key takeaways) before conversion
    processed_content, special_sections = extract_special_sections(processed_md)
    
    # Convert markdown to HTML using the markdown library with appropriate extensions
    html_content = markdown.markdown(
        processed_content,
        extensions=['extra', 'sane_lists', 'tables']
    )
    
    # Replace direct styling on headings with span elements for color styling
    # Handle h1 tags
    h1_pattern = r'<h1>(.*?)</h1>'
    h1_matches = re.finditer(h1_pattern, html_content)
    for match in h1_matches:
        original_h1 = match.group(0)
        h1_content = match.group(1)
        styled_h1 = f'<h1>\n    <span style="color:#920205;">{h1_content}</span>\n</h1>'
        html_content = html_content.replace(original_h1, styled_h1)
    
    # Handle h2 Learning Objectives specifically
    h2_learning_obj_pattern = r'(<h2>)(\s*Learning\s*Objectives\s*)(</h2>\s*)(<p>)(.*?)(</p>)(\s*<ul>)(.*?)(</ul>)'
    h2_match = re.search(h2_learning_obj_pattern, html_content, re.DOTALL | re.IGNORECASE)
    
    if h2_match:
        # Get all parts of the pattern
        h2_open = h2_match.group(1)
        h2_content = h2_match.group(2)
        h2_close = h2_match.group(3)
        p_open = h2_match.group(4)
        p_content = h2_match.group(5)
        p_close = h2_match.group(6)
        ul_start = h2_match.group(7)
        list_content = h2_match.group(8)
        ul_end = h2_match.group(9)
        
        # Style with span elements instead of direct styling
        styled_h2 = f'{h2_open}\n    <span style="color:#920205;">{h2_content}</span>\n{h2_close}'
        styled_p = f'{p_open}\n    <span style="color:#920205;">{p_content}</span>\n{p_close}'
        
        # Style list items with spans
        styled_list = re.sub(r'(<li>)(.*?)(</li>)', r'\1\n    <span style="color:#920205;">\2</span>\n\3', list_content)
        
        # Replace the entire section with the styled version
        html_content = html_content.replace(h2_match.group(0), styled_h2 + styled_p + ul_start + styled_list + ul_end)
    else:
        # If that pattern didn't match, try a simpler approach for the h2
        h2_pattern = r'<h2>(\s*Learning\s*Objectives\s*)</h2>'
        h2_match = re.search(h2_pattern, html_content, re.IGNORECASE)
        if h2_match:
            h2_content = h2_match.group(1)
            styled_h2 = f'<h2>\n    <span style="color:#920205;">{h2_content}</span>\n</h2>'
            html_content = html_content.replace(h2_match.group(0), styled_h2)
    
    # Replace special section placeholders with styled HTML
    for placeholder, section_type, section_content in special_sections:
        if section_type == "stop_reflect":
            replacement = create_stop_reflect_html(section_content)
        elif section_type == "key_takeaways":
            replacement = create_key_takeaways_html(section_content)
        elif section_type == "audio_instructions":
            replacement = create_audio_instructions_html(section_content)
        else:
            replacement = section_content
        
        html_content = html_content.replace(placeholder, replacement)
    
    # Construct the final HTML structure
    html_content = f"""
<div class="markdown-content" style="color:#333;font-family:Arial, sans-serif;line-height:1.6;margin:0 auto;max-width:800px;">
    <div class="container" style="margin-left:auto;">
        <div style="color:#333;font-family:Arial, sans-serif;line-height:1.6;">
            <style>
            p {{margin-bottom: 2em;}}
            </style>
            {html_content}
        </div>
    </div>
</div>
"""
    
    # Apply some additional cleanup - remove extra line breaks 
    html_content = re.sub(r'\n\s*\n', '\n', html_content)
    
    return html_content


def apply_learning_objectives_styling(html_content: str) -> str:
    """
    DEPRECATED: No longer needed as we're styling headings directly in markdown_to_html
    """
    return html_content


def extract_special_sections(content: str) -> tuple:
    """
    Extract special sections from markdown content and replace with placeholders
    
    Args:
        content: Original markdown content
        
    Returns:
        Tuple of (processed_content, list of tuples (placeholder, section_type, section_content))
    """
    special_sections = []
    processed_content = content
    
    # Extract Stop and Reflect sections - Markdown heading format
    stop_reflect_pattern = r'(?:\n|^)\s*#{1,3}\s*Stop and Reflect\s*#{0,3}\s*(?:\n|$)(.*?)(?:(?:\n|^)\s*#{1,3}|$)'
    for i, match in enumerate(re.finditer(stop_reflect_pattern, content, re.DOTALL | re.IGNORECASE)):
        placeholder = f"<!-- SPECIAL_SECTION_STOP_REFLECT_{i} -->"
        section_content = match.group(1).strip()
        special_sections.append((placeholder, "stop_reflect", section_content))
        processed_content = processed_content.replace(match.group(0), f"\n{placeholder}\n")
    
    # Extract Stop and Reflect sections - Triple dash format
    triple_dash_stop_reflect_pattern = r'(?:\n|^)\s*---stopandreflect---\s*(?:\n|$)(.*?)(?:(?:\n|^)\s*---stopandreflectEND---|$)'
    for i, match in enumerate(re.finditer(triple_dash_stop_reflect_pattern, content, re.DOTALL | re.IGNORECASE)):
        placeholder = f"<!-- SPECIAL_SECTION_STOP_REFLECT_DASH_{i} -->"
        section_content = match.group(1).strip()
        special_sections.append((placeholder, "stop_reflect", section_content))
        processed_content = processed_content.replace(match.group(0), f"\n{placeholder}\n")
    
    # Extract Key Takeaways sections - Markdown heading format
    key_takeaways_pattern = r'(?:\n|^)\s*#{1,3}\s*Key Takeaways\s*#{0,3}\s*(?:\n|$)(.*?)(?:(?:\n|^)\s*#{1,3}|$)'
    for i, match in enumerate(re.finditer(key_takeaways_pattern, content, re.DOTALL | re.IGNORECASE)):
        placeholder = f"<!-- SPECIAL_SECTION_KEY_TAKEAWAYS_{i} -->"
        section_content = match.group(1).strip()
        special_sections.append((placeholder, "key_takeaways", section_content))
        processed_content = processed_content.replace(match.group(0), f"\n{placeholder}\n")
    
    # Extract Key Takeaways sections - Triple dash format
    triple_dash_key_takeaways_pattern = r'(?:\n|^)\s*---keytakeaways---\s*(?:\n|$)(.*?)(?:(?:\n|^)\s*---keytakeawaysEND---|$)'
    for i, match in enumerate(re.finditer(triple_dash_key_takeaways_pattern, content, re.DOTALL | re.IGNORECASE)):
        placeholder = f"<!-- SPECIAL_SECTION_KEY_TAKEAWAYS_DASH_{i} -->"
        section_content = match.group(1).strip()
        special_sections.append((placeholder, "key_takeaways", section_content))
        processed_content = processed_content.replace(match.group(0), f"\n{placeholder}\n")
    
    # Extract Audio Instructions sections - Markdown heading format
    audio_instructions_pattern = r'(?:\n|^)\s*#{1,3}\s*Audio Instructions\s*#{0,3}\s*(?:\n|$)(.*?)(?:(?:\n|^)\s*#{1,3}|$)'
    for i, match in enumerate(re.finditer(audio_instructions_pattern, content, re.DOTALL | re.IGNORECASE)):
        placeholder = f"<!-- SPECIAL_SECTION_AUDIO_INSTRUCTIONS_{i} -->"
        section_content = match.group(1).strip()
        special_sections.append((placeholder, "audio_instructions", section_content))
        processed_content = processed_content.replace(match.group(0), f"\n{placeholder}\n")
    
    # Extract Audio Instructions sections - Triple dash format
    triple_dash_audio_instructions_pattern = r'(?:\n|^)\s*---audioinstructions---\s*(?:\n|$)(.*?)(?:(?:\n|^)\s*---audioinstructionsEND---|$)'
    for i, match in enumerate(re.finditer(triple_dash_audio_instructions_pattern, content, re.DOTALL | re.IGNORECASE)):
        placeholder = f"<!-- SPECIAL_SECTION_AUDIO_INSTRUCTIONS_DASH_{i} -->"
        section_content = match.group(1).strip()
        special_sections.append((placeholder, "audio_instructions", section_content))
        processed_content = processed_content.replace(match.group(0), f"\n{placeholder}\n")
    
    return processed_content, special_sections


def create_stop_reflect_html(content: str) -> str:
    """
    Create HTML for Stop and Reflect sections
    
    Args:
        content: The markdown content of the section
        
    Returns:
        Formatted HTML
    """
    # Convert the content markdown to HTML
    content_html = markdown.markdown(content, extensions=['extra', 'nl2br'])
    
    # Create the styled layout with image and dashed border
    styled_html = f"""
<div class="stop-reflect-container" style="border:3px dashed #e50200;display:flex;margin:20px 0;padding:0;width:100%;">
        <div class="stop-reflect-image" style="align-items:center;display:flex;justify-content:center;min-width:100px;padding:10px;width:20%;">
            <img class="image_resized" style="height:auto;max-width:150px;width:100%;" src="https://api.learnstage.com/media-manager/api/access/exceled/default/lms/courses/1648/Images/stopandreflect.jpg" alt="Stop and Reflect">
        </div>
        <div class="stop-reflect-content" style="display:flex;flex-direction:column;justify-content:center;padding:15px;width:80%;">
            {content_html}
        </div>
    </div>
    """
    
    return styled_html


def create_key_takeaways_html(content: str) -> str:
    """
    Create HTML for Key Takeaways sections with red/crimson styling
    
    Args:
        content: The markdown content of the section
        
    Returns:
        Formatted HTML
    """
    # Check if the content already contains a Key Takeaways table structure
    # to prevent double formatting
    if '<figure class="table"' in content and 'Key Takeaways' in content:
        # Content already has Key Takeaways formatting, return as is
        return content
        
    # Remove any heading that contains "Key Takeaways" from the content
    content = re.sub(r'#+\s*Key\s*Takeaways\s*.*?\n', '', content, flags=re.IGNORECASE)
    
    # Convert the cleaned content to HTML
    content_html = markdown.markdown(content, extensions=['extra', 'sane_lists'])
    
    # Create the styled table layout with image
    takeaways_html = f"""
<figure class="table" style="float:left;width:92.41%;">
        <table class="ck-table-resized" style="border-style:none;">
            <colgroup><col style="width:13.29%;"><col style="width:86.71%;"></colgroup>
            <tbody>
                <tr>
                    <td style="border-style:none;">
                        <figure class="image image_resized" style="width:100%;">
                            <img style="aspect-ratio:600/600;" src="https://api.learnstage.com/media-manager/api/access/exceled/default/89309a11-e6ae-4133-97a9-93c735f38be4/content-page/4e85aa67-83db-423a-b7de-53b356164071_removalai_preview.png" width="600" height="600">
                        </figure>
                    </td>
                    <td style="border-style:none;">
                        <h3>
                            <span style="color:hsl(359,97%,29%);"><strong>Key Takeaways</strong></span>
                        </h3>
                        {content_html}
                    </td>
                </tr>
            </tbody>
        </table>
    </figure>
    """
    
    return takeaways_html


def create_audio_instructions_html(content: str) -> str:
    """
    Create HTML for Audio Instructions sections with an audio player
    
    Args:
        content: The markdown content of the section
        
    Returns:
        Formatted HTML with audio controls
    """
    # Parse the content to extract title and audio URL
    lines = content.strip().split('\n')
    title = ""
    audio_url = ""
    
    # Extract title and URL from content
    for line in lines:
        if line.startswith('###') or line.startswith('#'):
            # Extract title without the markdown heading symbols
            title = re.sub(r'^#+\s*', '', line).replace('Audio Instructions:', 'Lesson Podcast Discussion:')
        elif 'http' in line and ('.mp3' in line or '.wav' in line or '.ogg' in line):
            # Extract the URL - clean up any line breaks or extra text
            url_match = re.search(r'(https?://[^\s<>"]+\.(?:mp3|wav|ogg))', line)
            if url_match:
                audio_url = url_match.group(1)
    
    # If no title was found, use a default
    if not title:
        title = "Lesson Podcast Discussion"
    
    # Create the HTML with audio controls
    styled_html = f"""
<h3>
    <span style="color:#000000;">{title}</span> <audio controls="">
        <source src="{audio_url}" type="audio/mpeg"> 
        Your browser does not support the audio element.
      </audio>
</h3>
    """
    
    return styled_html


class MarkdownConverterPanel:
    """Handles markdown to HTML conversion for the ClaudeAIPanel."""
    
    def __init__(self, parent):
        """
        Initialize the markdown converter panel.
        
        Args:
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        self.is_converting = False
        self.files_to_convert = []
        self.output_dir = None
        self.conversion_thread = None
        
    def setup_converter_tab(self):
        """Set up the markdown to HTML converter tab."""
        # Use the existing tab from the parent instead of creating a new one
        tab = self.parent.md_to_html_tab
        
        # Set up main frame with padding
        main_frame = ttk.Frame(tab, padding="10 10 10 10")
        main_frame.pack(fill="both", expand=True)
        
        # Set up left side (controls)
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Files section
        files_frame = ttk.LabelFrame(left_frame, text="Files to Convert")
        files_frame.pack(fill="x", expand=False, pady=(0, 10))
        
        self.file_count_var = tk.StringVar(value="No files selected")
        file_count_label = ttk.Label(files_frame, textvariable=self.file_count_var)
        file_count_label.pack(pady=5, padx=5, anchor="w")
        
        select_btn = ttk.Button(
            files_frame, 
            text="Select Files from Library", 
            command=self.convert_selected_files
        )
        select_btn.pack(fill="x", padx=5, pady=5)
        
        # Options section
        options_frame = ttk.LabelFrame(left_frame, text="Conversion Options")
        options_frame.pack(fill="x", expand=False, pady=(0, 10))
        
        # Output directory
        dir_frame = ttk.Frame(options_frame)
        dir_frame.pack(fill="x", padx=5, pady=5)
        
        self.output_dir_var = tk.StringVar()
        ttk.Label(dir_frame, text="Output Directory:").pack(side="left")
        ttk.Entry(dir_frame, textvariable=self.output_dir_var, width=30).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(dir_frame, text="Browse...", command=self.select_output_directory).pack(side="left")
        
        # Combine output option
        self.combine_var = tk.BooleanVar(value=False)
        combine_cb = ttk.Checkbutton(
            options_frame, 
            text="Combine all files into one HTML file", 
            variable=self.combine_var
        )
        combine_cb.pack(anchor="w", padx=5, pady=5)
        
        # Open output option
        self.open_output_var = tk.BooleanVar(value=True)
        open_cb = ttk.Checkbutton(
            options_frame, 
            text="Open output files when done", 
            variable=self.open_output_var
        )
        open_cb.pack(anchor="w", padx=5, pady=5)
        
        # Conversion actions
        actions_frame = ttk.Frame(left_frame)
        actions_frame.pack(fill="x", pady=10)
        
        self.convert_btn = ttk.Button(
            actions_frame, 
            text="Convert to HTML", 
            command=self.start_conversion, 
            state=tk.DISABLED
        )
        self.convert_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        self.cancel_btn = ttk.Button(
            actions_frame, 
            text="Cancel", 
            command=self.cancel_conversion, 
            state=tk.DISABLED
        )
        self.cancel_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # Progress section
        progress_frame = ttk.LabelFrame(left_frame, text="Progress")
        progress_frame.pack(fill="x", expand=False)
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        status_label.pack(pady=5, padx=5, anchor="w")
        
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", padx=5, pady=5)
        
        # Set up right side (log)
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        log_frame = ttk.LabelFrame(right_frame, text="Conversion Log")
        log_frame.pack(fill="both", expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=20)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_text.config(state="disabled")
        
        # Set up a custom handler for the logger
        log_handler = LoggingHandler(self.log_text)
        log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        log_handler.setLevel(logging.INFO)
        logger.addHandler(log_handler)
    
    def convert_selected_files(self):
        """Process the files selected in the main library panel for MD to HTML conversion."""
        # Get selected files from the file tree
        selected_items = self.parent.file_tree.selection()
        
        if not selected_items:
            messagebox.showinfo("No Files Selected", "Please select one or more files from the library.")
            return
        
        # Get file paths from selected items
        self.files_to_convert = []
        for item in selected_items:
            item_text = self.parent.file_tree.item(item, "text")
            item_values = self.parent.file_tree.item(item, "values")
            
            # Check if this is a file (not a directory) and ends with .md
            if len(item_values) > 0 and item_text.lower().endswith(".md"):
                full_path = item_values[0]
                self.files_to_convert.append(full_path)
        
        if not self.files_to_convert:
            messagebox.showinfo("No Markdown Files", "No markdown files were selected. Please select files with .md extension.")
            return
        
        # Update the UI
        self.update_file_list()
        self.convert_btn.config(state=tk.NORMAL)
        
        # Set default output directory to the location of the first file
        if self.files_to_convert and not self.output_dir_var.get():
            default_dir = os.path.dirname(self.files_to_convert[0])
            self.output_dir_var.set(default_dir)
    
    def update_file_list(self):
        """Update the file count label."""
        if not self.files_to_convert:
            self.file_count_var.set("No files selected")
        elif len(self.files_to_convert) == 1:
            self.file_count_var.set(f"1 file selected: {os.path.basename(self.files_to_convert[0])}")
        else:
            self.file_count_var.set(f"{len(self.files_to_convert)} files selected")
    
    def select_output_directory(self):
        """Open directory dialog to select output directory"""
        # Start with current dir or last selected dir
        initial_dir = self.output_dir_var.get() or os.getcwd()
        
        # Open directory selection dialog
        output_dir = filedialog.askdirectory(initialdir=initial_dir)
        
        # Update the entry if a directory was selected
        if output_dir:
            self.output_dir_var.set(output_dir)
    
    def start_conversion(self):
        """Start the batch conversion process"""
        # Validate we have files and an output directory
        if not self.files_to_convert:
            messagebox.showerror("Error", "No files selected for conversion.")
            return
        
        output_dir = self.output_dir_var.get()
        if not output_dir:
            messagebox.showerror("Error", "Please select an output directory.")
            return
        
        # Make sure output directory exists
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create output directory: {str(e)}")
                return
        
        # Update UI
        self.is_converting = True
        self.convert_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress_bar.config(value=0)
        self.update_status("Starting conversion...")
        
        # Start conversion in a separate thread
        self.conversion_thread = threading.Thread(
            target=self.run_conversion,
            args=(
                self.files_to_convert,
                output_dir,
                self.combine_var.get(),
                self.open_output_var.get()
            )
        )
        self.conversion_thread.daemon = True
        self.conversion_thread.start()
    
    def run_conversion(self, files, output_dir, combine_output, open_output):
        """Run the batch conversion process in a separate thread"""
        try:
            # Initialize variables
            converted_files = []
            total_files = len(files)
            combined_html = "" if combine_output else None
            combined_filename = None
            current_file_count = 0
            
            # Process each file
            for file_path in files:
                # Check if conversion was cancelled
                if not self.is_converting:
                    self.parent.after(0, lambda: self.update_status("Conversion cancelled."))
                    break
                
                # Get the basename and update status
                basename = os.path.basename(file_path)
                self.update_status(f"Converting {basename}...")
                logger.info(f"Converting {basename}")
                
                try:
                    # Read the markdown file
                    with open(file_path, 'r', encoding='utf-8') as md_file:
                        markdown_content = md_file.read()
                    
                    # Convert to HTML
                    html_content = markdown_to_html(markdown_content)
                    
                    # If combining output, append to combined HTML
                    if combine_output:
                        if not combined_filename:
                            # Use the first file's name as the base for the combined file
                            combined_filename = os.path.splitext(basename)[0] + "_combined.html"
                        
                        # Add a section heading for this file
                        file_title = os.path.splitext(basename)[0]
                        combined_html += f"<h1 style='margin-top:30px;border-top:1px solid #ccc;padding-top:20px;'>{file_title}</h1>\n{html_content}\n\n"
                    else:
                        # Create output HTML file
                        output_filename = os.path.splitext(basename)[0] + ".html"
                        output_path = os.path.join(output_dir, output_filename)
                        
                        with open(output_path, 'w', encoding='utf-8') as html_file:
                            html_file.write(html_content)
                        
                        converted_files.append(output_path)
                        logger.info(f"Created {output_filename}")
                    
                    # Update progress
                    current_file_count += 1
                    progress = int((current_file_count / total_files) * 100)
                    self.update_progress(progress)
                    
                except Exception as e:
                    logger.error(f"Error converting {basename}: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # If combining output, write the combined file
            if combine_output and combined_filename and self.is_converting:
                combined_output_path = os.path.join(output_dir, combined_filename)
                with open(combined_output_path, 'w', encoding='utf-8') as combined_file:
                    combined_file.write(combined_html)
                
                converted_files = [combined_output_path]
                logger.info(f"Created combined file: {combined_filename}")
            
            # Final status update
            if self.is_converting:
                if current_file_count == total_files:
                    self.update_status(f"Conversion complete. {current_file_count} files converted.")
                    logger.info(f"Conversion complete. {current_file_count} files converted.")
                    
                    # Open the output files if requested
                    if open_output and converted_files:
                        for output_file in converted_files:
                            # Open the file with the default application
                            self.update_status(f"Opening {os.path.basename(output_file)}...")
                            try:
                                if sys.platform == 'win32':
                                    os.startfile(output_file)
                                elif sys.platform == 'darwin':  # macOS
                                    subprocess.run(['open', output_file])
                                else:  # Linux
                                    subprocess.run(['xdg-open', output_file])
                            except Exception as e:
                                logger.error(f"Error opening file: {str(e)}")
            
            # Reset UI
            self.parent.after(0, self.reset_ui)
            
        except Exception as e:
            logger.error(f"Conversion error: {str(e)}")
            logger.error(traceback.format_exc())
            self.update_status(f"Error: {str(e)}")
            self.parent.after(0, self.reset_ui)
    
    def update_status(self, message):
        """Update status label from any thread"""
        self.parent.after(0, lambda: self.status_var.set(message))
    
    def update_progress(self, value):
        """Update progress bar from any thread"""
        self.parent.after(0, lambda: self.progress_bar.config(value=value))
    
    def reset_ui(self):
        """Reset UI after conversion"""
        self.is_converting = False
        self.convert_btn.config(state=tk.NORMAL)
        self.cancel_btn.config(state=tk.DISABLED)
    
    def cancel_conversion(self):
        """Cancel the ongoing batch conversion"""
        if self.is_converting:
            self.is_converting = False
            self.update_status("Cancelling conversion...")
            logger.info("User cancelled conversion")


def pre_process_audio_instructions(markdown_content: str) -> str:
    """
    Pre-process audio instructions to directly replace them with HTML audio players
    
    Args:
        markdown_content: The markdown content to process
        
    Returns:
        Processed markdown content with audio sections replaced
    """
    processed_content = markdown_content
    
    # Extract Audio Instructions sections - Triple dash format
    triple_dash_audio_pattern = r'(?:\n|^)\s*---audioinstructions---\s*(?:\n|$)(.*?)(?:(?:\n|^)\s*---audioinstructionsEND---|$)'
    for i, match in enumerate(re.finditer(triple_dash_audio_pattern, processed_content, re.DOTALL | re.IGNORECASE)):
        section_content = match.group(1).strip()
        
        # Extract title and URL from content
        lines = section_content.strip().split('\n')
        title = ""
        audio_url = ""
        
        for line in lines:
            if line.startswith('###') or line.startswith('#'):
                # Extract title without markdown heading symbols
                title = re.sub(r'^#+\s*', '', line).replace('Audio Instructions:', 'Lesson Podcast Discussion:')
            elif 'http' in line and ('.mp3' in line or '.wav' in line or '.ogg' in line):
                # Extract the URL - clean up any line breaks or extra text
                url_match = re.search(r'(https?://[^\s<>"]+\.(?:mp3|wav|ogg))', line)
                if url_match:
                    audio_url = url_match.group(1)
        
        # If no title was found, use a default
        if not title:
            title = "Lesson Podcast Discussion"
        
        # Create the HTML with audio controls
        audio_html = f"""
<h3>
    <span style="color:#000000;">{title}</span> <audio controls="">
        <source src="{audio_url}" type="audio/mpeg"> 
        Your browser does not support the audio element.
      </audio>
</h3>
        """
        
        # Replace the entire audio section with the HTML
        processed_content = processed_content.replace(match.group(0), audio_html)
    
    # Extract Stop and Reflect sections - Triple dash format
    triple_dash_reflect_pattern = r'(?:\n|^)\s*---stopandreflect---\s*(?:\n|$)(.*?)(?:(?:\n|^)\s*---stopandreflectEND---|$)'
    for i, match in enumerate(re.finditer(triple_dash_reflect_pattern, processed_content, re.DOTALL | re.IGNORECASE)):
        section_content = match.group(1).strip()
        content_html = markdown.markdown(section_content, extensions=['extra', 'nl2br'])
        
        # Create the styled layout with image and dashed border
        reflect_html = f"""
<div class="stop-reflect-container" style="border:3px dashed #e50200;display:flex;margin:20px 0;padding:0;width:100%;">
        <div class="stop-reflect-image" style="align-items:center;display:flex;justify-content:center;min-width:100px;padding:10px;width:20%;">
            <img class="image_resized" style="height:auto;max-width:150px;width:100%;" src="https://api.learnstage.com/media-manager/api/access/exceled/default/lms/courses/1648/Images/stopandreflect.jpg" alt="Stop and Reflect">
        </div>
        <div class="stop-reflect-content" style="display:flex;flex-direction:column;justify-content:center;padding:15px;width:80%;">
            {content_html}
        </div>
    </div>
        """
        
        # Replace the entire section with the HTML
        processed_content = processed_content.replace(match.group(0), reflect_html)
    
    # Extract Key Takeaways sections - Triple dash format
    triple_dash_takeaways_pattern = r'(?:\n|^)\s*---keytakeaways---\s*(?:\n|$)(.*?)(?:(?:\n|^)\s*---keytakeawaysEND---|$)'
    for i, match in enumerate(re.finditer(triple_dash_takeaways_pattern, processed_content, re.DOTALL | re.IGNORECASE)):
        section_content = match.group(1).strip()
        
        # Remove any heading that contains "Key Takeaways" from the content
        section_content = re.sub(r'#+\s*Key\s*Takeaways\s*.*?\n', '', section_content, flags=re.IGNORECASE)
        
        # Convert the cleaned content to HTML
        content_html = markdown.markdown(section_content, extensions=['extra', 'nl2br'])
        
        # Create the styled table layout with image
        takeaways_html = f"""
<figure class="table" style="float:left;width:92.41%;">
        <table class="ck-table-resized" style="border-style:none;">
            <colgroup><col style="width:13.29%;"><col style="width:86.71%;"></colgroup>
            <tbody>
                <tr>
                    <td style="border-style:none;">
                        <figure class="image image_resized" style="width:100%;">
                            <img style="aspect-ratio:600/600;" src="https://api.learnstage.com/media-manager/api/access/exceled/default/89309a11-e6ae-4133-97a9-93c735f38be4/content-page/4e85aa67-83db-423a-b7de-53b356164071_removalai_preview.png" width="600" height="600">
                        </figure>
                    </td>
                    <td style="border-style:none;">
                        <h3>
                            <span style="color:hsl(359,97%,29%);"><strong>Key Takeaways</strong></span>
                        </h3>
                        {content_html}
                    </td>
                </tr>
            </tbody>
        </table>
    </figure>
        """
        
        # Replace the entire section with the HTML
        processed_content = processed_content.replace(match.group(0), takeaways_html)
    
    return processed_content


def pre_process_numbered_lists(markdown_content: str) -> str:
    """
    Process numbered lists to ensure proper HTML formatting.
    This function no longer escapes numbered lists, allowing them to be properly
    converted to HTML ordered lists (<ol> elements).
    
    Args:
        markdown_content: The markdown content to process
        
    Returns:
        Processed markdown content with proper list formatting
    """
    # Simply return the content unchanged to allow the markdown processor
    # to handle numbered lists properly
    return markdown_content
