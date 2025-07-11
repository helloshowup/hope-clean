"""Content Enhancement Module for ClaudeAIPanel"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import logging
import json
import datetime
from .path_utils import get_project_root

# Import Claude API functionality
from claude_api import Client
from showup_tools.showup_core.claude_api_consts import LINE_EDIT_HEADER

# These constants were removed from the updated claude-api package. Provide
# simple replacements so existing prompts continue to work.
CONTEXT_SYSTEM_PROMPT = (
    "You are a helpful assistant that prepares editing context for documents."
)

# Get logger
logger = logging.getLogger("output_library_editor")


def send_claude_edit_request(cookie: str, markdown_text: str, instructions: str,
                             context: str = "") -> str:
    """Send an edit request to Claude using the modern Client API."""
    client = Client(cookie)
    conversation_id = client.create_new_chat()["uuid"]
    prompt_parts = [LINE_EDIT_HEADER, f"Instructions:\n{instructions.strip()}" ]
    if context:
        prompt_parts.append(f"Context:\n{context.strip()}")
    prompt_parts.append(f"Markdown:\n{markdown_text}")
    prompt = "\n\n".join(prompt_parts)
    return client.send_message(prompt, conversation_id)


def generate_claude_context(cookie: str, prompt: str, system_prompt: str) -> str:
    """Generate context using Claude via the modern API."""
    client = Client(cookie)
    conversation_id = client.create_new_chat()["uuid"]
    combined = f"{system_prompt}\n\n{prompt}"
    return client.send_message(combined, conversation_id)

class ContentEnhancer:
    """Handles content enhancement for the ClaudeAIPanel."""
    
    def __init__(self, parent):
        """Initialize the content enhancer.
        
        Args:
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        self.current_file_path = None
        self.current_file_content = ""
        self.enhanced_content = ""
        self.context = ""
        self.edit_thread = None
        self.context_thread = None
        
    def setup_enhance_tab(self):
        """Set up the content enhancement tab."""
        tab = self.parent.enhance_tab
        
        # Create main vertical panes
        self.main_panes = ttk.PanedWindow(tab, orient=tk.VERTICAL)
        self.main_panes.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Top section: File content and enhancement controls
        top_frame = ttk.Frame(self.main_panes)
        
        # Create horizontal panes for file and enhanced content
        self.content_panes = ttk.PanedWindow(top_frame, orient=tk.HORIZONTAL)
        self.content_panes.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left side: Original file content
        file_frame = ttk.LabelFrame(self.content_panes, text="Original Content")
        self.content_panes.add(file_frame, weight=1)
        
        # Add content area
        self.file_content = scrolledtext.ScrolledText(file_frame, wrap=tk.WORD)
        self.file_content.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Enhancement control frame
        control_frame = ttk.Frame(file_frame)
        control_frame.pack(fill="x", padx=5, pady=5)
        
        # Add context generation button
        self.context_btn = ttk.Button(control_frame, text="Generate Context", command=self.generate_context)
        self.context_btn.pack(side="left", padx=5)
        
        # Add enhancement button
        self.enhance_btn = ttk.Button(control_frame, text="Enhance Content", command=self.enhance_content)
        self.enhance_btn.pack(side="left", padx=5)
        
        # Add save button
        self.save_btn = ttk.Button(control_frame, text="Save Enhanced", command=self.save_enhanced_content)
        self.save_btn.pack(side="left", padx=5)
        
        # Add open button
        self.open_btn = ttk.Button(control_frame, text="Open File", command=self.open_file)
        self.open_btn.pack(side="left", padx=5)
        
        # Add toggle for Claude edit tool
        self.use_edit_tool_var = tk.BooleanVar(value=True)
        self.edit_tool_checkbutton = ttk.Checkbutton(
            control_frame, 
            text="Use Claude Edit Tool", 
            variable=self.use_edit_tool_var
        )
        self.edit_tool_checkbutton.pack(side="left", padx=15)
        
        # Add status label
        self.status_label = ttk.Label(control_frame, text="Ready")
        self.status_label.pack(side="left", padx=5)
        
        # Right side: Enhanced content
        enhanced_frame = ttk.LabelFrame(self.content_panes, text="Enhanced Content")
        self.content_panes.add(enhanced_frame, weight=1)
        
        # Add enhanced content area
        self.enhanced_display = scrolledtext.ScrolledText(enhanced_frame, wrap=tk.WORD)
        self.enhanced_display.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Bottom section: Context display
        context_frame = ttk.LabelFrame(self.main_panes, text="Generated Context")
        self.main_panes.add(top_frame, weight=3)
        self.main_panes.add(context_frame, weight=1)
        
        # Add context display with scrollbars
        self.context_display = scrolledtext.ScrolledText(context_frame, wrap=tk.WORD)
        self.context_display.pack(fill="both", expand=True, padx=5, pady=5)
    
    def open_file(self):
        """Open a markdown file for editing."""
        file_path = filedialog.askopenfilename(
            title="Open Markdown File",
            filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        
        if file_path:
            self.set_file_content(file_path)
    
    def set_file_content(self, file_path, content=None):
        """Set the file content either from a path or direct content."""
        self.current_file_path = file_path
        
        try:
            # Clear current content
            self.file_content.delete(1.0, tk.END)
            
            # Load content if not provided
            if content is None:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            
            # Update displays
            self.current_file_content = content
            self.file_content.insert(tk.END, content)
            
            # Update status
            self.status_label.config(text=f"Loaded: {os.path.basename(file_path)}")
            logger.info(f"Loaded file: {file_path}")
            
            # Clear enhanced content and context
            self.enhanced_display.delete(1.0, tk.END)
            self.context_display.delete(1.0, tk.END)
            self.enhanced_content = ""
            self.context = ""
            
        except Exception as e:
            messagebox.showerror("Error", f"Error loading file: {str(e)}")
            logger.error(f"Error loading file {file_path}: {str(e)}")
    
    def generate_context(self):
        """Generate context using Claude Haiku API."""
        # Verify we have file content
        file_content = self.file_content.get(1.0, tk.END).strip()
        if not file_content:
            messagebox.showwarning("No Content", "Please load or enter content to generate context for.")
            return
        
        # Get custom prompt and learner profile
        custom_prompt = ""
        learner_profile = ""
        
        # If parent has prompt manager initialized, get selected prompt
        if hasattr(self.parent, "prompt_manager") and self.parent.prompt_manager.selected_prompt:
            prompt_name = self.parent.prompt_manager.selected_prompt
            if prompt_name in self.parent.prompt_manager.prompts:
                custom_prompt = self.parent.prompt_manager.prompts[prompt_name]["content"]
        
        # If parent has profiles dropdown, get selected profile
        if self.parent.profiles and self.parent.profiles_dropdown_var.get():
            profile_name = self.parent.profiles_dropdown_var.get()
            if profile_name in self.parent.profiles:
                learner_profile = self.parent.profiles[profile_name]["system"]
        
        # Start context generation in a thread
        self.context_thread = threading.Thread(
            target=self._generate_context_thread,
            args=(file_content, custom_prompt, learner_profile)
        )
        self.context_thread.daemon = True
        self.context_thread.start()
        
        # Update UI
        self.status_label.config(text="Generating context...")
        self.context_btn.config(state="disabled")
        self.enhance_btn.config(state="disabled")
    
    def _generate_context_thread(self, file_content, custom_prompt, learner_profile):
        """Thread function for context generation."""
        try:
            # Skip local caching and use Claude's native API caching
            logger.info("Generating context using Claude's native API caching")
            
            # Enhanced system prompt for context generation
            system_prompt = """
            You are an expert educational content analyst specializing in content preparation and enhancement guidance.
            Your task is to analyze educational content and create a comprehensive preparatory context
            that will guide subsequent content enhancement.
            
            Focus on:
            1. Identifying the core purpose and structure of the content
            2. Extracting clear objectives from enhancement prompts
            3. Adapting content appropriately for the specific target learner
            4. Optimizing content for the learning medium specified in the profile
            5. Providing strategic guidance for improvement while preserving value
            
            Be concise yet thorough in your analysis. The quality of your preparatory context
            directly impacts the effectiveness of subsequent content enhancement.
            Generate content that serves as a foundation for further development, not as a final product.
            
            IMPORTANT: Include all learner profile considerations directly in your context. This will be
            the only guidance about the target learner available during enhancement.
            
            Pay particular attention to any limitations mentioned in the learner profile related to the learning medium 
            (such as asynchronous online learning, in-person classroom, mobile device, etc.), but avoid being
            overly prescriptive about formatting or structural changes unless specifically requested.
            """
            
            # Create a structured prompt for context generation that includes learner profile guidance
            full_prompt = f"""
            # Analysis Task: Generate Preparatory Context
            
            Please analyze the current content, enhancement prompt, and target learner profile to create a comprehensive 
            context that will guide content enhancement while:
            1. Maintaining educational integrity
            2. Addressing the specific needs in the enhancement prompt
            3. Preserving the original content's core value
            4. Adapting content appropriately for the target learner profile
            5. Optimizing for the learning medium (asynchronous online, in-person classroom, etc.)

            Your analysis must:
            - Identify key themes and concepts in the current content
            - Extract specific requirements from the enhancement prompt
            - Determine appropriate language level, examples, and complexity based on the learner profile
            - Note any limitations or considerations based on the learning medium
            - Create a guidance framework for targeted content enhancement
            - Suggest potential improvements while preserving original intent

            Format your response as a pre-fill instruction that provides a high-level overview 
            including:
            1. Content Summary: Brief overview of the current content's purpose and structure
            2. Enhancement Requirements: Clear objectives derived from the prompt
            3. Target Learner Considerations: Specific adaptations needed for the target learner
            4. Learning Medium Considerations: Brief note on any limitations imposed by the delivery medium
            5. Key Considerations: Important elements to preserve or improve
            6. Suggested Approach: Strategic recommendations for enhancement
            
            This preparatory context will be used as guidance for subsequent content enhancement.
            Focus on providing clear, actionable direction rather than specific edits.
            Include everything relevant from the learner profile directly in this context - the profile information
            will not be sent separately during enhancement.

            ## Target Learner Profile
            {learner_profile}

            ## Current Content
            {file_content}

            ## Enhancement Prompt
            {custom_prompt}
            """
            
            # Generate context with improved prompt structure
            cookie = os.getenv("CLAUDE_SESSION_COOKIE", "")
            context = generate_claude_context(
                cookie=cookie,
                prompt=full_prompt,
                system_prompt=system_prompt,
            )
            
            # Save context response to log file
            context_response_data = {
                "request_type": "content_enhancer_context_generation",
                "prompt": full_prompt,
                "system_prompt": system_prompt,
                "response": context
            }
            self._save_api_response_to_log(context_response_data)
            
            # Update UI in main thread
            self._update_ui_with_context(context)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Context generation error: {error_msg}")
            # Update UI with error in main thread
            self.parent.parent.after(0, lambda: self._update_ui_with_error(error_msg))
    
    def _update_ui_with_context(self, context):
        """Update UI with generated context (called from main thread)."""
        def update():
            self.context = context
            self.context_display.delete(1.0, tk.END)
            self.context_display.insert(tk.END, context)
            self.status_label.config(text="Context generated")
            self.context_btn.config(state="normal")
            self.enhance_btn.config(state="normal")
        
        self.parent.parent.after(0, update)
    
    def _update_ui_with_error(self, error_msg):
        """Update UI with error message (called from main thread)."""
        self.status_label.config(text=f"Error: {error_msg}")
        self.context_btn.config(state="normal")
        self.enhance_btn.config(state="normal")
        messagebox.showerror("Error", f"Context generation failed: {error_msg}")
    
    def enhance_content(self):
        """Enhance content using Claude Sonnet API."""
        # Verify we have file content
        file_content = self.file_content.get(1.0, tk.END).strip()
        if not file_content:
            messagebox.showwarning("No Content", "Please load or enter content to enhance.")
            return
        
        # Get custom prompt
        custom_prompt = ""
        
        # If parent has prompt manager initialized, get selected prompt
        if hasattr(self.parent, "prompt_manager") and self.parent.prompt_manager.selected_prompt:
            prompt_name = self.parent.prompt_manager.selected_prompt
            
            # Handle custom prompt option
            if prompt_name == "[Custom Prompt]":
                custom_prompt = self.parent.prompt_manager.prompt_content.get(1.0, tk.END).strip()
                logger.info("Using custom prompt from text editor")
            # Handle regular prompt
            elif prompt_name in self.parent.prompt_manager.prompts:
                custom_prompt = self.parent.prompt_manager.prompts[prompt_name]["content"]
                logger.info(f"Using prompt: {prompt_name}")
        
        # Check if we have a prompt
        if not custom_prompt:
            messagebox.showwarning("No Prompt", "Please select a prompt or enter a custom prompt in the Prompt Config tab.")
            return
            
        # Log the prompt being used (first 100 chars)
        prompt_preview = custom_prompt[:100] + "..." if len(custom_prompt) > 100 else custom_prompt
        logger.info(f"Prompt content preview: {prompt_preview}")
        
        # Start enhancement in a thread
        self.edit_thread = threading.Thread(
            target=self._enhance_content_thread,
            args=(file_content, custom_prompt, self.context)
        )
        self.edit_thread.daemon = True
        self.edit_thread.start()
        
        # Update UI
        self.status_label.config(text="Enhancing content...")
        self.enhance_btn.config(state="disabled")
        self.context_btn.config(state="disabled")
    
    def _enhance_content_thread(self, file_content, custom_prompt, context):
        """Thread function for content enhancement."""
        try:
            # Skip local caching but maintain token-efficient approach
            logger.info("Enhancing content using unified text editor approach")
            
            # Special handling for learning objectives to provide clear structure to the instructions
            if "learning objective" in custom_prompt.lower() and not custom_prompt.startswith("INSTRUCTIONS:"):
                instructions = f"INSTRUCTIONS: Add appropriate learning objectives at the beginning of this content.\n\nCreate 3-5 clear, measurable learning objectives that reflect what students will learn from this material. Format them as a bulleted list under a 'Learning Objectives' heading at the very beginning of the document.\n\nBe specific and use action verbs. The objectives should directly relate to the existing content.\n\nOriginal instructions: {custom_prompt}"
            else:
                instructions = custom_prompt
            
            # Validate instructions
            if not instructions or len(instructions.strip()) < 10:
                raise ValueError("Instructions must contain a clear task definition (at least 10 characters)")
            
            # Log the content length for debugging
            logger.info(f"Processing content with {len(file_content)} characters")
            
            # Call the text editor tool with the proper structure using the
            # updated Claude client
            cookie = os.getenv("CLAUDE_SESSION_COOKIE", "")
            enhanced_content = send_claude_edit_request(
                cookie=cookie,
                markdown_text=file_content,
                instructions=instructions,
                context=context,
            )
            
            # Save API response to log file
            edit_response_data = {
                "request_type": "content_enhancement",
                "markdown_text_length": len(file_content),
                "instructions": instructions,
                "context_length": len(context) if context else 0,
                "model": self.parent.edit_model,
                "response_length": len(enhanced_content) if enhanced_content else 0
            }
            self._save_api_response_to_log(edit_response_data)
            
            # Update UI in main thread
            self.parent.after(0, lambda: self._update_ui_with_enhanced(enhanced_content))
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Content enhancement error: {error_msg}")
            self.parent.after(0, lambda: self._update_ui_with_enhancement_error(error_msg))
    
    def _update_ui_with_enhanced(self, enhanced_content):
        """Update UI with enhanced content (called from main thread)."""
        def update():
            self.enhanced_content = enhanced_content
            self.enhanced_display.delete(1.0, tk.END)
            self.enhanced_display.insert(tk.END, enhanced_content)
            self.status_label.config(text="Enhancement complete")
            self.enhance_btn.config(state="normal")
            self.context_btn.config(state="normal")
        
        self.parent.parent.after(0, update)
    
    def _update_ui_with_enhancement_error(self, error_msg):
        """Update UI with error message (called from main thread)."""
        self.status_label.config(text=f"Error: {error_msg}")
        self.enhance_btn.config(state="normal")
        self.context_btn.config(state="normal")
        messagebox.showerror("Error", f"Content enhancement failed: {error_msg}")
    
    def save_enhanced_content(self):
        """Save the enhanced content to a file."""
        if not self.enhanced_content:
            messagebox.showwarning("No Content", "No enhanced content to save.")
            return
        
        # Determine default save path
        default_path = ""
        if self.current_file_path:
            # Create a path with _enhanced suffix
            base, ext = os.path.splitext(self.current_file_path)
            default_path = f"{base}_enhanced{ext}"
        
        # Ask for save location
        save_path = filedialog.asksaveasfilename(
            title="Save Enhanced Content",
            defaultextension=".md",
            initialfile=os.path.basename(default_path) if default_path else "enhanced.md",
            filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        
        if save_path:
            try:
                with open(save_path, "w", encoding="utf-8") as f:
                    f.write(self.enhanced_content)
                
                self.status_label.config(text=f"Saved to: {os.path.basename(save_path)}")
                logger.info(f"Saved enhanced content to: {save_path}")
                
                # Ask if user wants to load the saved file
                if messagebox.askyesno("Load File", "Would you like to load the saved file?"):
                    self.set_file_content(save_path, self.enhanced_content)
                    
            except Exception as e:
                messagebox.showerror("Save Error", f"Failed to save file: {str(e)}")
                logger.error(f"Error saving to {save_path}: {str(e)}")
    
    def _save_api_response_to_log(self, response_data):
        """Save API response to a JSON file in the logs folder.
        
        Args:
            response_data (dict): Dictionary containing the response data to save
        """
        try:
            # Ensure logs directory exists
            logs_dir = os.path.join(str(get_project_root()), "showup-editor-ui", "logs", "api_responses")
            os.makedirs(logs_dir, exist_ok=True)
            
            # Create filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"claude_api_{response_data['request_type']}_{timestamp}.json"
            filepath = os.path.join(logs_dir, filename)
            
            # Write response to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(response_data, f, indent=2)
            
            logger.info(f"Saved {response_data['request_type']} API response to {filename}")
            
        except Exception as e:
            logger.error(f"Error saving API response to log: {str(e)}")
