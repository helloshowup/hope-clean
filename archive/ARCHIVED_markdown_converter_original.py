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
from datetime import datetime
import shutil
import openai

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
    Convert Markdown to HTML using OpenAI's API for optimal formatting of list elements.
    
    Special syntax:
    - Use '---pagebreak---' on its own line to insert a page break.
    - Use '---stopandreflect---' and '---stopandreflectEND---' markers to create a Stop and Reflect box.
      All content between these markers will be included in the box.
    - Use '---checkyourunderstanding---' and '---checkyourunderstandingEND---' to create a
      "Check your understanding" quiz box with green styling and reveal functionality.
      Add correct answers between '---answer---' and '---answerEND---' markers.
    - Use '---keytakeaways---' and '---keytakeawaysEND---' to create a Key Takeaways box.
    - Use **CHECKPOINT:** followed by text to create a checkpoint section.
      
    Args:
        markdown_content: Markdown content to convert
        
    Returns:
        HTML content with proper paragraph breaks and special elements
    """
    if not markdown_content:
        return ""
    
    # First, normalize line endings
    normalized_content = markdown_content.replace('\r\n', '\n')
    
    # Extract special content before processing paragraphs
    stop_reflect_matches = []
    check_understanding_matches = []
    key_takeaways_matches = []
    special_placeholders = {}
    
    # Extract the title - look for the first two lines
    lines = normalized_content.split('\n')
    has_custom_title = False
    title_html = ""
    
    if len(lines) >= 2 and lines[0].startswith('#') and lines[1].startswith('#'):
        # Extract module number and title
        module_number = lines[0].lstrip('#').strip()
        module_title = lines[1].lstrip('#').strip()
        
        # Remove title lines from content
        lines = lines[2:]
        normalized_content = '\n'.join(lines)
        
        # Create custom title HTML
        title_html = f'<h1 style="color: #910204;">{module_number}<br>{module_title}</h1>'
        has_custom_title = True
    
    # Find all stop and reflect sections and replace with placeholders
    stop_reflect_pattern = r'---stopandreflect---(.*?)---stopandreflectEND---'
    for i, match in enumerate(re.findall(stop_reflect_pattern, normalized_content, re.DOTALL)):
        placeholder = f"SPECIAL_PLACEHOLDER_SR_{i}"
        stop_reflect_matches.append((placeholder, match.strip()))
        # Replace in the normalized content
        section = f"---stopandreflect---{match}---stopandreflectEND---"
        normalized_content = normalized_content.replace(section, placeholder)
    
    # Process Check Your Understanding sections
    check_pattern = r'---checkyourunderstanding---(.*?)---checkyourunderstandingEND---'
    for i, match in enumerate(re.findall(check_pattern, normalized_content, re.DOTALL)):
        # Extract the answer section if it exists
        answer_pattern = r'---answer---(.*?)---answerEND---'
        answer_matches = re.findall(answer_pattern, match, re.DOTALL)
        answer_text = answer_matches[0].strip() if answer_matches else ""
        
        # Remove the answer section from the main content
        main_content = re.sub(answer_pattern, '', match, flags=re.DOTALL).strip()
        
        # Create a placeholder
        placeholder = f"SPECIAL_PLACEHOLDER_CU_{i}"
        check_understanding_matches.append((placeholder, main_content, answer_text, i))
        
        # Replace in the normalized content
        section = f"---checkyourunderstanding---{match}---checkyourunderstandingEND---"
        normalized_content = normalized_content.replace(section, placeholder)
    
    # Process Key Takeaways sections
    key_takeaways_pattern = r'---keytakeaways---(.*?)---keytakeawaysEND---'
    for i, match in enumerate(re.findall(key_takeaways_pattern, normalized_content, re.DOTALL)):
        placeholder = f"SPECIAL_PLACEHOLDER_KT_{i}"
        key_takeaways_matches.append((placeholder, match.strip()))
        # Replace in the normalized content
        section = f"---keytakeaways---{match}---keytakeawaysEND---"
        normalized_content = normalized_content.replace(section, placeholder)
    
    # Process page breaks
    normalized_content = re.sub(r'\n---pagebreak---\n', r'<hr class="pagebreak" style="page-break-after: always;">', normalized_content)
    
    # Convert to HTML using OpenAI API
    try:
        html_content = convert_with_openai(normalized_content)
    except Exception as e:
        logger.error(f"Error in OpenAI conversion: {str(e)}")
        # Fallback to markdown library
        md = markdown.Markdown(extensions=['tables', 'fenced_code', 'extra', 'sane_lists'])
        html_content = md.convert(normalized_content)
    
    # Find and format all Learning Objectives headers
    # This will find any heading that contains 'Learning Objectives' regardless of level
    learning_obj_pattern = r'<h[1-6]>(.*?Learning\s+Objectives.*?)</h[1-6]>'
    learning_obj_matches = re.findall(learning_obj_pattern, html_content, re.IGNORECASE | re.DOTALL)
    
    # Replace all instances with properly formatted h3
    for match in learning_obj_matches:
        # Remove any existing bold formatting if present
        cleaned_text = re.sub(r'<strong>(.*?)</strong>', r'\1', match)
        # Create properly formatted h3 with burgundy color and underline
        formatted_h3 = f'<h3 class="learning-objectives" style="color: #910204; text-decoration: underline;">{cleaned_text}</h3>'
        # Replace in the HTML content
        html_content = html_content.replace(f'<h1>{match}</h1>', formatted_h3)
        html_content = html_content.replace(f'<h2>{match}</h2>', formatted_h3)
        html_content = html_content.replace(f'<h3>{match}</h3>', formatted_h3)
        html_content = html_content.replace(f'<h4>{match}</h4>', formatted_h3)
        html_content = html_content.replace(f'<h5>{match}</h5>', formatted_h3)
        html_content = html_content.replace(f'<h6>{match}</h6>', formatted_h3)
    
    # Add container and CSS
    container_start = '<div class="container" style="margin:auto;max-width:750px;padding-bottom:4em;padding-left:1em;padding-right:1em;">'
    css = '''
        <style>
            h1 {color: #910204;}
            h3.learning-objectives {color: #910204; text-decoration: underline;}
        </style>
    '''
    
    # Add the custom title at the beginning if extracted
    if has_custom_title:
        html_content = container_start + css + title_html + html_content + '</div>'
    else:
        html_content = container_start + css + html_content + '</div>'
    
    # Replace placeholders with actual content
    
    # Replace Stop and Reflect boxes
    for placeholder, content in stop_reflect_matches:
        # Use OpenAI to convert the content inside to HTML
        try:
            inner_html = convert_with_openai(content)
        except Exception:
            # Fallback to markdown library
            md = markdown.Markdown(extensions=['tables', 'fenced_code', 'extra', 'sane_lists'])
            inner_html = md.convert(content)
        
        # Check if this is a checkpoint (contains **CHECKPOINT:**)
        is_checkpoint = "**CHECKPOINT:**" in content
        
        if is_checkpoint:
            # Process the content to remove the checkpoint header
            inner_html = inner_html.replace('<p><strong>CHECKPOINT:</strong>', '<p>')
            
            # For CHECKPOINT, use the standardized styling with empty heading
            reflect_box = f'''
            <div class="stop-reflect-container" style="border:3px dashed #e50200; margin:20px 0; padding:0; display:flex; width:100%;">
                <div class="stop-reflect-image" style="width:20%; min-width:100px; display:flex; align-items:center; justify-content:center; padding:10px;">
                    <img src="https://api.learnstage.com/media-manager/api/access/exceled/default/lms/courses/1647/Images/Untitled%20design.jpg" 
                         style="width:100%; height:auto; max-width:150px;" alt="Stop and Reflect">
                </div>
                <div class="stop-reflect-content" style="display:flex; flex-direction:column; justify-content:center; padding:15px; width:80%;">
                    <h3 style="color:#000000; margin-top:0;">
                    </h3>
                    {inner_html}
                </div>
            </div>'''
        else:
            # For regular Stop and Reflect, use the standardized styling
            reflect_box = f'''
            <div class="stop-reflect-container" style="border:3px dashed #e50200; margin:20px 0; padding:0; display:flex; width:100%;">
                <div class="stop-reflect-image" style="width:20%; min-width:100px; display:flex; align-items:center; justify-content:center; padding:10px;">
                    <img src="https://api.learnstage.com/media-manager/api/access/exceled/default/lms/courses/1647/Images/Untitled%20design.jpg" 
                         style="width:100%; height:auto; max-width:150px;" alt="Stop and Reflect">
                </div>
                <div class="stop-reflect-content" style="display:flex; flex-direction:column; justify-content:center; padding:15px; width:80%;">
                    <h3 style="color:#000000; margin-top:0;">
                        Stop and Reflect
                    </h3>
                    {inner_html}
                </div>
            </div>'''
        
        html_content = html_content.replace(placeholder, reflect_box)
    
    # Replace Check Your Understanding boxes
    for placeholder, content, answer, index in check_understanding_matches:
        # Convert the content inside to HTML
        try:
            inner_html = convert_with_openai(content)
            answer_html = convert_with_openai(answer) if answer else ""
        except Exception:
            # Fallback to markdown library
            md = markdown.Markdown(extensions=['tables', 'fenced_code', 'extra', 'sane_lists'])
            inner_html = md.convert(content)
            answer_html = md.convert(answer) if answer else ""
        
        # Create the HTML for the Check Your Understanding box
        check_html = f'''
        <div class="check-understanding" style="border:1px solid #ccc; background-color:#f9f9f9; margin:20px 0; padding:15px; border-radius:5px;">
            <h3 style="color:#006400; margin-top:0;">Check Your Understanding</h3>
            {inner_html}
            <div class="answer-container" style="margin-top:15px;">
                <button onclick="toggleAnswer{index}()" class="reveal-btn" style="background-color:#4CAF50; color:white; border:none; padding:8px 16px; text-align:center; text-decoration:none; display:inline-block; font-size:14px; margin:4px 2px; cursor:pointer; border-radius:4px;">Reveal Answer</button>
                <div id="answer{index}" class="answer" style="display:none; margin-top:10px; padding:10px; background-color:#e8f5e9; border-left:4px solid #4CAF50;">
                    {answer_html}
                </div>
            </div>
            <script>
                function toggleAnswer{index}() {{
                    var answerDiv = document.getElementById("answer{index}");
                    var displayStyle = answerDiv.style.display;
                    if (displayStyle === "none") {{
                        answerDiv.style.display = "block";
                    }} else {{
                        answerDiv.style.display = "none";
                    }}
                }}
            </script>
        </div>'''
        
        html_content = html_content.replace(placeholder, check_html)
    
    # Replace Key Takeaways boxes
    for placeholder, content in key_takeaways_matches:
        # Convert the content inside to HTML
        try:
            inner_html = convert_with_openai(content)
        except Exception:
            # Fallback to markdown library
            md = markdown.Markdown(extensions=['tables', 'fenced_code', 'extra', 'sane_lists'])
            inner_html = md.convert(content)
        
        # Create the HTML for the Key Takeaways box
        takeaways_html = f'''
        <figure class="table" style="float:left;width:92.41%;" data-font-size="14" data-line-height="20">
            <table class="ck-table-resized" style="border-style:none;" data-font-size="14" data-line-height="20">
                <colgroup data-font-size="14" data-line-height="20"><col style="width:13.29%;" data-font-size="14" data-line-height="20"><col style="width:86.71%;" data-font-size="14" data-line-height="20"></colgroup>
                <tbody data-font-size="14" data-line-height="20">
                    <tr data-font-size="14" data-line-height="20">
                        <td style="border-style:none;" data-font-size="14" data-line-height="20">
                            <figure class="image image_resized" style="width:100%;" data-font-size="14" data-line-height="20">
                                <img style="aspect-ratio:600/600;" src="https://api.learnstage.com/media-manager/api/access/exceled/default/89309a11-e6ae-4133-97a9-93c735f38be4/content-page/4e85aa67-83db-423a-b7de-53b356164071_removalai_preview.png" width="600" height="600" data-font-size="14" data-line-height="20">
                            </figure>
                        </td>
                        <td style="border-style:none;" data-font-size="14" data-line-height="20">
                            <h3 data-font-size="16" data-line-height="23">
                                <span style="color:hsl(359,97%,29%);"><span data-font-size="16" data-line-height="23"><strong data-font-size="16" data-line-height="23">Key Takeaways</strong></span></span>
                            </h3>
                            {inner_html}
                        </td>
                    </tr>
                </tbody>
            </table>
        </figure>'''
        
        html_content = html_content.replace(placeholder, takeaways_html)
    
    return html_content


def convert_with_openai(markdown_text: str) -> str:
    """Convert markdown to HTML using OpenAI API with specific instructions for proper list handling."""
    try:
        # Initialize the OpenAI client
        client = openai.OpenAI()
        
        # Create the prompt with specific instructions for proper list handling
        prompt = f"""
        Convert the following Markdown text to HTML. Pay special attention to:
        
        1. Properly format lists (both ordered and unordered) according to HTML standards
        2. Ensure nested lists maintain proper hierarchical structure
        3. Group consecutive list items in a single <ul> or <ol> element
        4. Convert mixed list types correctly (ordered vs unordered)
        5. Maintain proper indentation for nested lists
        6. Handle cases where list items have paragraphs within them
        7. Preserve all Markdown formatting (bold, italic, links, etc.)
        8. Preserve code blocks and inline code
        
        Format the HTML cleanly without adding extra markup or CSS styles.
        Only return the HTML output, nothing else.
        
        Markdown content:
        ```
        {markdown_text}
        ```
        """
        
        # Call the OpenAI API
        response = client.chat.completions.create(
            model="gpt-4",  # Use the best model available for accurate HTML conversion
            messages=[
                {"role": "system", "content": "You are an expert markdown-to-HTML converter with perfect knowledge of HTML standards."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for more deterministic output
            max_tokens=2048  # Adjust based on expected size of converted HTML
        )
        
        # Extract HTML from the response
        html_content = response.choices[0].message.content.strip()
        
        # Remove any markdown code block wrappers if they exist
        html_content = re.sub(r'^```html\s*', '', html_content)
        html_content = re.sub(r'\s*```$', '', html_content)
        
        return html_content
    
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise


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
        tab = self.parent.md_to_html_tab
        
        # Main frame for all controls
        main_frame = ttk.Frame(tab, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title label
        title_label = ttk.Label(main_frame, text="Batch Markdown to HTML Converter", font=("Arial", 12, "bold"))
        title_label.pack(pady=(10, 15))
        
        # Configuration frame
        config_frame = ttk.LabelFrame(main_frame, text="Conversion Settings", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Instructions
        instructions = ttk.Label(config_frame, 
                           text="Select markdown files in the library panel and use the 'Convert Selected Files' button below.")
        instructions.pack(anchor="w", padx=5, pady=5)
        
        # File count status
        self.file_count_label = ttk.Label(config_frame, text="0 files selected for conversion")
        self.file_count_label.pack(anchor=tk.W, pady=5)
        
        # Output directory selection
        output_dir_frame = ttk.Frame(config_frame)
        output_dir_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(output_dir_frame, text="Output Directory:").pack(side=tk.LEFT, padx=5)
        
        self.output_dir_var = tk.StringVar()
        output_entry = ttk.Entry(output_dir_frame, textvariable=self.output_dir_var, width=50)
        output_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        select_output_btn = ttk.Button(output_dir_frame, text="Browse", 
                                     command=self.select_output_directory)
        select_output_btn.pack(side=tk.LEFT, padx=5)
        
        # Additional options
        options_frame = ttk.Frame(config_frame)
        options_frame.pack(fill=tk.X, pady=5)
        
        # Combine output option
        self.combine_output_var = tk.BooleanVar(value=False)
        combine_check = ttk.Checkbutton(options_frame, text="Combine all files into one output", 
                                      variable=self.combine_output_var)
        combine_check.pack(side=tk.LEFT, padx=5)
        
        # Open output directory option
        self.open_output_var = tk.BooleanVar(value=True)
        open_check = ttk.Checkbutton(options_frame, text="Open output when finished", 
                                   variable=self.open_output_var)
        open_check.pack(side=tk.LEFT, padx=5)
        
        # Conversion control buttons
        control_frame = ttk.Frame(config_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        self.convert_btn = ttk.Button(control_frame, text="Convert Selected Files", 
                                    command=self.convert_selected_files, style="Accent.TButton")
        self.convert_btn.pack(side=tk.LEFT, padx=5)
        
        self.cancel_btn = ttk.Button(control_frame, text="Cancel", 
                                   command=self.cancel_conversion, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Conversion log
        log_frame = ttk.LabelFrame(main_frame, text="Conversion Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Progress bar
        self.progress_frame = ttk.Frame(log_frame)
        self.progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient=tk.HORIZONTAL, 
                                         length=100, mode='determinate', 
                                         variable=self.progress_var)
        self.progress_bar.pack(fill=tk.X, side=tk.LEFT, expand=True)
        
        self.status_label = ttk.Label(self.progress_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, state="disabled")
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Set up custom logging
        self.log_handler = LoggingHandler(self.log_text)
        self.log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(self.log_handler)
        
        logger.info("MD to HTML converter tab initialized")
    
    def convert_selected_files(self):
        """Process the files selected in the main library panel for MD to HTML conversion."""
        # Get files selected in the main library panel
        selected_files = []
        
        if hasattr(self.parent, "file_tree") and self.parent.file_tree:
            for item_id in self.parent.file_tree.selection():
                item_values = self.parent.file_tree.item(item_id, "values")
                if item_values and len(item_values) > 1:
                    path = item_values[0]
                    item_type = item_values[1] if len(item_values) > 1 else ""
                    
                    # Only process markdown files, not directories
                    if item_type != "directory" and os.path.isfile(path) and path.lower().endswith(".md"):
                        selected_files.append(path)
        
        # Update the files to convert
        self.files_to_convert = selected_files
        self.update_file_list()
        
        # Check if any markdown files were selected
        if not self.files_to_convert:
            messagebox.showinfo("No Markdown Files", "Please select markdown (.md) files in the library panel first.")
            return
        
        # Get output directory
        output_dir = self.output_dir_var.get().strip()
        if not output_dir:
            # Default to the same directory as the first file
            output_dir = os.path.dirname(self.files_to_convert[0])
            self.output_dir_var.set(output_dir)
        
        self.output_dir = output_dir
        
        # Start the conversion
        self.start_conversion()
    
    def update_file_list(self):
        """Update the file count label."""
        self.file_count_label.config(text=f"{len(self.files_to_convert)} files selected for conversion")
    
    def select_output_directory(self):
        """Open directory dialog to select output directory"""
        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if output_dir:
            self.output_dir_var.set(output_dir)
    
    def start_conversion(self):
        """Start the batch conversion process"""
        # Check if files are selected
        if not self.files_to_convert:
            messagebox.showinfo("No Files Selected", "Please select files to convert.")
            return
        
        # Check output directory
        output_dir = self.output_dir_var.get()
        if not output_dir:
            messagebox.showinfo("No Output Directory", "Please select an output directory.")
            return
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create output directory: {str(e)}")
                return
        
        # Get options
        combine_output = self.combine_output_var.get()
        open_output = self.open_output_var.get()
        
        # Update UI
        self.is_converting = True
        self.convert_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress_bar["value"] = 0
        self.update_status("Starting conversion...")
        
        # Clear log
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # Start conversion thread
        self.conversion_thread = threading.Thread(
            target=self.run_conversion,
            args=(self.files_to_convert.copy(), output_dir, combine_output, open_output),
            daemon=True
        )
        self.conversion_thread.start()
    
    def run_conversion(self, files, output_dir, combine_output, open_output):
        """Run the batch conversion process in a separate thread"""
        try:
            # Initialize variables
            total_files = len(files)
            successful = 0
            combined_html = ""
            combined_filename = f"combined_markdown_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            
            logger.info(f"Starting conversion of {total_files} files")
            logger.info(f"Output directory: {output_dir}")
            logger.info(f"Combine output: {combine_output}")
            
            # Process each file
            for i, file_path in enumerate(files):
                # Check if conversion was cancelled
                if not self.is_converting:
                    logger.info("Conversion cancelled")
                    break
                
                try:
                    # Update status
                    filename = os.path.basename(file_path)
                    self.update_status(f"Converting {i+1}/{total_files}: {filename}")
                    self.update_progress((i / total_files) * 100)
                    
                    logger.info(f"Processing: {file_path}")
                    
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Convert content
                    html_content = markdown_to_html(content)
                    
                    if combine_output:
                        # Add file header and content to combined output
                        combined_html += f"<h1>{filename}</h1>\n"
                        combined_html += html_content
                        combined_html += "<hr style='margin-top: 30px; margin-bottom: 30px;'>\n"
                    else:
                        # Save individual file
                        output_filename = os.path.splitext(filename)[0] + ".html"
                        output_path = os.path.join(output_dir, output_filename)
                        
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(html_content)
                        
                        logger.info(f"Created: {output_path}")
                    
                    successful += 1
                    
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # Save combined file if requested
            if combine_output and combined_html and self.is_converting:
                output_path = os.path.join(output_dir, combined_filename)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(combined_html)
                logger.info(f"Created combined file: {output_path}")
            
            # Open output directory if requested
            if open_output and self.is_converting:
                self.parent.after(0, lambda: os.startfile(output_dir))
                logger.info("Opened output directory")
            
            # Update UI
            if self.is_converting:
                self.update_status(f"Conversion complete. {successful}/{total_files} files converted successfully.")
                self.update_progress(100)
                logger.info(f"Conversion complete. {successful}/{total_files} files converted successfully.")
                
                # Show completion message
                self.parent.after(0, lambda: messagebox.showinfo(
                    "Conversion Complete", 
                    f"{successful}/{total_files} files converted successfully."
                ))
        
        except Exception as e:
            logger.error(f"Error during conversion: {str(e)}")
            logger.error(traceback.format_exc())
            self.update_status(f"Error: {str(e)}")
            
            # Show error message
            self.parent.after(0, lambda: messagebox.showerror(
                "Conversion Error", 
                f"An error occurred during conversion: {str(e)}"
            ))
        
        finally:
            # Reset UI
            self.parent.after(0, self.reset_ui)
    
    def update_status(self, message):
        """Update status label from any thread"""
        self.parent.after(0, lambda: self.status_label.config(text=message))
        self.parent.update_status(message)
    
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
        tab = self.parent.file_renamer_tab
        
        # Main frame for all controls
        main_frame = ttk.Frame(tab, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title label
        title_label = ttk.Label(main_frame, text="Standardize File Names", font=("Arial", 12, "bold"))
        title_label.pack(pady=(10, 15))
        
        # Configuration frame
        config_frame = ttk.LabelFrame(main_frame, text="Renaming Settings", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Instructions
        instructions = ttk.Label(config_frame, 
                           text="Select markdown files in the library panel and click 'Preview Rename' to see the new standardized filenames.")
        instructions.pack(anchor="w", padx=5, pady=5)
        
        # File count status
        self.file_count_label = ttk.Label(config_frame, text="0 files selected for renaming")
        self.file_count_label.pack(anchor=tk.W, pady=5)
        
        # Additional options
        options_frame = ttk.Frame(config_frame)
        options_frame.pack(fill=tk.X, pady=5)
        
        # Backup option
        self.create_backup_var = tk.BooleanVar(value=True)
        backup_check = ttk.Checkbutton(options_frame, text="Create backup of original files", 
                                      variable=self.create_backup_var)
        backup_check.pack(side=tk.LEFT, padx=5)
        
        # Renaming control buttons
        control_frame = ttk.Frame(config_frame)
        control_frame.pack(fill=tk.X, pady=10)
        
        self.preview_btn = ttk.Button(control_frame, text="Preview Rename", 
                                    command=self.preview_rename_files)
        self.preview_btn.pack(side=tk.LEFT, padx=5)
        
        self.rename_btn = ttk.Button(control_frame, text="Apply Rename", 
                                    command=self.rename_files, state=tk.DISABLED, style="Accent.TButton")
        self.rename_btn.pack(side=tk.LEFT, padx=5)
        
        self.cancel_btn = ttk.Button(control_frame, text="Cancel", 
                                   command=self.cancel_renaming, state=tk.DISABLED)
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(main_frame, text="Rename Preview", padding=10)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create a treeview for the preview
        self.preview_tree = ttk.Treeview(preview_frame, columns=("Original", "New"), show="headings")
        self.preview_tree.heading("Original", text="Original Filename")
        self.preview_tree.heading("New", text="New Filename")
        self.preview_tree.column("Original", width=300)
        self.preview_tree.column("New", width=300)
        self.preview_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        # Add scrollbar to treeview
        scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL, command=self.preview_tree.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.preview_tree.configure(yscrollcommand=scrollbar.set)
        
        # Log frame for output
        log_frame = ttk.LabelFrame(main_frame, text="Renaming Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Progress bar
        self.progress_frame = ttk.Frame(log_frame)
        self.progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient=tk.HORIZONTAL, 
                                         length=100, mode='determinate', 
                                         variable=self.progress_var)
        self.progress_bar.pack(fill=tk.X, side=tk.LEFT, expand=True)
        
        self.status_label = ttk.Label(self.progress_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, state="disabled")
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Set up custom logging
        self.log_handler = LoggingHandler(self.log_text)
        self.log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(self.log_handler)
        
        logger.info("File renamer tab initialized")
    
    def extract_module_info(self, file_path):
        """Extract module number and title from the markdown file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(500)  # Read just the beginning of the file
            
            # Look for module number (e.g., # 2.12)
            module_number = None
            module_title = None
            
            # Match a line starting with # followed by a number (possibly with decimal)
            number_match = re.search(r'^#\s*(\d+(?:\.\d+)?)', content, re.MULTILINE)
            if number_match:
                module_number = number_match.group(1).strip()
            
            # Look for the next heading, which should be the title
            # This could be either a second level-1 heading or a level-2 heading
            title_match = re.search(r'^#\s+([^#\n]+)$', content, re.MULTILINE)
            if title_match:
                # Find all level-1 headings
                all_h1 = re.findall(r'^#\s+([^#\n]+)$', content, re.MULTILINE)
                if len(all_h1) > 1:
                    # If there's more than one level-1 heading, the second one is likely the title
                    module_title = all_h1[1].strip()
                else:
                    # Otherwise, look for a level-2 heading
                    h2_match = re.search(r'^##\s+([^#\n]+)$', content, re.MULTILINE)
                    if h2_match:
                        module_title = h2_match.group(1).strip()
            
            return module_number, module_title
        except Exception as e:
            logger.error(f"Error extracting module info from {file_path}: {str(e)}")
            return None, None
    
    def generate_standard_filename(self, module_number, module_title, original_path):
        """Generate a standardized filename from module info."""
        if not module_number or not module_title:
            return None
        
        # Format module number with padded zeros for single-digit decimal parts
        # Example: 2.9 becomes 2.09, but 2.10 remains 2.10
        if '.' in module_number:
            base, decimal = module_number.split('.', 1)
            if decimal.isdigit() and len(decimal) == 1:
                module_number = f"{base}.{decimal.zfill(2)}"
        
        # Clean up the title: remove special characters, replace spaces with underscores
        clean_title = re.sub(r'[^\w\s-]', '', module_title)  # Remove special chars
        clean_title = re.sub(r'\s+', '_', clean_title)  # Replace spaces with underscores
        
        # Get the original file extension
        _, ext = os.path.splitext(original_path)
        
        # Create the standardized filename
        return f"{module_number}_{clean_title}{ext}"
    
    def preview_rename_files(self):
        """Preview the renaming of selected files."""
        # Get files selected in the main library panel
        selected_files = []
        
        if hasattr(self.parent, "file_tree") and self.parent.file_tree:
            for item_id in self.parent.file_tree.selection():
                item_values = self.parent.file_tree.item(item_id, "values")
                if item_values and len(item_values) > 1:
                    path = item_values[0]
                    item_type = item_values[1] if len(item_values) > 1 else ""
                    
                    # Only process markdown files, not directories
                    if item_type != "directory" and os.path.isfile(path) and path.lower().endswith(".md"):
                        selected_files.append(path)
        
        # Update the files to rename
        self.files_to_rename = selected_files
        self.update_file_list()
        
        # Check if any markdown files were selected
        if not self.files_to_rename:
            messagebox.showinfo("No Markdown Files", "Please select markdown (.md) files in the library panel first.")
            return
        
        # Clear previous preview
        self.preview_tree.delete(*self.preview_tree.get_children())
        self.preview_data = []
        
        # Generate preview data
        for file_path in self.files_to_rename:
            original_name = os.path.basename(file_path)
            module_number, module_title = self.extract_module_info(file_path)
            
            if module_number and module_title:
                new_name = self.generate_standard_filename(module_number, module_title, file_path)
                if new_name:
                    self.preview_data.append((file_path, original_name, new_name))
                    self.preview_tree.insert("", tk.END, values=(original_name, new_name))
                else:
                    self.preview_tree.insert("", tk.END, values=(original_name, "<Failed to generate name>"))
            else:
                self.preview_tree.insert("", tk.END, values=(original_name, "<Could not extract module info>"))
        
        # Update UI
        if self.preview_data:
            self.rename_btn.config(state=tk.NORMAL)
            self.update_status(f"Preview complete. {len(self.preview_data)} files ready to rename.")
        else:
            self.rename_btn.config(state=tk.DISABLED)
            self.update_status("No valid files to rename found.")
    
    def rename_files(self):
        """Start the file renaming process."""
        # Check if we have preview data
        if not self.preview_data:
            messagebox.showinfo("No Files", "Please preview files before renaming.")
            return
        
        # Update UI
        self.is_renaming = True
        self.preview_btn.config(state=tk.DISABLED)
        self.rename_btn.config(state=tk.DISABLED)
        self.cancel_btn.config(state=tk.NORMAL)
        self.progress_bar["value"] = 0
        self.update_status("Starting renaming...")
        
        # Clear log
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # Get backup option
        create_backup = self.create_backup_var.get()
        
        # Start renaming thread
        self.rename_thread = threading.Thread(
            target=self.run_renaming,
            args=(self.preview_data.copy(), create_backup),
            daemon=True
        )
        self.rename_thread.start()
    
    def run_renaming(self, rename_data, create_backup):
        """Run the file renaming process in a separate thread."""
        try:
            # Initialize variables
            total_files = len(rename_data)
            successful = 0
            
            logger.info(f"Starting renaming of {total_files} files")
            logger.info(f"Create backup: {create_backup}")
            
            # Process each file
            for i, (file_path, original_name, new_name) in enumerate(rename_data):
                # Check if renaming was cancelled
                if not self.is_renaming:
                    logger.info("Renaming cancelled")
                    break
                
                try:
                    # Update status
                    self.update_status(f"Renaming {i+1}/{total_files}: {original_name}")
                    self.update_progress((i / total_files) * 100)
                    
                    logger.info(f"Processing: {file_path}")
                    
                    # Get directory and create new path
                    directory = os.path.dirname(file_path)
                    new_path = os.path.join(directory, new_name)
                    
                    # Check if target already exists
                    if os.path.exists(new_path) and new_path != file_path:
                        logger.warning(f"Destination file already exists: {new_path}")
                        continue
                    
                    # Skip if the new name is the same as the original
                    if original_name == new_name:
                        logger.info(f"Skipping {file_path} - name already standardized")
                        successful += 1
                        continue
                    
                    # Create backup if requested
                    if create_backup:
                        backup_path = file_path + ".bak"
                        shutil.copy2(file_path, backup_path)
                        logger.info(f"Created backup: {backup_path}")
                    
                    # Rename the file
                    os.rename(file_path, new_path)
                    logger.info(f"Renamed: {original_name} → {new_name}")
                    
                    successful += 1
                    
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")
                    logger.error(traceback.format_exc())
            
            # Update UI
            if self.is_renaming:
                self.update_status(f"Renaming complete. {successful}/{total_files} files renamed successfully.")
                self.update_progress(100)
                logger.info(f"Renaming complete. {successful}/{total_files} files renamed successfully.")
                
                # Show completion message
                self.parent.after(0, lambda: messagebox.showinfo(
                    "Renaming Complete", 
                    f"{successful}/{total_files} files renamed successfully."
                ))
                
                # Refresh the file tree after renaming
                if hasattr(self.parent, "refresh_file_tree"):
                    self.parent.after(500, self.parent.refresh_file_tree)  # Slight delay to ensure files are updated
        
        except Exception as e:
            logger.error(f"Error during renaming: {str(e)}")
            logger.error(traceback.format_exc())
            self.update_status(f"Error: {str(e)}")
            
            # Show error message
            self.parent.after(0, lambda: messagebox.showerror(
                "Renaming Error", 
                f"An error occurred during renaming: {str(e)}"
            ))
        
        finally:
            # Reset UI
            self.parent.after(0, self.reset_ui)
    
    def update_file_list(self):
        """Update the file count label."""
        self.file_count_label.config(text=f"{len(self.files_to_rename)} files selected for renaming")
    
    def update_status(self, message):
        """Update status label from any thread."""
        self.parent.after(0, lambda: self.status_label.config(text=message))
        self.parent.update_status(message)
    
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
