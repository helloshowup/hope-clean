"""Prompt Management Module for ClaudeAIPanel"""

import os
import glob
import json
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import logging
import requests
import time
import datetime
from pathlib import Path
from dotenv import load_dotenv
from .path_utils import get_project_root

# Import config manager
from .config_manager import config_manager

# Load environment variables from .env file
env_path = os.path.join(str(get_project_root()), '.env')
load_dotenv(env_path)

# Get logger
logger = logging.getLogger("output_library_editor")

class PromptManager:
    """Handles prompt and profile loading/management for ClaudeAIPanel."""
    
    def __init__(self, parent):
        """Initialize the prompt manager.
        
        Args:
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        # Use the prompt library path from config_manager
        self.prompts_dir = config_manager.get_setting("library_prompts_path")
        showup_root = Path(
            os.environ.get("SHOWUP_ROOT", get_project_root())
        )
        self.profiles_dir = str(
            showup_root / "showup-library" / "Student personas"
        )
        
        # Ensure prompt directory exists
        if not os.path.exists(self.prompts_dir):
            os.makedirs(self.prompts_dir, exist_ok=True)
            logger.info(f"Created prompts directory: {self.prompts_dir}")
        os.makedirs(self.profiles_dir, exist_ok=True)
        
        # Initialize variables
        self.prompts = {}
        self.prompt_files = []
        self.selected_prompt = None
        self.selected_profile = None
    
    def setup_prompt_tab(self):
        """Set up the prompt configuration tab."""
        tab = self.parent.prompt_tab
        
        # Create prompt selection frame
        prompt_frame = ttk.LabelFrame(tab, text="Select Prompt")
        prompt_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Add action buttons to the top of the prompt frame
        refresh_frame = ttk.Frame(prompt_frame)
        refresh_frame.pack(fill="x", padx=5, pady=5, anchor="ne")
        
        # New Prompt button
        new_prompt_btn = ttk.Button(refresh_frame, text="+ New Prompt", command=self.create_new_prompt)
        new_prompt_btn.pack(side="right", padx=(0, 5))
        
        # Refresh button
        refresh_btn = ttk.Button(refresh_frame, text="↻ Refresh Resources", command=self.refresh_resources)
        refresh_btn.pack(side="right")
        
        # Create prompt selection listbox
        self.prompt_list = tk.Listbox(prompt_frame, height=5, exportselection=False)
        self.prompt_list.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.prompt_list.bind("<<ListboxSelect>>", self.on_prompt_file_selected)
        
        # Add scrollbar to prompt list
        prompt_scrollbar = ttk.Scrollbar(prompt_frame)
        prompt_scrollbar.pack(side="right", fill="y")
        self.prompt_list.config(yscrollcommand=prompt_scrollbar.set)
        prompt_scrollbar.config(command=self.prompt_list.yview)
        
        # Create prompt content display
        prompt_content_frame = ttk.LabelFrame(tab, text="Prompt Preview")
        prompt_content_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Add prompt content text area
        self.prompt_content = scrolledtext.ScrolledText(prompt_content_frame, wrap=tk.WORD, height=10)
        self.prompt_content.pack(fill="both", expand=True, padx=5, pady=5)
        self.prompt_content.config(state="disabled")
        
        # Add buttons for prompt actions
        button_frame = ttk.Frame(prompt_content_frame)
        button_frame.pack(side="right", padx=5, pady=5)
        
        # Add "Edit Prompt" button
        self.edit_prompt_btn = ttk.Button(button_frame, text="Edit Prompt", command=self.edit_prompt_dialog)
        self.edit_prompt_btn.pack(side="right", padx=5)
        
        # Add "View Full Prompt" button
        self.view_full_prompt_btn = ttk.Button(button_frame, text="View Full Prompt", command=self.show_full_prompt_dialog)
        self.view_full_prompt_btn.pack(side="right", padx=5)
        
        # Create learner profile selection frame
        profile_frame = ttk.LabelFrame(tab, text="Select Learner Profile")
        profile_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create profile selection listbox
        self.profile_list = tk.Listbox(profile_frame, height=5, exportselection=False)
        self.profile_list.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.profile_list.bind("<<ListboxSelect>>", self.on_profile_selected)
        
        # Add scrollbar to profile list
        profile_scrollbar = ttk.Scrollbar(profile_frame)
        profile_scrollbar.pack(side="right", fill="y")
        self.profile_list.config(yscrollcommand=profile_scrollbar.set)
        profile_scrollbar.config(command=self.profile_list.yview)
        
        # Create profile content display
        profile_content_frame = ttk.LabelFrame(tab, text="Profile Preview")
        profile_content_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Add profile content text area
        self.profile_content = scrolledtext.ScrolledText(profile_content_frame, wrap=tk.WORD, height=10)
        self.profile_content.pack(fill="both", expand=True, padx=5, pady=5)
        self.profile_content.config(state="disabled")
        
        # Add "View Full Profile" button
        self.view_full_profile_btn = ttk.Button(profile_content_frame, text="View Full Profile", command=self.show_full_profile_dialog)
        self.view_full_profile_btn.pack(side="right", padx=5, pady=5)
        
        # Load prompts with latest settings
        self.load_prompts()
        
        # Load learner profiles
        self.load_learner_profiles()
        
        # Select the first prompt by default
        if len(self.prompt_files) > 0:
            self.prompt_list.selection_set(0)
            self.selected_prompt = self.prompt_files[0]
    
    def refresh_resources(self):
        """Refresh prompt files and profiles from disk."""
        # Re-fetch the prompt directory path from config in case it's been updated
        self.prompts_dir = config_manager.get_setting("library_prompts_path")
        
        # Check if the prompts directory exists
        if not os.path.exists(self.prompts_dir):
            logger.warning(f"Prompt directory does not exist: {self.prompts_dir}")
            messagebox.showwarning("Warning", f"Prompt directory does not exist: {self.prompts_dir}\nPlease set a valid path in the Prompt Library Root field.")
            self.prompt_files = []
        else:
            # Refresh prompt files (search recursively in subdirectories)
            self.prompt_files = []
            
            # Search in main directory
            for file in glob.glob(os.path.join(self.prompts_dir, "*.txt")):
                if os.path.isfile(file) and not os.path.basename(file).startswith("."):
                    self.prompt_files.append(file)
            
            for file in glob.glob(os.path.join(self.prompts_dir, "*.md")):
                if os.path.isfile(file) and not os.path.basename(file).startswith("."):
                    self.prompt_files.append(file)
                    
            # Also search in subdirectories
            for file in glob.glob(os.path.join(self.prompts_dir, "**", "*.txt"), recursive=True):
                if os.path.isfile(file) and not os.path.basename(file).startswith(".") and file not in self.prompt_files:
                    self.prompt_files.append(file)
            
            for file in glob.glob(os.path.join(self.prompts_dir, "**", "*.md"), recursive=True):
                if os.path.isfile(file) and not os.path.basename(file).startswith(".") and file not in self.prompt_files:
                    self.prompt_files.append(file)
                    
            # Update the prompt list
            self.prompt_list.delete(0, tk.END)
            
            # Sort prompts alphabetically but keep custom prompt at the top
            sorted_prompts = sorted([os.path.basename(p) for p in self.prompt_files])
            display_prompts = ["[Custom Prompt]"] + sorted_prompts
            
            for prompt in display_prompts:
                self.prompt_list.insert(tk.END, prompt)
                
            # Select the first prompt by default
            if len(self.prompt_files) > 0:
                self.prompt_list.selection_set(0)
                self.selected_prompt = self.prompt_files[0]
                self.on_prompt_file_selected(None)  # Trigger display update
    
    def load_prompts(self):
        """Load prompts from the prompts directory."""
        # Re-fetch the prompt directory path from config in case it's been updated
        self.prompts_dir = config_manager.get_setting("library_prompts_path")
        
        self.prompts = {}
        self.prompt_files = []
        
        try:
            # First, add a custom prompt option
            self.prompts["[Custom Prompt]"] = {
                "file": None,
                "content": ""
            }
            self.prompt_files.append("[Custom Prompt]")
            
            # Then load from files (including subdirectories)
            if os.path.exists(self.prompts_dir):
                # Find all txt and md files in the prompts directory and its subdirectories
                txt_files = glob.glob(os.path.join(self.prompts_dir, "**", "*.txt"), recursive=True)
                md_files = glob.glob(os.path.join(self.prompts_dir, "**", "*.md"), recursive=True)
                all_files = txt_files + md_files
                
                for prompt_path in all_files:
                    # Get relative path for display
                    rel_path = os.path.relpath(prompt_path, self.prompts_dir)
                    # Use the file name as the prompt name
                    prompt_name = os.path.splitext(os.path.basename(prompt_path))[0]
                    
                    # Add category prefix for files in subdirectories
                    if os.path.dirname(rel_path):
                        category = os.path.dirname(rel_path).replace("\\", "/")
                        display_name = f"{category}/{prompt_name}"
                    else:
                        display_name = prompt_name
                    
                    try:
                        with open(prompt_path, "r", encoding="utf-8") as prompt_file:
                            prompt_content = prompt_file.read()
                            
                            self.prompts[display_name] = {
                                "file": prompt_path,
                                "content": prompt_content
                            }
                            
                            self.prompt_files.append(display_name)
                            
                    except Exception as e:
                        logger.error(f"Error loading prompt file {prompt_path}: {str(e)}")
                
                # Update the prompt list
                self.prompt_list.delete(0, tk.END)
                
                # Sort prompts alphabetically but keep custom prompt at the top
                sorted_prompts = sorted([p for p in self.prompt_files if p != "[Custom Prompt]"])
                display_prompts = ["[Custom Prompt]"] + sorted_prompts
                
                for prompt in display_prompts:
                    self.prompt_list.insert(tk.END, prompt)
                
                # Select the first prompt by default
                if len(self.prompt_files) > 0:
                    self.prompt_list.selection_set(0)
                    self.selected_prompt = self.prompt_files[0]
                    self.on_prompt_file_selected(None)  # Trigger display update
            else:
                logger.warning(f"Prompts directory not found: {self.prompts_dir}")
                
        except Exception as e:
            logger.error(f"Error loading prompts: {str(e)}")
    
    def on_prompt_file_selected(self, event):
        """Handle selection of a prompt file."""
        try:
            selection = self.prompt_list.curselection()
            if not selection:
                return
            
            index = selection[0]
            prompt_name = self.prompt_list.get(index)
            self.selected_prompt = prompt_name
            
            # Load and display prompt content
            if prompt_name == "[Custom Prompt]":
                self.prompt_content.config(state="normal")
                self.prompt_content.delete(1.0, tk.END)
                self.prompt_content.config(state="normal")  # Keep editable
            else:
                prompt_content = self.prompts[prompt_name]["content"]
                
                # Update preview
                self.prompt_content.config(state="normal")
                self.prompt_content.delete(1.0, tk.END)
                self.prompt_content.insert(1.0, prompt_content)
                
                # Make content editable but not savable
                self.prompt_content.config(state="normal")
            
            # Update parent's current prompt
            if prompt_name == "[Custom Prompt]":
                self.parent.current_prompt = self.prompt_content.get("1.0", tk.END)
            else:
                self.parent.current_prompt = self.prompts[prompt_name]["content"]
            
            logger.info(f"Selected prompt: {prompt_name}")
        except Exception as e:
            logger.error(f"Error displaying prompt: {str(e)}")
    
    def edit_prompt_dialog(self):
        """Open a dialog to edit and save a prompt."""
        if not self.selected_prompt:
            messagebox.showinfo("No Prompt Selected", "Please select a prompt first.")
            return
            
        # Cannot edit the custom prompt this way
        if self.selected_prompt == "[Custom Prompt]":
            messagebox.showinfo("Custom Prompt", "The custom prompt can be edited directly in the main interface.")
            return
            
        # Get the prompt file path and content
        prompt_path = self.prompts[self.selected_prompt]["file"]
        prompt_content = self.prompts[self.selected_prompt]["content"]
        
        # Create dialog window
        dialog = tk.Toplevel(self.parent)
        dialog.title(f"Edit Prompt: {self.selected_prompt}")
        dialog.geometry("800x600")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Add text area
        text_area = scrolledtext.ScrolledText(dialog, wrap=tk.WORD)
        text_area.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Display the full content
        text_area.insert(1.0, prompt_content)
        
        # Make the dialog text area editable
        text_area.config(state="normal")
        
        # Add save and cancel buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        def save_prompt_changes():
            # Get the updated content
            updated_content = text_area.get("1.0", tk.END)
            
            try:
                # Save to file
                with open(prompt_path, "w", encoding="utf-8") as f:
                    f.write(updated_content)
                
                # Update internal data
                self.prompts[self.selected_prompt]["content"] = updated_content
                
                # Update preview in main window
                self.prompt_content.config(state="normal")
                self.prompt_content.delete("1.0", tk.END)
                self.prompt_content.insert("1.0", updated_content)
                self.prompt_content.config(state="disabled")
                
                # Update parent's current prompt
                self.parent.current_prompt = updated_content
                
                messagebox.showinfo("Success", f"Prompt saved successfully to {prompt_path}")
                logger.info(f"Saved changes to prompt: {self.selected_prompt}")
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save prompt: {str(e)}")
                logger.error(f"Error saving prompt: {str(e)}")
        
        save_button = ttk.Button(button_frame, text="Save Changes", command=save_prompt_changes)
        save_button.pack(side="left", padx=5)
        
        cancel_button = ttk.Button(button_frame, text="Cancel", command=dialog.destroy)
        cancel_button.pack(side="left", padx=5)
    
    def show_full_prompt_dialog(self):
        """Show the full prompt content in a dialog window."""
        if not self.selected_prompt:
            messagebox.showinfo("No Prompt Selected", "Please select a prompt first.")
            return
        
        if self.selected_prompt == "[Custom Prompt]":
            prompt_content = self.prompt_content.get("1.0", tk.END)
        else:
            prompt_content = self.prompts[self.selected_prompt]["content"]
        
        # Create dialog window
        dialog = tk.Toplevel(self.parent)
        dialog.title(f"Prompt: {self.selected_prompt}")
        dialog.geometry("800x600")
        dialog.transient(self.parent)
        dialog.grab_set()
        
        # Add text area
        text_area = scrolledtext.ScrolledText(dialog, wrap=tk.WORD)
        text_area.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Display the full content
        text_area.insert(1.0, prompt_content)
        
        # Make the dialog text area editable
        text_area.config(state="normal")
        
        # Add a note that changes aren't saved
        note_frame = ttk.Frame(dialog)
        note_frame.pack(fill="x", padx=10, pady=5)
        
        note_label = ttk.Label(note_frame, text="Note: Changes made here will not be saved to the file", foreground="red")
        note_label.pack(side="left")
        
        # Add close button
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        close_button = ttk.Button(button_frame, text="Close", command=dialog.destroy)
        close_button.pack()
    
    def load_learner_profiles(self):
        """Load learner profiles from the profiles directory."""
        try:
            self.profile_list.delete(0, tk.END)
            
            # Get all markdown and text files in the profiles directory
            md_files = glob.glob(os.path.join(self.profiles_dir, "*.md"))
            txt_files = glob.glob(os.path.join(self.profiles_dir, "*.txt"))
            
            # Combine and sort the file lists
            profile_files = sorted(md_files + txt_files)
            
            # Store profiles for system prompts
            self.parent.profiles = {}
            
            for file_path in profile_files:
                profile_name = os.path.splitext(os.path.basename(file_path))[0]
                self.profile_list.insert(tk.END, profile_name)
                
                # Also load content into parent's profiles dictionary
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.parent.profiles[profile_name] = {
                        "system": content,
                        "path": file_path
                    }
                except Exception as e:
                    logger.error(f"Error reading profile {file_path}: {str(e)}")
                
            logger.info(f"Loaded {len(profile_files)} learner profiles")
        except Exception as e:
            logger.error(f"Error loading learner profiles: {str(e)}")
    
    def on_profile_selected(self, event):
        """Handle selection of a learner profile."""
        try:
            selection = self.profile_list.curselection()
            if not selection:
                return
            
            index = selection[0]
            profile_name = self.profile_list.get(index)
            self.selected_profile = profile_name
            
            # Load and display profile content from parent's profiles dictionary
            if profile_name in self.parent.profiles:
                content = self.parent.profiles[profile_name]["system"]
                
                # Update preview - make editable but changes won't be saved
                self.profile_content.config(state="normal")
                self.profile_content.delete(1.0, tk.END)
                
                # Show full content in preview
                self.profile_content.insert(tk.END, content)
                self.profile_content.config(state="normal")  # Keep editable but won't save changes
                
                # Update parent dropdown
                self.parent.profiles_dropdown_var.set(profile_name)
                
                logger.info(f"Learner profile selected: {profile_name}")
            else:
                logger.error(f"Profile {profile_name} not found in loaded profiles")
        except Exception as e:
            logger.error(f"Error displaying learner profile: {str(e)}")
    
    def show_full_profile_dialog(self):
        """Show the full learner profile content in a dialog window."""
        if not self.selected_profile:
            messagebox.showinfo("No Profile Selected", "Please select a learner profile first.")
            return
        
        try:
            # Get profile content from parent's profiles dictionary
            if self.selected_profile in self.parent.profiles:
                content = self.parent.profiles[self.selected_profile]["system"]
            
                # Create dialog window
                dialog = tk.Toplevel(self.parent)
                dialog.title(f"Full Profile: {self.selected_profile}")
                dialog.geometry("800x600")
                
                # Add text area
                text_area = scrolledtext.ScrolledText(dialog, wrap=tk.WORD)
                text_area.pack(fill="both", expand=True, padx=10, pady=10)
                text_area.insert(tk.END, content)
                
                # Make editable but add note that changes won't be saved
                text_area.config(state="normal")
                
                # Add note that changes aren't saved
                note_frame = ttk.Frame(dialog)
                note_frame.pack(fill="x", padx=10, pady=5)
                
                note_label = ttk.Label(note_frame, text="Note: Changes made here will not be saved to the file", foreground="red")
                note_label.pack(side="left")
                
                # Add close button
                close_btn = ttk.Button(dialog, text="Close", command=dialog.destroy)
                close_btn.pack(pady=10)
            else:
                messagebox.showinfo("Profile Not Found", f"Could not find content for profile {self.selected_profile}")
        except Exception as e:
            logger.error(f"Error showing full profile: {str(e)}")
    
    def create_new_prompt(self):
        """Create a new prompt file in the prompt library."""
        # Get the prompt library directory
        prompt_dir = self.prompts_dir
        
        # Create a dialog window to get the prompt details
        dialog = tk.Toplevel(self.parent.parent)
        dialog.title("Create New Prompt")
        dialog.geometry("600x500")
        dialog.transient(self.parent.parent)  # Make it a modal dialog
        dialog.grab_set()  # Make it modal
        
        # Create the main frame with padding
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Category selection
        category_frame = ttk.Frame(main_frame)
        category_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(category_frame, text="Category:").pack(side="left")
        
        # Get existing categories from the prompt directory
        categories = ["content_editing", "robotics", "misc"]  # Default categories
        try:
            subdirs = [d for d in os.listdir(prompt_dir) if os.path.isdir(os.path.join(prompt_dir, d))]
            if subdirs:
                categories = subdirs
        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
        
        # Create a combobox for category selection
        category_var = tk.StringVar(value=categories[0] if categories else "")
        category_combo = ttk.Combobox(category_frame, textvariable=category_var, values=categories, width=30)
        category_combo.pack(side="left", padx=(5, 0))
        
        # Add a button to create a new category
        def create_new_category():
            new_cat = simpledialog.askstring("New Category", "Enter new category name:")
            if new_cat and new_cat.strip():
                new_cat = new_cat.strip().lower().replace(' ', '_')
                if new_cat not in categories:
                    categories.append(new_cat)
                    category_combo.config(values=categories)
                    category_var.set(new_cat)
        
        ttk.Button(category_frame, text="+", width=3, command=create_new_category).pack(side="left", padx=5)
        
        # Prompt name entry
        name_frame = ttk.Frame(main_frame)
        name_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(name_frame, text="Prompt Name:").pack(side="left")
        name_var = tk.StringVar()
        name_entry = ttk.Entry(name_frame, textvariable=name_var, width=40)
        name_entry.pack(side="left", padx=(5, 0))
        
        # Prompt content
        ttk.Label(main_frame, text="Prompt Content:").pack(anchor="w")
        
        content_text = scrolledtext.ScrolledText(main_frame, wrap="word", height=15)
        content_text.pack(fill="both", expand=True, pady=(5, 10))
        
        # Add template text
        template = """# System Prompt for Claude

This is a template for a new prompt. Replace this text with your prompt content.

## Instructions
- Define the role Claude should take
- Provide context for the task
- Include any specific formatting requirements
- Add examples if needed

## Example
You are an expert [role] helping the user with [task]. 
Follow these guidelines:
1. First, analyze the content provided
2. Then, generate [output format]
3. Finally, suggest improvements
"""
        content_text.insert("1.0", template)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x", pady=(0, 5))
        
        def save_prompt():
            category = category_var.get().strip()
            name = name_var.get().strip()
            content = content_text.get("1.0", tk.END)
            
            if not category or not name or not content.strip():
                messagebox.showerror("Error", "All fields are required")
                return
            
            # Format the name to be file-friendly
            name = name.lower().replace(' ', '_')
            
            # Create the category directory if it doesn't exist
            category_dir = os.path.join(prompt_dir, category)
            os.makedirs(category_dir, exist_ok=True)
            
            # Get the next available number prefix for the file
            try:
                existing_files = os.listdir(category_dir)
                number_prefixes = [int(f.split('_')[0]) for f in existing_files if f[0].isdigit() and '_' in f]
                next_number = max(number_prefixes) + 1 if number_prefixes else 1
            except Exception as e:
                logger.error(f"Error determining file number: {str(e)}")
                next_number = 1
            
            # Format with leading zeros for sorting
            file_name = f"{next_number:03d}_{name}.txt"
            file_path = os.path.join(category_dir, file_name)
            
            # Save the prompt
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                messagebox.showinfo("Success", f"Prompt saved to {file_path}")
                dialog.destroy()
                
                # Refresh the prompts
                self.refresh_resources()
                
                # Select the new prompt
                for i, prompt in enumerate(self.prompt_list.get(0, tk.END)):
                    if file_name in prompt or name in prompt:
                        self.prompt_list.selection_clear(0, tk.END)
                        self.prompt_list.selection_set(i)
                        self.prompt_list.see(i)
                        self.on_prompt_file_selected(None)  # Trigger selection event
                        break
                        
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save prompt: {str(e)}")
                logger.error(f"Error saving prompt: {str(e)}")
        
        # Add Save and Cancel buttons
        ttk.Button(buttons_frame, text="Save", command=save_prompt).pack(side="right", padx=5)
        ttk.Button(buttons_frame, text="Cancel", command=dialog.destroy).pack(side="right", padx=5)
        
        # Set focus to the name entry
        name_entry.focus_set()
    
    def call_claude_api(self, system, prompt, model="claude-opus-4-20250514", force_refresh=False):
        """
        Call the Claude API with the given system prompt, user prompt, and model.
        
        Args:
            system (str): The system prompt to use
            prompt (str): The user prompt to send to Claude
            model (str): The Claude model to use
            
        Returns:
            str: The response from Claude
        """
        # Try to read API key directly from .env file
        env_file_path = os.path.join(str(get_project_root()), '.env')
        api_key = None
        
        # First try to get from environment
        api_key = os.getenv("ANTHROPIC_API_KEY")
        
        # If not found, try to read directly from the .env file
        if not api_key and os.path.exists(env_file_path):
            try:
                with open(env_file_path, 'r') as env_file:
                    for line in env_file:
                        if line.strip().startswith('ANTHROPIC_API_KEY='):
                            api_key = line.strip().split('=', 1)[1].strip().strip('"\'')
                            break
                logger.info(f"Successfully loaded API key from {env_file_path}")
            except Exception as e:
                logger.error(f"Error reading .env file: {str(e)}")
        
        if not api_key:
            error_msg = "ANTHROPIC_API_KEY not found in environment variables or .env file. Please check your .env file."
            logger.error(error_msg)
            return error_msg
        
        # Log the API call (but not the full content for privacy)
        logger.info(f"Calling Claude API with model: {model}")
        
        # Anthropic API endpoint
        url = "https://api.anthropic.com/v1/messages"
        
        # API request headers
        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": api_key,
            "anthropic-version": "2023-06-01"
        }
        
        # API request data
        data = {
            "model": model,
            "system": system,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 4000
        }
        
        try:
            # Create directory for storing API calls in a Lesson_Preview subfolder
            storage_dir = r"C:\Users\User\Documents\showup-v4\showup-data\stored_api_calls\Lesson_Preview"
            os.makedirs(storage_dir, exist_ok=True)
            
            # Create a unique identifier for this request based on content hash
            # Use a shorter hash (first 16 chars) to keep paths under 120 characters
            import hashlib
            # Only hash the first 500 chars of the prompt to avoid overly long strings
            content_to_hash = system[:100] + prompt[:500] + model
            request_hash = hashlib.md5(content_to_hash.encode()).hexdigest()[:16]
            
            # Format timestamp as YYMMDD to keep the filename shorter
            timestamp = datetime.datetime.now().strftime('%y%m%d_%H%M%S')
            
            # Create a filename with timestamp prefix for better organization
            json_file_path = os.path.join(storage_dir, f"{timestamp}_{request_hash}.json")
            
            # Check cache only if force_refresh is False
            if not force_refresh:
                # Attempt to find a cached response by searching for files with the same hash suffix
                cached_file = None
                try:
                    for filename in os.listdir(storage_dir):
                        if filename.endswith(f"_{request_hash}.json"):
                            cached_file = os.path.join(storage_dir, filename)
                            break
                            
                    if cached_file and os.path.exists(cached_file):
                        with open(cached_file, 'r', encoding='utf-8') as f:
                            cached_data = json.load(f)
                            logger.info(f"Using cached API response from {cached_file}")
                            return cached_data.get('response', '')
                except Exception as e:
                    logger.warning(f"Error checking/reading cached response: {str(e)}")
            else:
                logger.info("Force refresh enabled - bypassing cache and making fresh API call")
            
            # Make the API request if no cache hit
            start_time = time.time()
            response = requests.post(url, headers=headers, json=data, timeout=120)
            end_time = time.time()
            
            # Log the response time
            logger.info(f"Claude API response time: {end_time - start_time:.2f} seconds")
            
            # Check for errors
            if response.status_code != 200:
                error_msg = f"Error calling Claude API: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return error_msg
            
            # Parse the response
            result = response.json()
            
            # Extract the content from the response
            if "content" in result and len(result["content"]) > 0:
                content_blocks = result["content"]
                text_blocks = [block["text"] for block in content_blocks if block["type"] == "text"]
                response_text = "".join(text_blocks)
                
                # Store the request and response
                storage_data = {
                    'timestamp': datetime.datetime.now().isoformat(),
                    'model': model,
                    'system': system,
                    'prompt': prompt,
                    'response': response_text,
                    'response_time': end_time - start_time
                }
                
                try:
                    with open(json_file_path, 'w', encoding='utf-8') as f:
                        json.dump(storage_data, f, indent=2, ensure_ascii=False)
                    logger.info(f"Stored API call in {json_file_path}")
                except Exception as e:
                    logger.error(f"Error storing API call: {str(e)}")
                    
                return response_text
            else:
                error_msg = "No content found in Claude API response"
                logger.error(error_msg)
                return error_msg
                
        except Exception as e:
            error_msg = f"Exception calling Claude API: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def refresh_resources(self):
        """Refresh prompt files and learner profiles from disk."""
        # Save current selections
        current_prompt = self.selected_prompt
        current_profile = self.selected_profile
        
        # Clear listboxes
        self.prompt_list.delete(0, tk.END)
        self.profile_list.delete(0, tk.END)
        
        # Reload resources
        self.load_prompts()
        self.load_learner_profiles()
        
        # Restore selections if still available
        if current_prompt:
            # Find index of current prompt in the refreshed list
            try:
                prompt_index = self.prompt_files.index(current_prompt)
                self.prompt_list.selection_set(prompt_index)
                self.prompt_list.see(prompt_index)
                self.on_prompt_file_selected(None)  # Refresh content display
            except ValueError:
                # Prompt no longer exists
                if self.prompt_list.size() > 0:
                    self.prompt_list.selection_set(0)
                    self.prompt_list.see(0)
                    self.on_prompt_file_selected(None)
        
        if current_profile:
            # Find index of current profile in the refreshed list
            try:
                profile_idx = list(self.learner_profiles.keys()).index(current_profile)
                self.profile_list.selection_set(profile_idx)
                self.profile_list.see(profile_idx)
                self.on_profile_selected(None)  # Refresh content display
            except ValueError:
                # Profile no longer exists
                if self.profile_list.size() > 0:
                    self.profile_list.selection_set(0)
                    self.profile_list.see(0)
                    self.on_profile_selected(None)
        
        # Log refresh action
        logger.info("Prompts and learner profiles refreshed successfully")
        if hasattr(self.parent, "update_status"):
            self.parent.update_status("Prompts and learner profiles refreshed successfully")
