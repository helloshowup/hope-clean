"""Content Generation Module for ClaudeAIPanel"""

import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import logging
import sys
from .path_utils import get_project_root
# Dynamic import of cache_utils.py from root directory
from importlib.util import spec_from_file_location, module_from_spec

# Path to cache_utils.py in the root directory
cache_utils_path = os.path.join(str(get_project_root()), 'cache_utils.py')

# Import cache_utils.py dynamically
spec = spec_from_file_location('cache_utils', cache_utils_path)
cache_utils = module_from_spec(spec)
spec.loader.exec_module(cache_utils)

# Get the required function
get_cache_instance = cache_utils.get_cache_instance

# Import Claude API functionality from the showup-core directory
claude_api_path = os.path.join(str(get_project_root()), 'showup-core', 'claude_api.py')

# Import claude_api.py dynamically
spec = spec_from_file_location('claude_api', claude_api_path)
claude_api = module_from_spec(spec)
spec.loader.exec_module(claude_api)

# Get the required functions
generate_content_with_claude = claude_api.generate_with_claude_sonnet

# Import CLAUDE_MODELS configuration
sys.path.insert(0, os.path.join(str(get_project_root()), "showup-core"))
from claude_api import CLAUDE_MODELS

# Get logger
logger = logging.getLogger("output_library_editor")

class ContentGenerator:
    """Handles content generation for the ClaudeAIPanel."""
    
    def __init__(self, parent):
        """Initialize the content generator.
        
        Args:
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        self.generated_content = ""
        self.generation_thread = None
        self.output_dir = "" 
        
    def setup_generate_content_tab(self):
        """Set up the content generation tab."""
        tab = self.parent.generate_content_tab
        
        # Create output directory frame
        output_dir_frame = ttk.LabelFrame(tab, text="Output Directory")
        output_dir_frame.pack(fill="x", padx=10, pady=5)
        
        # Add output directory entry
        self.output_dir_var = tk.StringVar()
        output_dir_entry = ttk.Entry(output_dir_frame, textvariable=self.output_dir_var, width=50)
        output_dir_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        # Add browse button
        browse_btn = ttk.Button(output_dir_frame, text="Browse...", command=self._browse_output_dir)
        browse_btn.pack(side="right", padx=5, pady=5)
        
        # Create prompt frame
        prompt_frame = ttk.LabelFrame(tab, text="Generate Content")
        prompt_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Add model selection frame
        model_frame = ttk.Frame(prompt_frame)
        model_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(model_frame, text="Model:").pack(side="left", padx=5)
        
        # Add model selection dropdown
        self.generate_model_var = tk.StringVar(value=CLAUDE_MODELS["CONTEXT_GEN"])
        self.generate_model_dropdown = ttk.Combobox(model_frame, textvariable=self.generate_model_var, values=[
            CLAUDE_MODELS["CONTEXT_GEN"],
            CLAUDE_MODELS["CONTENT_EDIT"],
            "claude-opus-4-20250514"
        ], state="readonly", width=30)
        self.generate_model_dropdown.pack(side="left", padx=5)
        
        # Create split frame
        split_frame = ttk.Frame(prompt_frame)
        split_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create left pane
        left_frame = ttk.Frame(split_frame)
        left_frame.pack(side="left", fill="both", expand=True)
        
        # Create note to inform user that prompt will be pulled from Prompt Config tab
        prompt_note_frame = ttk.LabelFrame(left_frame, text="Note")
        prompt_note_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        prompt_note = ttk.Label(prompt_note_frame, text="The prompt and target learner will be pulled\nfrom the Prompt Config tab.\n\nNo context will be generated before submission.")
        prompt_note.pack(padx=5, pady=5)
        
        # Create custom prompt frame - Keep this for additional instructions if needed
        custom_prompt_frame = ttk.LabelFrame(split_frame, text="Additional Instructions (Optional)")
        custom_prompt_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add custom prompt text area
        self.custom_prompt_text = scrolledtext.ScrolledText(custom_prompt_frame, wrap=tk.WORD, height=10)
        self.custom_prompt_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add generate button frame
        generate_btn_frame = ttk.Frame(prompt_frame)
        generate_btn_frame.pack(fill="x", pady=5)
        
        # Add progress bar
        self.generate_progress = ttk.Progressbar(generate_btn_frame, mode="indeterminate")
        self.generate_progress.pack(side="left", fill="x", expand=True, padx=5)
        
        # Add generate button
        self.generate_btn = ttk.Button(generate_btn_frame, text="Generate Content", command=self.generate_custom_content)
        self.generate_btn.pack(side="right", padx=5)
        
        # Create generated content frame
        content_frame = ttk.LabelFrame(tab, text="Generated Content")
        content_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Add content text area
        self.generated_content_text = scrolledtext.ScrolledText(content_frame, wrap=tk.WORD)
        self.generated_content_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add thinking area label
        ttk.Label(content_frame, text="Claude's Thinking Process:").pack(anchor="w", padx=5)
        
        # Add thinking text area
        self.thinking_text = scrolledtext.ScrolledText(content_frame, wrap=tk.WORD, height=5)
        self.thinking_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add save button
        self.save_btn = ttk.Button(content_frame, text="Save Content", command=self.save_generated_content)
        self.save_btn.pack(side="right", padx=5, pady=5)
        
        # Bind mouse wheel events for scrolling
        self.bind_mousewheel()
    
    def on_mousewheel(event):
        """Handle mousewheel events for scrolling."""
        # Implementation would depend on the platform
        pass
        
    def bind_mousewheel(self, event=None):
        """Bind mousewheel events to the scrollable widgets."""
        # Implementation would depend on the platform
        pass
        
    def unbind_mousewheel(self, event=None):
        """Unbind mousewheel events from the scrollable widgets."""
        # Implementation would depend on the platform
        pass
    
    def _browse_output_dir(self):
        """Browse for output directory."""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir_var.set(directory)
    
    def load_generate_prompt_templates(self):
        """Load content generation prompt templates."""
        # No longer needed as we pull from Prompt Config tab
        pass
    
    def on_generate_prompt_selected(self, event):
        """Handle selection of a prompt template."""
        # No longer needed as we pull from Prompt Config tab
        pass
    
    def load_learner_profiles_for_generation(self):
        """Load available learner profiles for content generation."""
        # No longer needed as we pull from Prompt Config tab
        pass
    
    def on_generate_profile_selected(self, event):
        """Handle selection of a learner profile for content generation."""
        # No longer needed as we pull from Prompt Config tab
        pass
    
    def generate_custom_content(self):
        """Generate custom content using Claude."""
        # Get current file content from selected files in the file tree
        file_content = ""
        file_paths = []
        
        # Add diagnostic logging
        logger.info("Starting content generation...")
        if hasattr(self.parent, 'selected_files'):
            logger.info(f"Parent has selected_files attribute: {self.parent.selected_files}")
        else:
            logger.info("Parent does not have selected_files attribute")
            
        # Check for files selected in the file tree view
        # Try alternative approaches to get selected files
        if hasattr(self.parent, 'file_tree') and self.parent.file_tree:
            # Get selected items from the file tree
            selected_items = self.parent.file_tree.selection()
            logger.info(f"Selected items in file tree: {selected_items}")
            
            # Get the path for each selected item
            for item in selected_items:
                try:
                    item_path = self.parent.file_tree.item(item, "values")[0]  # Typically the full path is in values
                    
                    # Sometimes the path might be in text instead
                    if not item_path or not os.path.exists(item_path):
                        item_path = self.parent.file_tree.item(item, "text")
                    
                    # Make sure we have a valid path
                    if item_path and os.path.exists(item_path):
                        file_paths.append(item_path)
                        logger.info(f"Added file path: {item_path}")
                except Exception as e:
                    logger.error(f"Error getting path for item: {str(e)}")
        
        # If we still don't have files, try the previously used method
        if not file_paths and hasattr(self.parent, 'selected_files') and self.parent.selected_files:
            file_paths = self.parent.selected_files
            logger.info(f"Using parent.selected_files: {file_paths}")
            
        # Process the selected files
        if file_paths:
            combined_content = []
            
            # Read content from all selected files
            for file_path in file_paths:
                try:
                    # Make sure it's a file, not a directory
                    if os.path.isfile(file_path):
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Add filename as header to separate content
                            file_name = os.path.basename(file_path)
                            combined_content.append(f"\n\n### File: {file_name} ###\n\n{content}")
                            logger.info(f"Successfully read file: {file_path}")
                    else:
                        logger.info(f"Skipping directory: {file_path}")
                except Exception as e:
                    logger.error(f"Error reading file {file_path}: {str(e)}")
                    messagebox.showerror("Error", f"Could not read file {os.path.basename(file_path)}: {str(e)}")
            
            # Combine all file contents
            file_content = "\n\n".join(combined_content)
            
        # If no files are selected, check if there's content in the markdown editor
        if not file_content and hasattr(self.parent, 'markdown_editor') and hasattr(self.parent.markdown_editor, 'editor'):
            file_content = self.parent.markdown_editor.editor.get(1.0, tk.END)
            logger.info("Using content from markdown editor")
        
        if not file_content.strip():
            logger.warning("No content found in files or editor")
            messagebox.showinfo("No Content", "Please open or select a file first.")
            return
        
        # Get prompt and learner profile from the Prompt Config tab
        prompt_tab = self.parent.prompt_tab
        prompt_text_widget = None
        learner_profile = None
        profile_name = None
        
        # Improved prompt finding logic
        # Find scrolledtext widgets in the prompt tab as candidates for the prompt text widget
        prompt_text_candidates = []
        
        # First, search for all scrolledtext widgets in the tab
        def find_scrolledtext_widgets(parent_widget):
            widgets = []
            for child in parent_widget.winfo_children():
                if isinstance(child, scrolledtext.ScrolledText):
                    widgets.append(child)
                elif child.winfo_children():
                    widgets.extend(find_scrolledtext_widgets(child))
            return widgets
        
        prompt_text_candidates = find_scrolledtext_widgets(prompt_tab)
        
        # If we have candidates, use the first one as the prompt text widget
        if prompt_text_candidates:
            prompt_text_widget = prompt_text_candidates[0]
        
        # Find combobox widgets to locate the profile selector
        def find_profile_combobox(parent_widget):
            for child in parent_widget.winfo_children():
                if isinstance(child, ttk.Combobox):
                    if hasattr(child, 'winfo_name') and 'profile' in child.winfo_name().lower():
                        return child
                    # If the combobox has a parent with 'profile' in the name, that's likely it
                    parent_name = str(child.master).lower()
                    if 'profile' in parent_name:
                        return child
                elif child.winfo_children():
                    result = find_profile_combobox(child)
                    if result:
                        return result
            return None
            
        profile_combobox = find_profile_combobox(prompt_tab)
        if profile_combobox:
            profile_name = profile_combobox.get()
            if profile_name:
                profiles_dir = os.path.join(str(get_project_root()), "showup-editor-ui", "profiles")
                profile_path = os.path.join(profiles_dir, profile_name)
                if os.path.exists(profile_path):
                    try:
                        with open(profile_path, 'r', encoding='utf-8') as f:
                            learner_profile = f.read()
                    except Exception as e:
                        logger.error(f"Error reading learner profile: {str(e)}")
        
        if not prompt_text_widget:
            # Fallback to a more direct approach
            for widget in prompt_tab.winfo_children():
                if isinstance(widget, ttk.LabelFrame) and "prompt" in widget.cget("text").lower():
                    for child in widget.winfo_children():
                        if isinstance(child, scrolledtext.ScrolledText):
                            prompt_text_widget = child
                            break
                    if prompt_text_widget:
                        break
        
        if not prompt_text_widget:
            messagebox.showinfo("No Prompt", "Could not find prompt in Prompt Config tab. Please make sure you have a prompt configured.")
            return
        
        custom_prompt = prompt_text_widget.get(1.0, tk.END).strip()
        if not custom_prompt:
            messagebox.showinfo("No Prompt", "Please enter a prompt in the Prompt Config tab.")
            return
            
        # Get any additional instructions
        additional_instructions = self.custom_prompt_text.get(1.0, tk.END).strip()
        if additional_instructions:
            custom_prompt += "\n\nAdditional Instructions:\n" + additional_instructions
            
        # Add information about what files were processed if multiple files were used
        if len(file_paths) > 1:
            file_names = [os.path.basename(path) for path in file_paths]
            file_list_str = "\n- ".join(file_names)
            custom_prompt += f"\n\nFiles Processed:\n- {file_list_str}"
        
        # Update UI
        self.generate_btn.config(state="disabled")
        self.generate_progress.start()
        self.generated_content_text.delete(1.0, tk.END)
        self.generated_content_text.insert(tk.END, "Generating content... Please wait.")
        self.thinking_text.delete(1.0, tk.END)
        
        # Start generation thread - Note: No context generation step
        self.generation_thread = threading.Thread(
            target=self._generate_custom_content_thread,
            args=(file_content, custom_prompt, learner_profile)
        )
        self.generation_thread.daemon = True
        self.generation_thread.start()
    
    def _generate_custom_content_thread(self, file_content, custom_prompt, learner_profile):
        """Thread function for generating custom content."""
        try:
            # Get selected model
            model = self.generate_model_var.get()
            
            # Look for system prompt and other configuration in prompt_config.json
            system_prompt = ""
            config_path = os.path.join(str(get_project_root()), "showup-editor-ui", "data", "prompt_config.json")
            
            temperature = 0.2  # Default temperature
            max_tokens = 12000  # Minimum token limit to prevent content cutoff
            
            try:
                if os.path.exists(config_path):
                    import json
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                        if "system" in config_data:
                            system_prompt = config_data["system"]
                            logger.info("Using system prompt from prompt configuration")
                        
                        # Get other settings if available
                        if "temperature" in config_data:
                            temperature = config_data["temperature"]
                        if "max_tokens" in config_data:
                            # Ensure max_tokens is never below 12000 to prevent content cutoff
                            max_tokens = max(12000, config_data["max_tokens"])
            except Exception as e:
                logger.error(f"Error loading configuration from config: {str(e)}")
            
            # Create the user prompt - this should include BOTH:
            # 1. The custom prompt for the target learner
            # 2. The content to be enhanced
            user_prompt = custom_prompt + "\n\n" + f"""
# Content to Enhance:

{file_content}
"""
            
            # Log what we're doing
            logger.info(f"Generating content with model: {model}")
            logger.info(f"Using system prompt: {system_prompt}")
            logger.info(f"Temperature: {temperature}")
            
            # Generate content with the proper structure
            result = generate_content_with_claude(
                prompt=user_prompt,
                system_prompt=system_prompt,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract content and thinking
            if isinstance(result, dict):
                content = result.get("content", "")
                thinking = result.get("thinking", "")
            else:
                content = result
                thinking = ""
            
            # Store generated content
            self.generated_content = content
            
            # Update UI
            self.parent.after(0, lambda: self._update_generated_content_ui(content, thinking))
            
        except Exception as e:
            logger.error(f"Error generating content: {str(e)}")
            self.parent.after(0, lambda: self._update_generated_content_ui(None, None, error=True))
    
    def _update_generated_content_ui(self, content, thinking="", error=False):
        """Update the UI after content generation."""
        self.generate_progress.stop()
        self.generate_btn.config(state="normal")
        
        if error:
            self.generated_content_text.delete(1.0, tk.END)
            self.generated_content_text.insert(tk.END, "Error generating content. Please try again.")
            return
        
        self.generated_content_text.delete(1.0, tk.END)
        self.generated_content_text.insert(tk.END, content if content else "No content generated.")
        
        self.thinking_text.delete(1.0, tk.END)
        self.thinking_text.insert(tk.END, thinking if thinking else "No thinking process available.")
    
    def save_generated_content(self):
        """Save the generated content to a file."""
        if not self.generated_content:
            messagebox.showinfo("No Content", "Please generate content first.")
            return
        
        # Get output directory
        output_dir = self.output_dir_var.get()
        if not output_dir:
            output_dir = filedialog.askdirectory(title="Select Output Directory")
            if not output_dir:
                return
            self.output_dir_var.set(output_dir)
        
        # Ensure directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Get filename
        filename = filedialog.asksaveasfilename(
            initialdir=output_dir,
            title="Save Generated Content",
            filetypes=[("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")],
            defaultextension=".md"
        )
        
        if not filename:
            return
        
        # Save content
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.generated_content)
            
            messagebox.showinfo("Save Successful", f"Content saved to {filename}")
            logger.info(f"Generated content saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving generated content: {str(e)}")
            messagebox.showerror("Save Error", f"Error saving content: {str(e)}")
