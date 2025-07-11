"""Lesson Preview Panel for ClaudeAIPanel"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import logging

# Import the Learning Context Manager
from .learning_context_manager import LearningContextManager

# Get logger
logger = logging.getLogger("output_library_editor")

class LessonPreviewPanel:
    """Panel for previewing lesson flow from a student's perspective."""
    
    def __init__(self, parent):
        """
        Initialize the lesson preview panel.
        
        Args:
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        self.processing = False
        self.selected_files = []
        
        # Initialize the learning context manager
        self.context_manager = LearningContextManager()
        
    def setup_lesson_preview_tab(self):
        """Set up the lesson preview tab with UI elements."""
        tab = self.parent.lesson_preview_tab
        
        # Main frame for all controls
        main_frame = ttk.Frame(tab, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configuration frame
        config_frame = ttk.LabelFrame(main_frame, text="Lesson Preview Configuration", padding=10)
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Instructions
        instructions = ttk.Label(config_frame, 
                              text="Select .md files in the library panel, choose a learner profile, and add special instructions.")
        instructions.pack(anchor="w", padx=5, pady=5)
        
        # Profile selector
        profile_frame = ttk.Frame(config_frame)
        profile_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(profile_frame, text="Learner Profile:").pack(side=tk.LEFT, padx=5)
        
        # Use the profiles from the parent
        self.profile_var = tk.StringVar()
        self.profile_dropdown = ttk.Combobox(profile_frame, 
                                          textvariable=self.profile_var,
                                          state="readonly",
                                          width=30)
        self.profile_dropdown.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Set up the profile dropdown values
        self._update_profile_dropdown()
        
        # Special instructions
        instructions_frame = ttk.LabelFrame(config_frame, text="Special Instructions", padding=5)
        instructions_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.instructions_box = scrolledtext.ScrolledText(instructions_frame, height=4, wrap=tk.WORD)
        self.instructions_box.pack(fill=tk.X, expand=True, padx=5, pady=5)
        self.instructions_box.insert(tk.END, "Focus on concept transitions and identify any confusing parts.")
        
        # Selected files display
        files_frame = ttk.LabelFrame(config_frame, text="Selected Files", padding=5)
        files_frame.pack(fill=tk.X, pady=5, padx=5)
        
        self.files_display = scrolledtext.ScrolledText(files_frame, height=4, wrap=tk.WORD, state="disabled")
        self.files_display.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        # Control buttons
        button_frame = ttk.Frame(config_frame, padding=5)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.refresh_button = ttk.Button(
            button_frame, 
            text="Refresh Selected Files", 
            command=self._refresh_selected_files
        )
        self.refresh_button.pack(side=tk.LEFT, padx=10)
        
        self.process_button = ttk.Button(
            button_frame, 
            text="Start Lesson Preview", 
            command=self.on_run_preview,
            style="Accent.TButton"
        )
        self.process_button.pack(side=tk.LEFT, padx=10)
        
        # Force refresh option
        self.force_refresh_var = tk.BooleanVar(value=False)
        self.force_refresh_cb = ttk.Checkbutton(
            button_frame,
            text="Force API refresh (bypass cache)",
            variable=self.force_refresh_var
        )
        self.force_refresh_cb.pack(side=tk.RIGHT, padx=10)
        
        # Notes display
        notes_frame = ttk.LabelFrame(main_frame, text="Student Notes", padding=10)
        notes_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.notes_pane = scrolledtext.ScrolledText(notes_frame, height=15, wrap=tk.WORD)
        self.notes_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def _update_profile_dropdown(self):
        """Update the profile dropdown with available profiles."""
        if hasattr(self.parent, 'profiles') and self.parent.profiles:
            profile_names = list(self.parent.profiles.keys())
            self.profile_dropdown['values'] = profile_names
            
            # Set the default value to the first profile
            if profile_names and not self.profile_var.get():
                self.profile_var.set(profile_names[0])
        else:
            # If no profiles are available, set a default
            self.profile_dropdown['values'] = ["Default"]
            self.profile_var.set("Default")
            
    def _refresh_selected_files(self):
        """Refresh the list of selected files from the library panel."""
        self.selected_files = []
        
        if hasattr(self.parent, "file_tree") and self.parent.file_tree:
            for item_id in self.parent.file_tree.selection():
                item_values = self.parent.file_tree.item(item_id, "values")
                if item_values and len(item_values) > 1:
                    path = item_values[0]
                    item_type = item_values[1] if len(item_values) > 1 else ""
                    
                    # Only process markdown files, not directories
                    if item_type != "directory" and os.path.isfile(path) and path.lower().endswith(".md"):
                        self.selected_files.append(path)
        
        # Update the files display
        self._update_files_display()
        
        # Show a message if no files are selected
        if not self.selected_files:
            messagebox.showinfo("No Files Selected", "Please select markdown (.md) files in the library panel first.")
            
    def _update_files_display(self):
        """Update the files display with the selected files."""
        # Enable the text widget for editing
        self.files_display.config(state=tk.NORMAL)
        
        # Clear the current content
        self.files_display.delete(1.0, tk.END)
        
        # Add each file path
        for file_path in self.selected_files:
            file_name = os.path.basename(file_path)
            self.files_display.insert(tk.END, f"{file_name}\n")
        
        # Disable the text widget again
        self.files_display.config(state=tk.DISABLED)
            
    def get_selected_markdown_files(self):
        """Get the currently selected markdown files."""
        return self.selected_files
    
    def on_run_preview(self):
        """Run the lesson preview process on selected files."""
        # Get selected files
        files = self.get_selected_markdown_files()
        
        # Check if any files are selected
        if not files:
            messagebox.showinfo("No Files Selected", "Please select markdown (.md) files in the library panel first.")
            return
        
        # Get the selected profile
        profile_name = self.profile_var.get()
        if not profile_name:
            messagebox.showinfo("No Profile Selected", "Please select a learner profile.")
            return
        
        # Get the profile data
        profile = self.parent.profiles.get(profile_name)
        if not profile:
            messagebox.showerror("Error", f"Could not find profile: {profile_name}")
            return
        
        # Get special instructions
        instructions = self.instructions_box.get(1.0, tk.END).strip()
        
        # Clear the notes pane
        self.notes_pane.delete(1.0, tk.END)
        self.notes_pane.insert(tk.END, "Processing...\n\n")
        
        # Set processing flag
        self.processing = True
        self.process_button.config(state=tk.DISABLED)
        
        # Run the preview in a separate thread
        threading.Thread(target=self._run_preview_thread, 
                        args=(files, profile, instructions),
                        daemon=True).start()
    
    def _run_preview_thread(self, files, profile, instructions):
        """Run the preview process in a separate thread."""
        try:
            notes = []
            profile_name = profile.get('name', 'Default')
            
            # Update UI with processing status
            self._update_status(f"Starting preview of {len(files)} lesson files...")
            
            # Process each file in sequence, maintaining learning context
            for i, path in enumerate(files):
                file_name = os.path.basename(path)
                self._update_status(f"Processing file {i+1}/{len(files)}: {file_name}")
                
                # Load the markdown content
                content = self._load_markdown(path)
                
                # Load the current learning context
                learning_context = self.context_manager.load_learning_context(profile_name)
                
                # Run AI simulation with learning context
                note = self._run_ai_simulation(
                    text=content,
                    profile=profile,
                    instructions=instructions,
                    learning_context=learning_context,
                    file_path=path
                )
                
                # Add to notes
                notes.append(f"## {os.path.basename(path)}\n{note}")
            
            # Update the notes pane
            self._update_notes("\n\n".join(notes))
            self._update_status("Preview completed successfully!")
            
        except Exception as e:
            self._update_status(f"Error running preview: {str(e)}")
        finally:
            # Reset processing flag
            self.processing = False
            self._enable_process_button()
    
    def _update_status(self, message):
        """Update the status message in the notes pane."""
        # Schedule the update on the main thread
        self.parent.after(0, lambda: self.parent.update_status(message))
    
    def _update_notes(self, text):
        """Update the notes pane with the generated notes."""
        # Schedule the update on the main thread
        self.parent.after(0, lambda: self._set_notes_text(text))
    
    def _set_notes_text(self, text):
        """Set the text in the notes pane."""
        self.notes_pane.delete(1.0, tk.END)
        self.notes_pane.insert(tk.END, text)
    
    def _enable_process_button(self):
        """Enable the process button on the main thread."""
        # Schedule the update on the main thread
        self.parent.after(0, lambda: self.process_button.config(state=tk.NORMAL))
    
    def _load_markdown(self, file_path):
        """Load markdown content from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error loading markdown file {file_path}: {str(e)}")
            raise
    
    def _run_ai_simulation(self, text, profile, instructions, learning_context=None, file_path=None):
        """Run the AI simulation on the lesson content."""
        try:
            # Get the parent's API interface - required for Claude integration
            if hasattr(self.parent, 'prompt_manager') and hasattr(self.parent.prompt_manager, 'call_claude_api'):
                # Construct a prompt for the AI following the reference workflow structure
                # Get profile description if available, otherwise use a default
                profile_description = profile.get('description', 'A student learning this material.')
                
                # Start with basic system prompt
                system_prompt = f"{profile['system']}\n\nYou are simulating a student with the following profile and characteristics:\n\n{profile_description}\n\nAs you review the lesson content, you should consider your background knowledge, learning style, and typical responses to new information."
                
                # Add learning context if available
                try:
                    if learning_context and len(learning_context.get('lessons_completed', [])) > 0:
                        # Format the learning context for the prompt
                        context_text = self.context_manager.format_context_for_prompt(learning_context)
                        system_prompt += f"\n\n{context_text}"
                        
                        # Add specific instructions about how to use the context
                        system_prompt += "\n\nBased on this learning history, adjust your response appropriately. If concepts are repeated from previous lessons, express frustration or boredom. If questions from previous lessons remain unanswered in this new content, point this out. If the new content builds on previous knowledge in a helpful way, express appreciation for this progression. Remember that as a continuing student, you should react naturally to repetition, gaps, or effective scaffolding in the curriculum."
                except Exception as e:
                    logger.error(f"Error formatting learning context: {str(e)}")
                
                # Create a more structured prompt with clear output guidance based on reference workflow
                user_prompt = f"""I'm going to show you a lesson document. Your task is to simulate me as a student learning from this material.

Here's the lesson content I need to study:

{text}

{instructions}

Please analyze this content from my perspective as a student and respond in the following format:

## Key Concepts
- [List 3-5 key concepts I would understand from this lesson]

## Questions
- [List 2-3 specific questions I would have about the material based on my background]

## Understanding Level
[Rate my understanding from 1-5, where 1 is confused and 5 is confident, and explain why]

## Emotional Response
[Share how I would feel about this material in 2-3 sentences]

## Learning Flow Analysis
- [Analyze how the lesson progression worked for me]
- [Identify any gaps or jumps in the explanation that affected my understanding]
- [Note any particularly effective teaching moments]

## Improvement Suggestions
- [List 2-3 specific ways this lesson could be improved for me]

For my emotional response, consider:
- How confident I would feel with this material based on my profile
- What aspects would be most interesting or engaging to me personally
- What parts would be frustrating or confusing given my background
- How relevant this material feels to my learning goals"""
                
                # Get force refresh setting
                force_refresh = self.force_refresh_var.get() if hasattr(self, 'force_refresh_var') else False
                
                # Call the Claude API using the parent's prompt manager
                if force_refresh:
                    self._update_status(f"Analyzing lesson content with Claude {self.parent.edit_model} (FRESH API CALL)...")
                else:
                    self._update_status(f"Analyzing lesson content with Claude {self.parent.edit_model}...")
                    
                response = self.parent.prompt_manager.call_claude_api(
                    system=system_prompt,
                    prompt=user_prompt,
                    model=self.parent.edit_model,  # Use the more powerful model for this complex task
                    force_refresh=force_refresh)  # Pass the force refresh flag
                
                # Get the response text
                response_text = response.strip()
                
                # Update the learning context if we have a valid file path and profile
                if file_path and response_text and 'error' not in response_text.lower()[:50]:
                    profile_name = profile.get('name', 'Default')
                    try:
                        # Update the learning context with what was learned in this lesson
                        self.context_manager.update_from_lesson(profile_name, file_path, response_text)
                        logger.info(f"Updated learning context for {profile_name} with {os.path.basename(file_path)}")
                    except Exception as e:
                        logger.error(f"Error updating learning context: {str(e)}")
                
                # Return the structured response
                return response_text
            else:
                # If API access is not available, provide clear error message
                error_msg = "Claude API access is not available. Please check your API key and connection."
                logger.error(error_msg)
                return error_msg
        except Exception as e:
            error_msg = f"Error running AI simulation: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def _generate_placeholder_analysis(self, text):
        """Generate a placeholder analysis for testing."""
        # Just a simple placeholder that extracts headers and counts paragraphs
        import re
        
        # Extract headers
        headers = re.findall(r'^#+\s+(.+)$', text, re.MULTILINE)
        
        # Count paragraphs (text blocks separated by blank lines)
        paragraphs = [p for p in re.split(r'\n\s*\n', text) if p.strip()]
        
        # Generate a simple analysis
        analysis = """### Student Notes

Key concepts I understood:
- This lesson covered several important topics based on the headers
- The content was structured in a logical sequence

Points that were confusing:
- Some concepts might need more examples
- The connections between sections could be clearer

Questions I have:
- How does this relate to previous lessons?
- Where can I practice these concepts more?

Suggestions for improvement:
- Add more visual elements
- Include interactive exercises
- Provide a summary at the end"""
        
        # Add some stats
        stats = f"\n\n### Content Stats\n- Found {len(headers)} section headers\n- Contains approximately {len(paragraphs)} paragraphs\n"
        
        return analysis + stats
