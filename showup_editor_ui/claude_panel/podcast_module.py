#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Podcast Module for the Modular Output Library Editor

Provides podcast generation functionality with input, script, and audio tabs.
"""

import os
import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from typing import List
from datetime import datetime
from .path_utils import get_project_root

# Third-party imports
import requests
from dotenv import load_dotenv

# Ensure dotenv is available
try:
    from dotenv import load_dotenv
except ImportError:
    print("Warning: python-dotenv package not found. Environment variables must be set manually.")
    def load_dotenv():
        pass

# Load environment variables
load_dotenv()

# Get logger
logger = logging.getLogger("podcast_module")

# Check for OpenAI API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not found in environment variables")


class PodcastGenerator:
    """Main class for podcast generation functionality"""
    
    def __init__(self):
        self.selected_files = []
        self.target_learner = ""
        self.script_content = ""
        self.audio_file_path = ""
        
    def select_files(self) -> List[str]:
        """Allow user to select input content files"""
        return filedialog.askopenfilenames(
            title="Select Content Files",
            filetypes=[
                ("Text Files", "*.txt"),
                ("Markdown Files", "*.md"),
                ("All Files", "*.*")
            ]
        )
    
    def read_file_content(self, file_path: str) -> str:
        """Read content from a file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            return ""
    
    def generate_script(self, content: str, target_learner: str) -> str:
        """Generate podcast script using OpenAI API"""
        if not OPENAI_API_KEY:
            return "Error: OpenAI API key not found. Please check your .env file."
        
        try:
            # Prepare the prompt for script generation
            system_prompt = (
                "You are an expert podcast script writer. Create a natural-sounding discussion between two hosts "
                "about the provided content. Format your response as a conversation with clearly marked speakers. "
                f"The target audience is {target_learner}. Make the conversation engaging, informative, and natural. "
                "Use a conversational tone with occasional light humor. Include pauses, emphasis, and tone variations "
                "using Speech Markdown syntax (like [pause], [emphasis], etc.) to make the audio sound natural and "
                "not robotic. The two hosts should have distinct personalities - one more analytical and one more curious."
            )
            
            # Call OpenAI API
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4.1",  # Using the latest model
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 4000
                }
            )
            
            if response.status_code == 200:
                script = response.json()["choices"][0]["message"]["content"]
                logger.info("Script generated successfully")
                return script
            else:
                error_msg = f"API Error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return f"Error generating script: {error_msg}"
                
        except Exception as e:
            error_msg = f"Error generating script: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def convert_to_audio(self, script: str) -> str:
        """Convert script to audio using OpenAI API"""
        if not OPENAI_API_KEY:
            return "Error: OpenAI API key not found. Please check your .env file."
        
        try:
            # Create timestamp for unique filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(str(get_project_root()), "showup-editor-ui", "generated_podcasts")
            os.makedirs(output_dir, exist_ok=True)
            
            output_path = os.path.join(output_dir, f"podcast_{timestamp}.mp3")
            
            # Call OpenAI TTS API
            response = requests.post(
                "https://api.openai.com/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-mini-tts",  # Using the TTS model
                    "input": script,
                    "voice": "alloy",  # Can be customized
                    "response_format": "mp3"
                }
            )
            
            if response.status_code == 200:
                # Save the audio file
                with open(output_path, "wb") as file:
                    file.write(response.content)
                
                logger.info(f"Audio file saved to {output_path}")
                return output_path
            else:
                error_msg = f"API Error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return f"Error converting to audio: {error_msg}"
                
        except Exception as e:
            error_msg = f"Error converting to audio: {str(e)}"
            logger.error(error_msg)
            return error_msg


class PodcastPanel(ttk.Frame):
    """Podcast panel for integration with ClaudeAIPanel"""
    
    def __init__(self, parent, main_panel):
        ttk.Frame.__init__(self, parent)
        self.parent = parent
        self.main_panel = main_panel
        
        # Create the main generator instance
        self.generator = PodcastGenerator()
        
        # Create the notebook (tabs)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self.input_tab = ttk.Frame(self.notebook)
        self.script_tab = ttk.Frame(self.notebook)
        self.audio_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.input_tab, text="1. Input")
        self.notebook.add(self.script_tab, text="2. Script")
        self.notebook.add(self.audio_tab, text="3. Audio")
        
        # Setup tabs
        self._setup_input_tab()
        self._setup_script_tab()
        self._setup_audio_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _setup_input_tab(self):
        """Setup the input tab for file selection and target audience"""
        frame = ttk.Frame(self.input_tab, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = ttk.Label(frame, text="Input Content and Settings", style="Header.TLabel")
        header.pack(fill=tk.X, pady=(0, 10))
        
        # File selection
        file_frame = ttk.LabelFrame(frame, text="Content Files")
        file_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.files_list = tk.Listbox(file_frame, selectmode=tk.EXTENDED, height=10)
        self.files_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(file_frame, orient=tk.VERTICAL, command=self.files_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        self.files_list.config(yscrollcommand=scrollbar.set)
        
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        add_btn = ttk.Button(btn_frame, text="Add Files", command=self._add_files)
        add_btn.pack(side=tk.LEFT, padx=5)
        
        remove_btn = ttk.Button(btn_frame, text="Remove Selected", command=self._remove_files)
        remove_btn.pack(side=tk.LEFT, padx=5)
        
        # Use selected files button
        use_selected_btn = ttk.Button(btn_frame, text="Use Files From Library", command=self._use_library_files)
        use_selected_btn.pack(side=tk.LEFT, padx=5)
        
        # Target learner
        target_frame = ttk.LabelFrame(frame, text="Target Audience")
        target_frame.pack(fill=tk.X, pady=10)
        
        self.target_var = tk.StringVar()
        self.target_var.set("Beginners with no prior knowledge")  # Default value
        
        # Learner dropdown
        dropdown_frame = ttk.Frame(target_frame)
        dropdown_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(dropdown_frame, text="Target Learner:").pack(side=tk.LEFT, padx=5)
        
        # List of target learners
        target_options = [
            "Beginners with no prior knowledge",
            "Intermediate learners with some background",
            "Advanced professionals seeking in-depth knowledge",
            "Students in academic settings",
            "Business professionals looking for practical applications"
        ]
        
        # Create dropdown
        self.target_dropdown = ttk.Combobox(dropdown_frame, textvariable=self.target_var, values=target_options)
        self.target_dropdown.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Custom target option
        custom_frame = ttk.Frame(target_frame)
        custom_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(custom_frame, text="Custom Target:").pack(side=tk.LEFT, padx=5)
        
        self.custom_entry = ttk.Entry(custom_frame, width=40)
        self.custom_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Set custom button
        set_custom_btn = ttk.Button(custom_frame, text="Set Custom", 
                                 command=lambda: self.target_var.set(self.custom_entry.get()))
        set_custom_btn.pack(side=tk.LEFT, padx=5)
        
        # Next button
        next_frame = ttk.Frame(frame)
        next_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(next_frame, text="Generate Script »", command=self._generate_script).pack(side=tk.RIGHT)
    
    def _setup_script_tab(self):
        """Setup the script tab for editing the generated script"""
        frame = ttk.Frame(self.script_tab, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = ttk.Label(frame, text="Generated Podcast Script", style="Header.TLabel")
        header.pack(fill=tk.X, pady=(0, 10))
        
        # Script editor
        editor_frame = ttk.Frame(frame)
        editor_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.script_editor = scrolledtext.ScrolledText(editor_frame, wrap=tk.WORD, width=80, height=20)
        self.script_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="« Back to Input", command=lambda: self.notebook.select(0)).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Generate Audio »", command=self._convert_to_audio).pack(side=tk.RIGHT)
    
    def _setup_audio_tab(self):
        """Setup the audio tab for player and download links"""
        frame = ttk.Frame(self.audio_tab, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = ttk.Label(frame, text="Generated Podcast Audio", style="Header.TLabel")
        header.pack(fill=tk.X, pady=(0, 10))
        
        # Audio info
        self.audio_info_var = tk.StringVar()
        self.audio_info_var.set("No audio generated yet")
        
        info_label = ttk.Label(frame, textvariable=self.audio_info_var)
        info_label.pack(fill=tk.X, pady=5)
        
        # Audio player placeholder (would integrate with an actual player in a complete implementation)
        player_frame = ttk.LabelFrame(frame, text="Audio Player")
        player_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        ttk.Label(player_frame, text="Audio playback is not implemented in this version.\nPlease use your default audio player to play the generated file.").pack(pady=20)
        
        # Buttons for actions
        actions_frame = ttk.Frame(frame)
        actions_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(actions_frame, text="Open File Location", command=self._open_file_location).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Play in Default Player", command=self._play_in_default_player).pack(side=tk.LEFT, padx=5)
        
        # Navigation
        nav_frame = ttk.Frame(frame)
        nav_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(nav_frame, text="« Back to Script", command=lambda: self.notebook.select(1)).pack(side=tk.LEFT)
        ttk.Button(nav_frame, text="Start New Podcast", command=self._reset_all).pack(side=tk.RIGHT)
    
    def _add_files(self):
        """Add files to the list"""
        files = self.generator.select_files()
        if files:
            for file in files:
                self.files_list.insert(tk.END, file)
            self.status_var.set(f"Added {len(files)} file(s)")
    
    def _remove_files(self):
        """Remove selected files from the list"""
        selected = self.files_list.curselection()
        if not selected:
            return
        
        # Remove in reverse order to avoid index shifting
        for index in sorted(selected, reverse=True):
            self.files_list.delete(index)
        
        self.status_var.set(f"Removed {len(selected)} file(s)")
    
    def _use_library_files(self):
        """Use files selected in the library panel"""
        try:
            # Get the selected files from the main panel's file tree
            selected_items = self.main_panel.file_tree.selection()
            if not selected_items:
                messagebox.showinfo("No Files Selected", "Please select files in the library panel first.")
                return
                
            files = []
            for item_id in selected_items:
                # Get the item's values
                item_values = self.main_panel.file_tree.item(item_id, "values")
                if item_values and len(item_values) >= 2:
                    path = item_values[0]
                    item_type = item_values[1]
                    
                    # Only add files, not directories
                    if item_type.lower() == "file":
                        files.append(path)
            
            if not files:
                messagebox.showinfo("No Files Selected", "Please select files (not directories) in the library panel.")
                return
                
            # Clear existing files
            self.files_list.delete(0, tk.END)
            
            # Add selected files
            for file in files:
                self.files_list.insert(tk.END, file)
                
            self.status_var.set(f"Added {len(files)} file(s) from library")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Error getting selected files: {str(e)}")
    
    def _generate_script(self):
        """Generate the podcast script"""
        # Get files from list
        files = self.files_list.get(0, tk.END)
        if not files:
            messagebox.showerror("Error", "Please add at least one content file.")
            return
        
        # Get target learner
        target = self.target_var.get()
        if not target:
            messagebox.showerror("Error", "Please specify a target audience.")
            return
        
        # Store selected values
        self.generator.selected_files = files
        self.generator.target_learner = target
        
        # Show busy cursor
        self.parent.config(cursor="wait")
        self.status_var.set("Generating script... This may take a minute or two.")
        self.update_idletasks()
        
        # Run in a separate thread to keep UI responsive
        def generate_thread():
            # Combine content from all files
            combined_content = ""
            for file in files:
                file_content = self.generator.read_file_content(file)
                if file_content:
                    combined_content += f"\n\n--- Content from {os.path.basename(file)} ---\n\n{file_content}"
            
            # Generate script
            script = self.generator.generate_script(combined_content, target)
            
            # Update UI from the main thread
            self.after(0, lambda: self._update_script(script))
        
        threading.Thread(target=generate_thread, daemon=True).start()
    
    def _update_script(self, script):
        """Update the script editor with generated content"""
        # Reset cursor
        self.parent.config(cursor="")
        
        # Update script editor
        self.script_editor.delete(1.0, tk.END)
        self.script_editor.insert(tk.END, script)
        
        # Store script
        self.generator.script_content = script
        
        # Switch to script tab
        self.notebook.select(1)
        
        # Update status
        self.status_var.set("Script generated successfully. Review and make any desired edits.")
    
    def _convert_to_audio(self):
        """Convert the script to audio"""
        # Get current script from editor
        script = self.script_editor.get(1.0, tk.END).strip()
        if not script:
            messagebox.showerror("Error", "No script to convert.")
            return
        
        # Update stored script
        self.generator.script_content = script
        
        # Show busy cursor
        self.parent.config(cursor="wait")
        self.status_var.set("Converting script to audio... This may take a few minutes.")
        self.update_idletasks()
        
        # Run in a separate thread to keep UI responsive
        def convert_thread():
            # Convert to audio
            result = self.generator.convert_to_audio(script)
            
            # Update UI from the main thread
            self.after(0, lambda: self._update_audio(result))
        
        threading.Thread(target=convert_thread, daemon=True).start()
    
    def _update_audio(self, result):
        """Update the audio tab with generated audio file"""
        # Reset cursor
        self.parent.config(cursor="")
        
        # Check if result is an error message
        if result.startswith("Error"):
            messagebox.showerror("Error", result)
            self.status_var.set("Error converting to audio.")
            return
        
        # Store audio file path
        self.generator.audio_file_path = result
        
        # Update audio info
        self.audio_info_var.set(f"Generated audio file: {os.path.basename(result)}\nLocation: {result}")
        
        # Switch to audio tab
        self.notebook.select(2)
        
        # Update status
        self.status_var.set("Audio generated successfully.")
        
        # Show success message
        messagebox.showinfo("Success", f"Audio file generated successfully at:\n{result}")
    
    def _open_file_location(self):
        """Open the folder containing the generated audio file"""
        if not self.generator.audio_file_path or not os.path.exists(self.generator.audio_file_path):
            messagebox.showerror("Error", "No audio file available.")
            return
        
        # Open the folder containing the file
        folder_path = os.path.dirname(self.generator.audio_file_path)
        os.startfile(folder_path)  # For Windows
    
    def _play_in_default_player(self):
        """Play the audio file in the default system player"""
        if not self.generator.audio_file_path or not os.path.exists(self.generator.audio_file_path):
            messagebox.showerror("Error", "No audio file available.")
            return
        
        # Open the audio file with the default player
        os.startfile(self.generator.audio_file_path)  # For Windows
    
    def _reset_all(self):
        """Reset the application for a new podcast"""
        # Reset file list
        self.files_list.delete(0, tk.END)
        
        # Reset script editor
        self.script_editor.delete(1.0, tk.END)
        
        # Reset audio info
        self.audio_info_var.set("No audio generated yet")
        
        # Reset generator
        self.generator = PodcastGenerator()
        
        # Switch to input tab
        self.notebook.select(0)
        
        # Update status
        self.status_var.set("Ready for new podcast creation")


def setup_podcast_tab(podcast_tab: ttk.Frame, main_panel) -> ttk.Frame:
    """Setup the podcast tab for the ClaudeAIPanel
    
    Args:
        podcast_tab: The frame to use for the podcast tab
        main_panel: The main ClaudeAIPanel instance
        
    Returns:
        The created podcast tab frame
    """
    # Create the podcast panel
    podcast_panel = PodcastPanel(podcast_tab, main_panel)
    podcast_panel.pack(fill=tk.BOTH, expand=True)
    
    return podcast_tab
