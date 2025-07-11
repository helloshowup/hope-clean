"""Document Creator Module for ClaudeAIPanel"""

import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import logging
from typing import List, Any, Optional

# Dynamic import of cache_utils.py from root directory
from importlib.util import spec_from_file_location, module_from_spec

# Path to cache_utils.py in the root directory
cache_utils_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..', 'cache_utils.py'))

# Import cache_utils.py dynamically
spec = spec_from_file_location('cache_utils', cache_utils_path)
cache_utils = module_from_spec(spec)
spec.loader.exec_module(cache_utils)

# Get the required function
get_cache_instance = cache_utils.get_cache_instance

# Use the installed claude_api package
from claude_api import regenerate_markdown_with_claude

# Get logger
logger = logging.getLogger("output_library_editor")

class DocumentCreator:
    """Handles document creation from multiple markdown sources for the ClaudeAIPanel."""
    
    def __init__(self, doc_creator_tab: ttk.Frame, parent: Any):
        """
        Initialize the document creator.
        
        Args:
            doc_creator_tab: The document creator tab
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        self.doc_creator_tab = doc_creator_tab
        self.source_files: List[str] = []  # List to store source markdown files
        self.generated_content: str = ""
        self.generation_thread: Optional[threading.Thread] = None
        self.output_dir: str = ""
        
    def setup_doc_creator_tab(self) -> None:
        """Set up the document creator tab."""
        # Create the main frame for this tab
        main_frame = ttk.Frame(self.doc_creator_tab, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Create side-by-side layout
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left pane for source file selection
        source_frame = ttk.LabelFrame(paned_window, text="Source Files")
        paned_window.add(source_frame, weight=1)
        
        # Right pane for configuration and output
        config_frame = ttk.LabelFrame(paned_window, text="Document Generation")
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
        
        # File movement buttons
        move_btn_frame = ttk.Frame(source_frame)
        move_btn_frame.pack(fill="x", padx=5, pady=5)
        
        move_up_btn = ttk.Button(move_btn_frame, text="↑", width=3, command=self.move_file_up)
        move_up_btn.pack(side=tk.LEFT, padx=5)
        
        move_down_btn = ttk.Button(move_btn_frame, text="↓", width=3, command=self.move_file_down)
        move_down_btn.pack(side=tk.LEFT, padx=5)
        
        # Configuration components
        
        # Output filename frame
        output_file_frame = ttk.Frame(config_frame)
        output_file_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(output_file_frame, text="Output Filename:").pack(side=tk.LEFT, padx=5)
        
        self.output_filename_var = tk.StringVar(value="generated_document.md")
        output_filename_entry = ttk.Entry(output_file_frame, textvariable=self.output_filename_var, width=30)
        output_filename_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=5)
        
        # Output directory frame
        output_dir_frame = ttk.Frame(config_frame)
        output_dir_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(output_dir_frame, text="Output Directory:").pack(side=tk.LEFT, padx=5)
        
        self.output_dir_var = tk.StringVar()
        output_dir_entry = ttk.Entry(output_dir_frame, textvariable=self.output_dir_var, width=30)
        output_dir_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=5)
        
        browse_btn = ttk.Button(output_dir_frame, text="Browse...", command=self._browse_output_dir)
        browse_btn.pack(side=tk.RIGHT, padx=5)
        
        # Description of functionality
        description_frame = ttk.LabelFrame(config_frame, text="About")
        description_frame.pack(fill="x", padx=5, pady=5)
        
        description = ttk.Label(description_frame, text="This tool will create new documents by analyzing multiple source files.\n\n• Uses the prompt from the 'Prompt Config' tab\n• Uses Claude 3.7 to generate new documents\n• Source files will be processed in the order listed\n• The generated documents will be saved to the specified location")
        description.pack(padx=10, pady=10)
        
        # Additional instructions frame
        instructions_frame = ttk.LabelFrame(config_frame, text="Additional Instructions (Optional)")
        instructions_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.instructions_text = scrolledtext.ScrolledText(instructions_frame, wrap=tk.WORD, height=5)
        self.instructions_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # View prompt button
        view_prompt_btn = ttk.Button(config_frame, text="View Current Prompt", command=self._show_current_prompt)
        view_prompt_btn.pack(pady=5)
        
        # Generate button
        generate_frame = ttk.Frame(config_frame)
        generate_frame.pack(fill="x", padx=5, pady=10)
        
        self.generate_btn = ttk.Button(generate_frame, text="Generate Documents", command=self.generate_document)
        self.generate_btn.pack(side=tk.LEFT, padx=5)
        
        self.cancel_btn = ttk.Button(generate_frame, text="Cancel", command=self.cancel_generation, state="disabled")
        self.cancel_btn.pack(side=tk.LEFT, padx=5)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(main_frame, text="Preview")
        preview_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Preview text area
        self.preview_text = scrolledtext.ScrolledText(preview_frame, wrap=tk.WORD)
        self.preview_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Save button
        self.save_btn = ttk.Button(preview_frame, text="Save Document", command=self.save_document)
        self.save_btn.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # Progress bar and status
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var)
        self.status_label.pack(pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        
        # Log setup completion
        logger.info("Document creator tab setup")
    
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
            else:
                messagebox.showinfo("No Files", "No markdown files found in the selected directory.")
    
    def clear_sources(self) -> None:
        """Clear all source files."""
        self.source_files = []
        self.source_files_listbox.delete(0, tk.END)
        logger.info("Cleared source files")
    
    def move_file_up(self) -> None:
        """Move the selected file up in the list."""
        selected_indices = self.source_files_listbox.curselection()
        if not selected_indices or selected_indices[0] == 0:
            return
            
        index = selected_indices[0]
        file = self.source_files[index]
        
        # Remove from current position
        self.source_files.pop(index)
        self.source_files_listbox.delete(index)
        
        # Insert at new position
        new_index = index - 1
        self.source_files.insert(new_index, file)
        self.source_files_listbox.insert(new_index, file)
        
        # Reselect the item
        self.source_files_listbox.selection_set(new_index)
    
    def move_file_down(self) -> None:
        """Move the selected file down in the list."""
        selected_indices = self.source_files_listbox.curselection()
        if not selected_indices or selected_indices[0] == len(self.source_files) - 1:
            return
            
        index = selected_indices[0]
        file = self.source_files[index]
        
        # Remove from current position
        self.source_files.pop(index)
        self.source_files_listbox.delete(index)
        
        # Insert at new position
        new_index = index + 1
        self.source_files.insert(new_index, file)
        self.source_files_listbox.insert(new_index, file)
        
        # Reselect the item
        self.source_files_listbox.selection_set(new_index)
    
    def _browse_output_dir(self) -> None:
        """Browse for output directory."""
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir_var.set(directory)
    
    def _show_current_prompt(self) -> None:
        """Show the current prompt configuration."""
        # Check if prompt manager is available
        if not hasattr(self.parent, "prompt_manager") or not self.parent.prompt_manager.selected_prompt:
            messagebox.showinfo("No Prompt", "No prompt is currently selected.")
            return
            
        # Get prompt content
        prompt_text = ""
        if self.parent.prompt_manager.selected_prompt == "[Custom Prompt]":
            prompt_text = self.parent.prompt_manager.prompt_content.get("1.0", tk.END)
        else:
            prompt_name = self.parent.prompt_manager.selected_prompt
            if prompt_name in self.parent.prompt_manager.prompts:
                prompt_text = self.parent.prompt_manager.prompts[prompt_name]["content"]
        
        # Show prompt in a dialog
        if prompt_text:
            dialog = tk.Toplevel(self.parent)
            dialog.title("Current Prompt")
            dialog.geometry("600x400")
            
            prompt_display = scrolledtext.ScrolledText(dialog, wrap=tk.WORD)
            prompt_display.pack(fill="both", expand=True, padx=10, pady=10)
            prompt_display.insert("1.0", prompt_text)
            prompt_display.config(state="disabled")
            
            close_btn = ttk.Button(dialog, text="Close", command=dialog.destroy)
            close_btn.pack(pady=10)
        else:
            messagebox.showinfo("No Prompt", "No prompt content found.")
    
    def generate_document(self) -> None:
        """Generate new documents from the source files."""
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
        
        # Get current prompt from the prompt manager
        if not hasattr(self.parent, "prompt_manager") or not self.parent.prompt_manager.selected_prompt:
            messagebox.showwarning("No Prompt", "Please select a prompt in the Prompt Config tab.")
            return
            
        # Get prompt content
        prompt_text = ""
        if self.parent.prompt_manager.selected_prompt == "[Custom Prompt]":
            prompt_text = self.parent.prompt_manager.prompt_content.get("1.0", tk.END)
        else:
            prompt_name = self.parent.prompt_manager.selected_prompt
            if prompt_name in self.parent.prompt_manager.prompts:
                prompt_text = self.parent.prompt_manager.prompts[prompt_name]["content"]
        
        if not prompt_text:
            messagebox.showwarning("No Prompt", "No prompt content found.")
            return
        
        # Get additional instructions
        additional_instructions = self.instructions_text.get("1.0", tk.END).strip()
        
        # Start generation in a separate thread
        self.status_var.set("Generating documents...")
        self.generate_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.progress_bar.start()
        
        self.generation_thread = threading.Thread(
            target=self._generate_document_thread,
            args=(prompt_text, additional_instructions)
        )
        self.generation_thread.daemon = True
        self.generation_thread.start()
    
    def _generate_document_thread(self, prompt_text: str, additional_instructions: str) -> None:
        """Thread function to generate the documents."""
        try:
            # Process each file individually
            for file_path in self.source_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                        filename = os.path.basename(file_path)
                        
                        # Create system and user prompts
                        system_prompt = "You are an AI writing assistant helping to create a new document based on a source file."
                        
                        # Ensure the content isn't too large for the API call
                        content_truncated = content
                        if len(content) > 100000:  # If content is very large
                            logger.warning(f"Content for {filename} is too large, truncating to 100,000 characters")
                            content_truncated = content[:100000]
                            # Add a note about truncation
                            content_truncated += "\n\n[Note: Content was truncated due to size limitations.]"
                        
                        user_prompt = f"""Create a new document based on the following source file:\n
{content_truncated}\n
Use this prompt as your guide:
{prompt_text}\n
Additional instructions:
{additional_instructions}\n
Generate a well-structured, comprehensive document that incorporates the information from the source file.
"""
                        
                        # Call Claude API
                        logger.info(f"Calling Claude API to generate document for {filename}...")
                        try:
                            response = regenerate_markdown_with_claude(
                                markdown_text=content_truncated,
                                instructions=prompt_text,
                                context=additional_instructions,
                                model="claude-opus-4-20250514",
                                temperature=0.5
                            )
                            
                            # Handle string response
                            if isinstance(response, str):
                                content = response
                                thinking = ""
                            # Handle dict response
                            elif isinstance(response, dict) and "content" in response:
                                content = response.get("content", "")
                                thinking = response.get("thinking", "")
                            else:
                                error_msg = f"Unexpected response format from Claude API: {type(response)}"
                                logger.error(error_msg)
                                self.parent.after(0, lambda err=error_msg: messagebox.showerror(
                                    "Generation Error", f"Error generating document for {filename}: {err}"
                                ))
                                continue
                            
                            # Save the generated document
                            base_name = os.path.splitext(filename)[0]  # Remove .md extension
                            output_filename = f"{base_name}_generated.md"
                            output_path = os.path.join(self.output_dir_var.get(), output_filename)
                            with open(output_path, 'w', encoding='utf-8') as file:
                                file.write(content)
                            
                            logger.info(f"Document generated and saved for {filename}")
                            
                            # Update UI from main thread
                            self.parent.after(0, lambda content_text=content: self._update_preview(content_text))
                            
                        except Exception as api_error:
                            error_msg = str(api_error)
                            logger.error(f"API error for {filename}: {error_msg}")
                            self.parent.after(0, lambda file=filename, err=error_msg: messagebox.showerror(
                                "API Error", f"Error generating document for {file}: {err}"
                            ))
                            
                except Exception as file_error:
                    error_msg = str(file_error)
                    logger.error(f"Error processing file {file_path}: {error_msg}")
                    self.parent.after(0, lambda path=file_path, err=error_msg: messagebox.showerror(
                        "File Error", f"Error processing file {path}: {err}"
                    ))
        except Exception as general_error:
            error_msg = str(general_error)
            logger.error(f"General error generating documents: {error_msg}")
            self.parent.after(0, lambda err=error_msg: messagebox.showerror(
                "Generation Error", f"Error generating documents: {err}"
            ))
        finally:
            # Update UI from main thread
            self.parent.after(0, self._reset_ui_after_generation)
    
    def _update_preview(self, content: str) -> None:
        """Update the preview text widget with the generated content."""
        try:
            # Make sure the widget is in the correct state for modification
            current_state = str(self.preview_text.cget("state"))
            if current_state == "disabled":
                self.preview_text.config(state="normal")
                
            # Update content
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, content)
            
            # Restore original state if it was disabled
            if current_state == "disabled":
                self.preview_text.config(state="disabled")
                
            logger.info("Updated document preview with generated content")
        except Exception as e:
            logger.error(f"Error updating document preview: {str(e)}")
    
    def _reset_ui_after_generation(self) -> None:
        """Reset the UI after generation is complete."""
        self.status_var.set("Generation complete")
        self.generate_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.progress_bar.stop()
        self.progress_var.set(100)
        
        # Show completion message
        messagebox.showinfo("Success", f"All documents have been generated and saved to {self.output_dir_var.get()}")
    
    def cancel_generation(self) -> None:
        """Cancel the document generation."""
        if self.generation_thread and self.generation_thread.is_alive():
            # We can't directly stop the thread, but we can indicate it should stop
            self.status_var.set("Cancelling...")
            # The thread will have to check a flag or we'll have to wait for it to complete
    
    def save_document(self) -> None:
        """Save the currently previewed document."""
        if not self.generated_content:
            messagebox.showwarning("No Content", "No document has been generated yet.")
            return
            
        output_dir = self.output_dir_var.get()
        if not output_dir:
            output_dir = filedialog.askdirectory(title="Select Output Directory")
            if not output_dir:
                return
            self.output_dir_var.set(output_dir)
        
        # Ask for a filename
        output_filename = filedialog.asksaveasfilename(
            initialdir=output_dir,
            title="Save Document As",
            filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")],
            defaultextension=".md"
        )
        
        if not output_filename:
            return
        
        try:
            with open(output_filename, 'w', encoding='utf-8') as file:
                file.write(self.generated_content)
                
            self.status_var.set(f"Document saved to {output_filename}")
            messagebox.showinfo("Success", f"Document saved to {output_filename}")
            
            # Open the file in the default editor
            if messagebox.askyesno("Open File", "Would you like to open the generated document?"):
                try:
                    os.startfile(output_filename)
                except Exception as e:
                    logger.error(f"Error opening file: {str(e)}")
                    messagebox.showerror("Error", f"Error opening file: {str(e)}")
        except Exception as e:
            logger.error(f"Error saving document: {str(e)}")
            messagebox.showerror("Error", f"Error saving document: {str(e)}")
