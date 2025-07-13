#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GUI components for the podcast generator application.

Contains classes for creating the GUI tabs and handling user interactions.
"""

import os
import logging
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import List
import subprocess
import re

logger = logging.getLogger('podcast_generator')


class BaseTab:
    """Base class for notebook tabs in the podcast generator GUI."""
    
    def __init__(self, parent: ttk.Frame, main_gui):
        """Initialize a base tab.
        
        Args:
            parent: The parent frame where this tab resides
            main_gui: Reference to the main GUI controller
        """
        self.parent = parent
        self.main_gui = main_gui
        self.frame = ttk.Frame(parent, padding="10")
        self.frame.pack(fill=tk.BOTH, expand=True)


class InputTab(BaseTab):
    """Input tab for selecting content files and target audience."""
    
    def __init__(self, parent: ttk.Frame, main_gui):
        super().__init__(parent, main_gui)
        
        # Header
        header = ttk.Label(self.frame, text="Input Content and Settings", style="Header.TLabel")
        header.pack(fill=tk.X, pady=(0, 10))
        
        # File selection
        file_frame = ttk.LabelFrame(self.frame, text="Content Files")
        file_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.files_list = tk.Listbox(file_frame, selectmode=tk.EXTENDED, height=10)
        self.files_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(file_frame, orient=tk.VERTICAL, command=self.files_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        self.files_list.config(yscrollcommand=scrollbar.set)
        
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        add_btn = ttk.Button(btn_frame, text="Add Files", command=self.add_files)
        add_btn.pack(side=tk.LEFT, padx=5)
        
        remove_btn = ttk.Button(btn_frame, text="Remove Selected", command=self.remove_files)
        remove_btn.pack(side=tk.LEFT, padx=5)
        
        # Target learner
        target_frame = ttk.LabelFrame(self.frame, text="Target Audience")
        target_frame.pack(fill=tk.X, pady=10)
        
        self.target_var = tk.StringVar()
        
        # Get available profiles
        profile_names = self.main_gui.generator.get_profile_names()
        
        # Set default to Robotics_Podcast if available
        robotics_profile_name = None
        for profile_name in profile_names:
            if "Robotics" in profile_name or profile_name == "Robotics_Podcast":
                robotics_profile_name = profile_name
                break
        
        if robotics_profile_name:
            self.target_var.set(robotics_profile_name)  # Default to Robotics profile
        elif profile_names:
            self.target_var.set(profile_names[0])  # Default to first profile
        else:
            self.target_var.set("Beginners with no prior knowledge")  # Fallback default
        
        # Create dropdown menu with learner profiles
        profile_label = ttk.Label(target_frame, text="Select target learner profile:")
        profile_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        profile_dropdown = ttk.Combobox(target_frame, textvariable=self.target_var, values=profile_names, width=40)
        profile_dropdown.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Custom entry option
        custom_frame = ttk.Frame(target_frame)
        custom_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        custom_label = ttk.Label(custom_frame, text="Or enter custom target audience:")
        custom_label.pack(side=tk.LEFT, padx=5)
        
        self.custom_entry = ttk.Entry(custom_frame, width=40)
        self.custom_entry.pack(side=tk.LEFT, padx=5)
        
        # Word limit setting
        limit_frame = ttk.Frame(target_frame)
        limit_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        limit_label = ttk.Label(limit_frame, text="Word limit for script:")
        limit_label.pack(side=tk.LEFT, padx=5)
        
        self.word_limit_var = tk.StringVar()
        self.word_limit_var.set(str(self.main_gui.generator.word_limit))  # Default from generator
        
        self.word_limit_entry = ttk.Entry(limit_frame, width=10, textvariable=self.word_limit_var)
        self.word_limit_entry.pack(side=tk.LEFT, padx=5)
        
        # Generate button
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        generate_btn = ttk.Button(btn_frame, text="Generate Podcast Script", command=self.generate_script)
        generate_btn.pack(side=tk.RIGHT, padx=5)
    
    def add_files(self):
        """Add files to the list."""
        files = self.main_gui.generator.select_files()
        if files:
            for file in files:
                self.files_list.insert(tk.END, file)
            self.main_gui.status_var.set(f"Added {len(files)} file(s)")
    
    def remove_files(self):
        """Remove selected files from the list."""
        selected = self.files_list.curselection()
        if not selected:
            return
        
        # Remove in reverse order to avoid index shifting
        for index in sorted(selected, reverse=True):
            self.files_list.delete(index)
        
        self.main_gui.status_var.set(f"Removed {len(selected)} file(s)")
    
    def generate_script(self):
        """Generate the podcast script."""
        self.main_gui._generate_script()
        
    def get_selected_files(self) -> List[str]:
        """Get the list of selected files."""
        return [self.files_list.get(i) for i in range(self.files_list.size())]
    
    def get_target_learner(self) -> str:
        """Get the selected target learner profile or custom entry."""
        custom_entry = self.custom_entry.get().strip()
        if custom_entry:
            return custom_entry
        return self.target_var.get()
    
    def get_word_limit(self) -> int:
        """Get the word limit for script generation."""
        try:
            return int(self.word_limit_var.get())
        except ValueError:
            # If invalid input, return default
            return self.main_gui.generator.word_limit


class ScriptTab(BaseTab):
    """Script tab for editing the generated script."""
    
    def __init__(self, parent: ttk.Frame, main_gui):
        super().__init__(parent, main_gui)
        
        # Header and instructions
        header_frame = ttk.Frame(self.frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        header = ttk.Label(header_frame, text="Generated Podcast Script", style="Header.TLabel")
        header.pack(side=tk.LEFT, pady=(0, 5))
        
        # Instructions for editing
        instructions_frame = ttk.Frame(self.frame)
        instructions_frame.pack(fill=tk.X, pady=(0, 10))
        
        instructions = ttk.Label(instructions_frame, 
                               text="You can edit this script before converting it to audio. Maintain the 'Specialist 1:' and 'Specialist 2:' format.",
                               wraplength=600)
        instructions.pack(side=tk.LEFT, pady=(0, 5), padx=5)
        
        # Script editor with line numbers and syntax highlighting
        editor_frame = ttk.LabelFrame(self.frame, text="Script Editor")
        editor_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.script_editor = scrolledtext.ScrolledText(editor_frame, wrap=tk.WORD, width=80, height=20,
                                                     font=("Consolas", 10))
        self.script_editor.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add some basic text formatting options
        format_frame = ttk.Frame(self.frame)
        format_frame.pack(fill=tk.X, pady=(5, 10))
        
        # Character counter
        self.char_count_var = tk.StringVar()
        self.char_count_var.set("Characters: 0 | Words: 0")
        char_count_label = ttk.Label(format_frame, textvariable=self.char_count_var)
        char_count_label.pack(side=tk.LEFT, padx=5)
        
        # Format tools
        ttk.Button(format_frame, text="Format Specialist 1", 
                  command=lambda: self._insert_specialist_tag(1)).pack(side=tk.RIGHT, padx=5)
        ttk.Button(format_frame, text="Format Specialist 2", 
                  command=lambda: self._insert_specialist_tag(2)).pack(side=tk.RIGHT, padx=5)
        ttk.Button(format_frame, text="Add [emphasis]", 
                  command=self._insert_emphasis).pack(side=tk.RIGHT, padx=5)
        ttk.Button(format_frame, text="Add [pause]", 
                  command=self._insert_pause).pack(side=tk.RIGHT, padx=5)
        
        # Action buttons 
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(btn_frame, text="« Back to Input", 
                   command=lambda: self.main_gui.notebook.select(0)).pack(side=tk.LEFT)
                   
        # Save/load buttons
        ttk.Button(btn_frame, text="Save Script", 
                  command=self._save_script).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="Load Script", 
                  command=self._load_script).pack(side=tk.LEFT, padx=5)
                  
        # Validate before generating audio
        ttk.Button(btn_frame, text="Validate Script", 
                  command=self._validate_script).pack(side=tk.RIGHT, padx=10)
        ttk.Button(btn_frame, text="Generate Audio »", 
                   command=self.convert_to_audio).pack(side=tk.RIGHT)
                   
        # Bind events
        self.script_editor.bind("<KeyRelease>", self._update_counts)
    
    def update_script(self, script: str):
        """Update the script editor with generated content."""
        self.script_editor.delete(1.0, tk.END)
        self.script_editor.insert(tk.END, script)
        self._update_counts()
    
    def get_script(self) -> str:
        """Get the current script content."""
        return self.script_editor.get(1.0, tk.END)
    
    def convert_to_audio(self):
        """Convert the script to audio."""
        self.main_gui._convert_to_audio()
        
    def _update_counts(self, event=None):
        """Update character and word counts."""
        text = self.script_editor.get(1.0, tk.END)
        char_count = len(text) - 1  # Subtract 1 for the trailing newline
        word_count = len(text.split())
        self.char_count_var.set(f"Characters: {char_count} | Words: {word_count}")
        
    def _insert_specialist_tag(self, specialist_num: int):
        """Insert specialist tag at cursor position."""
        try:
            # Get current position
            current_pos = self.script_editor.index(tk.INSERT)
            line, col = map(int, current_pos.split('.'))
            
            # If not at the beginning of a line, insert a newline first
            if col > 0:
                self.script_editor.insert(tk.INSERT, "\n\n")
                
            # Insert the specialist tag
            self.script_editor.insert(tk.INSERT, f"Specialist {specialist_num}: ")
            self._update_counts()
        except Exception as e:
            logger.error(f"Error inserting specialist tag: {str(e)}")
            
    def _insert_emphasis(self):
        """Insert emphasis tags around selected text or at cursor."""
        try:
            # Check if there's a selection
            try:
                selected_text = self.script_editor.get(tk.SEL_FIRST, tk.SEL_LAST)
                self.script_editor.delete(tk.SEL_FIRST, tk.SEL_LAST)
                self.script_editor.insert(tk.INSERT, f"[emphasis]{selected_text}[/emphasis]")
            except tk.TclError:  # No selection
                self.script_editor.insert(tk.INSERT, "[emphasis][/emphasis]")
                # Move cursor back to between tags
                current_pos = self.script_editor.index(tk.INSERT)
                self.script_editor.mark_set(tk.INSERT, f"{current_pos}-11c")
            self._update_counts()
        except Exception as e:
            logger.error(f"Error inserting emphasis: {str(e)}")
            
    def _insert_pause(self):
        """Insert pause tag at cursor position."""
        try:
            self.script_editor.insert(tk.INSERT, "[pause]")
            self._update_counts()
        except Exception as e:
            logger.error(f"Error inserting pause: {str(e)}")
            
    def _save_script(self):
        """Save script to file."""
        try:
            from tkinter import filedialog
            script = self.get_script()
            if not script.strip():
                messagebox.showwarning("Empty Script", "There is no script to save.")
                return
                
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Save Script"
            )
            
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(script)
                messagebox.showinfo("Success", f"Script saved to {file_path}")
        except Exception as e:
            logger.error(f"Error saving script: {str(e)}")
            messagebox.showerror("Error", f"Could not save script: {str(e)}")
            
    def _load_script(self):
        """Load script from file."""
        try:
            from tkinter import filedialog
            file_path = filedialog.askopenfilename(
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Load Script"
            )
            
            if file_path:
                with open(file_path, 'r', encoding='utf-8') as f:
                    script = f.read()
                self.update_script(script)
                messagebox.showinfo("Success", f"Script loaded from {file_path}")
        except Exception as e:
            logger.error(f"Error loading script: {str(e)}")
            messagebox.showerror("Error", f"Could not load script: {str(e)}")
            
    def _validate_script(self):
        """Validate the script format."""
        try:
            script = self.get_script()
            
            # Basic validation
            if not script.strip():
                messagebox.showwarning("Empty Script", "The script is empty.")
                return
                
            # Check for specialist tags
            specialist1_count = script.lower().count("specialist 1:")
            specialist2_count = script.lower().count("specialist 2:")
            
            if specialist1_count == 0 and specialist2_count == 0:
                messagebox.showwarning("Format Warning", 
                                     "No 'Specialist 1:' or 'Specialist 2:' tags found. The script should use these tags for proper audio generation.")
                return
                
            # Check for balance between specialists
            if specialist1_count == 0:
                messagebox.showwarning("Format Warning", "No 'Specialist 1:' tags found.")
            if specialist2_count == 0:
                messagebox.showwarning("Format Warning", "No 'Specialist 2:' tags found.")
                
            # Word count check  
            words = re.findall(r'\b\w+\b', script)
            word_count = len(words)
            
            if word_count < 450 or word_count > 550:
                messagebox.showwarning("Word Count", 
                                     f"Script has {word_count} words. Recommended range is 450-550 words.")
            else:
                messagebox.showinfo("Validation Passed", 
                                  f"Script format looks good! Word count: {word_count}\n" +
                                  f"Specialist 1 appears {specialist1_count} times.\n" +
                                  f"Specialist 2 appears {specialist2_count} times.")
                
        except Exception as e:
            logger.error(f"Error validating script: {str(e)}")
            messagebox.showerror("Error", f"Could not validate script: {str(e)}")


class AudioTab(BaseTab):
    """Audio tab for player and download links."""
    
    def __init__(self, parent: ttk.Frame, main_gui):
        super().__init__(parent, main_gui)
        
        # Header
        header = ttk.Label(self.frame, text="Generated Podcast Audio", style="Header.TLabel")
        header.pack(fill=tk.X, pady=(0, 10))
        
        # Audio info
        self.audio_info_var = tk.StringVar()
        self.audio_info_var.set("No audio generated yet")
        
        info_label = ttk.Label(self.frame, textvariable=self.audio_info_var)
        info_label.pack(fill=tk.X, pady=5)
        
        # Audio player placeholder (would integrate with an actual player in a complete implementation)
        player_frame = ttk.LabelFrame(self.frame, text="Audio Player")
        player_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        ttk.Label(player_frame, 
                 text="Audio playback is not implemented in this version.\n"
                      "Please use your default audio player to play the generated file."
                 ).pack(pady=20)
        
        # Buttons for actions
        actions_frame = ttk.Frame(self.frame)
        actions_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(actions_frame, text="Open File Location", 
                   command=self.open_file_location).pack(side=tk.LEFT, padx=5)
        ttk.Button(actions_frame, text="Play in Default Player", 
                   command=self.play_in_default_player).pack(side=tk.LEFT, padx=5)
        
        # Navigation
        nav_frame = ttk.Frame(self.frame)
        nav_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(nav_frame, text="« Back to Script", 
                   command=lambda: self.main_gui.notebook.select(1)).pack(side=tk.LEFT)
        ttk.Button(nav_frame, text="Start New Podcast", 
                   command=self.main_gui._reset_all).pack(side=tk.RIGHT)
    
    def update_audio(self, result: str):
        """Update the audio tab with generated audio file."""
        if result.startswith("Error"):
            self.audio_info_var.set(f"Error generating audio: {result}")
            messagebox.showerror("Audio Generation Error", result)
        else:
            self.audio_info_var.set(f"Audio file generated: {os.path.basename(result)}")
            # Save the path to the audio file
            self.main_gui.generator.audio_file_path = result
    
    def open_file_location(self):
        """Open the folder containing the generated audio file."""
        if not self.main_gui.generator.audio_file_path:
            messagebox.showinfo("No Audio", "No audio file has been generated yet.")
            return
            
        file_path = self.main_gui.generator.audio_file_path
        directory = os.path.dirname(file_path)
        
        try:
            # Open the directory in file explorer
            if os.name == 'nt':  # Windows
                os.startfile(directory)
            elif os.name == 'posix':  # macOS and Linux
                subprocess.call(['open', directory] if os.uname().sysname == 'Darwin' else ['xdg-open', directory])
            
            self.main_gui.status_var.set(f"Opened folder: {directory}")
        except Exception as e:
            logger.error(f"Error opening file location: {str(e)}")
            messagebox.showerror("Error", f"Could not open file location: {str(e)}")
    
    def play_in_default_player(self):
        """Play the audio file in the default system player."""
        if not self.main_gui.generator.audio_file_path:
            messagebox.showinfo("No Audio", "No audio file has been generated yet.")
            return
            
        file_path = self.main_gui.generator.audio_file_path
        
        try:
            # Open with default player
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # macOS and Linux
                subprocess.call(['open', file_path] if os.uname().sysname == 'Darwin' else ['xdg-open', file_path])
            
            self.main_gui.status_var.set(f"Playing audio: {os.path.basename(file_path)}")
        except Exception as e:
            logger.error(f"Error playing audio: {str(e)}")
            messagebox.showerror("Error", f"Could not play audio: {str(e)}")
