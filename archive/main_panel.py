"""Main Panel Class - Core initialization and tab setup"""

import os
import sys
import json
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext, simpledialog
import logging
import shutil
import subprocess
from .path_utils import get_project_root

# Import config manager
from .config_manager import config_manager

# Internal modules
from .prompt_manager import PromptManager
from .batch_processor import BatchProcessor
from .full_doc_regenerator import FullDocRegenerator
from .ai_detector import AIDetector
from .content_generator import ContentGenerator
from .markdown_splitter import MarkdownSplitterPanel
from .markdown_converter import MarkdownConverterPanel, FileRenamerPanel
from .markdown_editor import MarkdownEditor
from .batch_file_splitter import BatchFileSplitterPanel
from .html_viewer import HTMLViewerPanel
from .markdown_tools import MarkdownTools
from .tab_manager import TabManager
from .document_creator import DocumentCreator
from .audio_script_splitter import AudioScriptSplitter
from .podcast_launcher import setup_podcast_tab  # Import the podcast launcher module
from .lesson_preview_panel import LessonPreviewPanel  # Import the lesson preview panel
from .enrich_lesson import EnrichLessonPanel  # Import the enrich lesson panel

# Import CLAUDE_MODELS configuration from the module
from claude_api import CLAUDE_MODELS

# Get logger
logger = logging.getLogger("output_library_editor")

class ClaudeAIPanel(ttk.Frame):
    """Panel for Claude AI integration with prompt configuration and processing."""
    
    def __init__(self, parent, main_app, *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        self.parent = parent
        self.main_app = main_app
        self.batch_files = []  # List to store batch file paths
        self.batch_results = {}  # Dictionary to store batch results
        self.processing_batch = False  # Flag to indicate batch processing
        
        # Initialize model variables with centralized model configuration
        self.context_model = CLAUDE_MODELS["CONTEXT_GEN"]  # Use centralized model configuration
        self.edit_model = CLAUDE_MODELS["CONTENT_EDIT"]  # Use centralized model configuration
        
        # Initialize profile variables
        self.profiles = {}
        self.profiles_dropdown_var = tk.StringVar()
        
        # Initialize ttk style object
        self.style = ttk.Style()
        
        logger.info("ClaudeAIPanel initialized")
        
        # Load system profiles
        self._load_profiles()
        
        # Create the main split pane layout
        self._setup_split_pane_structure()
        
        # Set up the library panel
        self._setup_library_panel()
        
        # Initialize all components
        self.prompt_manager = PromptManager(self)
        self.batch_processor = BatchProcessor(self.batch_tab, self)
        self.full_doc_regenerator = FullDocRegenerator(self.full_regen_tab, self)
        self.ai_detector = AIDetector(self)
        self.content_generator = ContentGenerator(self)
        self.markdown_splitter = MarkdownSplitterPanel(self)
        self.markdown_converter = MarkdownConverterPanel(self)
        self.markdown_editor = MarkdownEditor(self)
        self.batch_file_splitter = BatchFileSplitterPanel(self)
        self.file_renamer = FileRenamerPanel(self)
        self.html_viewer = HTMLViewerPanel(self)
        self.markdown_tools = MarkdownTools(self.markdown_tools_tab, self)
        self.document_creator = DocumentCreator(self.doc_creator_tab, self)
        self.audio_script_splitter = AudioScriptSplitter(self.audio_script_splitter_tab, self)
        self.lesson_preview = LessonPreviewPanel(self)
        self.enrich_lesson = EnrichLessonPanel(self.enrich_lesson_tab, self, self.markdown_editor)
        
        # Initialize the tab manager (after all tabs are created)
        self.tab_manager = TabManager(self, self.notebook)
        
        # Create the tab manager UI
        self.tab_manager_ui = self.tab_manager.create_tab_manager_frame(self.tab_manager_frame)
        self.tab_manager_ui.pack(fill="x", expand=True)
        
        # Initialize tab visibility management after the TabManager is created
        # (This will happen later in the initialization sequence)
        
        # Setup all tabs
        self.prompt_manager.setup_prompt_tab()
        self.batch_processor.setup_batch_tab()
        self.full_doc_regenerator.setup_full_regen_tab()
        self.ai_detector.setup_ai_detect_tab()
        self.markdown_editor.setup_editor_tab()
        self.content_generator.setup_generate_content_tab()
        self.markdown_splitter.setup_splitter_tab()
        self.markdown_converter.setup_converter_tab()
        self.batch_file_splitter.setup_batch_splitter_tab()  # Set up the batch splitter tab
        self.file_renamer.setup_renamer_tab()  # Set up the new file renamer tab
        self.html_viewer.setup_html_viewer_tab()  # Set up the HTML viewer tab
        self.markdown_tools.setup_markdown_tools_tab()  # Set up the markdown tools tab
        self.document_creator.setup_doc_creator_tab()  # Set up the document creator tab
        self.audio_script_splitter.setup_audio_script_splitter_tab()  # Set up the audio script splitter tab
        setup_podcast_tab(self.podcast_tab, self)  # Set up the podcast launcher tab
        self.lesson_preview.setup_lesson_preview_tab()  # Set up the lesson preview tab
        
        # Add UI elements for analyzing selected text
        self._setup_selected_text_analysis()
        
        # Set up right-click context menu for the file tree
        self._setup_file_tree_context_menu()
        
        # Register all tabs with the tab manager after they are all set up
        self._register_tabs_with_manager()

        logger.info("All tabs initialized")

        # Handle window close event to ensure resources are cleaned up
        self.parent.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def _setup_split_pane_structure(self):
        """Set up the main split pane structure with library on left and notebook on right."""
        # Create the main horizontal panes
        self.main_panes = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.main_panes.pack(fill="both", expand=True)
        
        # Create the left panel for file browser
        self.left_panel = ttk.Frame(self.main_panes, width=250)
        self.main_panes.add(self.left_panel, weight=1)
        
        # Create tab manager frame at the top of the left panel
        self.tab_manager_frame = ttk.Frame(self.left_panel)
        self.tab_manager_frame.pack(fill="x", padx=5, pady=5)
        
        # Create the library frame below the tab manager
        self.library_frame = ttk.Frame(self.left_panel)
        self.library_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create the right panel with notebook tabs
        self.right_panel = ttk.Frame(self.main_panes)
        self.main_panes.add(self.right_panel, weight=4)
        
        # Create the notebook for tabs
        self.notebook = ttk.Notebook(self.right_panel)
        self.notebook.pack(fill="both", expand=True)
        
        # Create tabs
        self.prompt_tab = ttk.Frame(self.notebook)
        self.markdown_editor_tab = ttk.Frame(self.notebook)
        self.batch_tab = ttk.Frame(self.notebook)
        self.full_regen_tab = ttk.Frame(self.notebook)
        self.ai_detect_tab = ttk.Frame(self.notebook)
        self.generate_content_tab = ttk.Frame(self.notebook)
        self.md_splitter_tab = ttk.Frame(self.notebook)
        self.md_to_html_tab = ttk.Frame(self.notebook)
        self.batch_splitter_tab = ttk.Frame(self.notebook)  # New batch splitter tab
        self.file_renamer_tab = ttk.Frame(self.notebook)  # New file renamer tab
        self.html_viewer_tab = ttk.Frame(self.notebook)  # New HTML viewer tab
        self.markdown_tools_tab = ttk.Frame(self.notebook)  # New markdown tools tab
        self.podcast_tab = ttk.Frame(self.notebook)  # New podcast generator tab
        self.doc_creator_tab = ttk.Frame(self.notebook)  # New document creator tab
        self.audio_script_splitter_tab = ttk.Frame(self.notebook)  # New audio script splitter tab
        self.lesson_preview_tab = ttk.Frame(self.notebook)  # New lesson preview tab
        self.enrich_lesson_tab = ttk.Frame(self.notebook)  # New enrich lesson tab
        
        # Add tabs to notebook
        self.notebook.add(self.prompt_tab, text="Prompt Config")
        self.notebook.add(self.markdown_editor_tab, text="Markdown Editor")
        self.notebook.add(self.batch_tab, text="Batch Processing")
        self.notebook.add(self.full_regen_tab, text="Full Doc Regeneration")
        self.notebook.add(self.ai_detect_tab, text="AI Detection")
        self.notebook.add(self.generate_content_tab, text="Generate Content")
        self.notebook.add(self.md_splitter_tab, text="MD Splitter")
        self.notebook.add(self.md_to_html_tab, text="MD to HTML")
        self.notebook.add(self.batch_splitter_tab, text="Batch Splitter")  # Add new batch splitter tab
        self.notebook.add(self.file_renamer_tab, text="File Renamer")  # Add new file renamer tab
        self.notebook.add(self.html_viewer_tab, text="HTML Viewer")  # Add new HTML viewer tab
        self.notebook.add(self.markdown_tools_tab, text="Markdown Tools")  # Add new markdown tools tab
        self.notebook.add(self.podcast_tab, text="Podcast Generator")  # Add new podcast generator tab
        self.notebook.add(self.doc_creator_tab, text="Document Creator")  # Add new document creator tab
        self.notebook.add(self.audio_script_splitter_tab, text="Audio Script Splitter")  # Add new audio script splitter tab
        self.notebook.add(self.lesson_preview_tab, text="Lesson Preview")  # Add new lesson preview tab
        self.notebook.add(self.enrich_lesson_tab, text="Enrich Lesson")  # Add new enrich lesson tab
        
        # Log tab indices for debugging
        logger.info("ClaudeAIPanel tabs created with following indexes:")
        logger.info(f"Prompt Config tab index: {self.notebook.index(self.prompt_tab)}")
        logger.info(f"Markdown Editor tab index: {self.notebook.index(self.markdown_editor_tab)}")
        logger.info(f"Batch Processing tab index: {self.notebook.index(self.batch_tab)}")
        logger.info(f"Full Doc Regeneration tab index: {self.notebook.index(self.full_regen_tab)}")
        logger.info(f"AI Detection tab index: {self.notebook.index(self.ai_detect_tab)}")
        logger.info(f"Generate Content tab index: {self.notebook.index(self.generate_content_tab)}")
        logger.info(f"MD Splitter tab index: {self.notebook.index(self.md_splitter_tab)}")
        logger.info(f"MD to HTML tab index: {self.notebook.index(self.md_to_html_tab)}")
        logger.info(f"Batch Splitter tab index: {self.notebook.index(self.batch_splitter_tab)}")
        logger.info(f"File Renamer tab index: {self.notebook.index(self.file_renamer_tab)}")
        logger.info(f"HTML Viewer tab index: {self.notebook.index(self.html_viewer_tab)}")
        logger.info(f"Markdown Tools tab index: {self.notebook.index(self.markdown_tools_tab)}")
        logger.info(f"Podcast Generator tab index: {self.notebook.index(self.podcast_tab)}")
        logger.info(f"Document Creator tab index: {self.notebook.index(self.doc_creator_tab)}")
        logger.info(f"Audio Script Splitter tab index: {self.notebook.index(self.audio_script_splitter_tab)}")
        logger.info(f"Lesson Preview tab index: {self.notebook.index(self.lesson_preview_tab)}")
        
    def _setup_library_panel(self):
        """Set up the library panel on the left side with file browser."""
        # Create label frame for library
        self.library_label_frame = ttk.LabelFrame(self.library_frame, text="Library Files")
        self.library_label_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add library path configuration frame
        self.library_path_frame = ttk.Frame(self.library_label_frame)
        self.library_path_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Label(self.library_path_frame, text="Library Root:").pack(side="left", padx=2, pady=2)
        
        # Get the library path from config
        self.library_path_var = tk.StringVar(value=config_manager.get_library_path())
        self.library_path_entry = ttk.Entry(self.library_path_frame, textvariable=self.library_path_var)
        self.library_path_entry.pack(side="left", fill="x", expand=True, padx=2, pady=2)
        
        # Add browse button
        self.browse_button = ttk.Button(self.library_path_frame, text="Browse", width=8,
                                      command=self._browse_library_path)
        self.browse_button.pack(side="left", padx=2, pady=2)
        
        # Add save button
        self.save_path_button = ttk.Button(self.library_path_frame, text="Save", width=8,
                                        command=self._save_library_path)
        self.save_path_button.pack(side="left", padx=2, pady=2)

        # Add prompt library path configuration frame
        self.prompt_path_frame = ttk.Frame(self.library_label_frame)
        self.prompt_path_frame.pack(fill="x", padx=5, pady=2)
        
        ttk.Label(self.prompt_path_frame, text="Prompt Library Root:").pack(side="left", padx=2, pady=2)
        
        # Get the prompt library path from config
        self.prompt_path_var = tk.StringVar(value=config_manager.get_setting("library_prompts_path"))
        self.prompt_path_entry = ttk.Entry(self.prompt_path_frame, textvariable=self.prompt_path_var)
        self.prompt_path_entry.pack(side="left", fill="x", expand=True, padx=2, pady=2)
        
        # Add browse button for prompt path
        self.prompt_browse_button = ttk.Button(self.prompt_path_frame, text="Browse", width=8,
                                      command=self._browse_prompt_path)
        self.prompt_browse_button.pack(side="left", padx=2, pady=2)
        
        # Add save button for prompt path
        self.save_prompt_path_button = ttk.Button(self.prompt_path_frame, text="Save", width=8,
                                        command=self._save_prompt_path)
        self.save_prompt_path_button.pack(side="left", padx=2, pady=2)
        
        # Add refresh button frame
        refresh_frame = ttk.Frame(self.library_label_frame)
        refresh_frame.pack(fill="x", padx=5, pady=2)
        
        self.refresh_button = ttk.Button(refresh_frame, text="⟳", width=3, 
                                      command=self._refresh_library)
        self.refresh_button.pack(side="right", padx=5, pady=2)
        
        # Add search entry
        self.search_frame = ttk.Frame(self.library_label_frame)
        self.search_frame.pack(fill="x", padx=5, pady=2)
        
        self.search_label = ttk.Label(self.search_frame, text="Search:")
        self.search_label.pack(side="left", padx=2)
        
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(self.search_frame, textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=2)
        self.search_var.trace("w", self._filter_library)
        
        # Create file treeview
        tree_frame = ttk.Frame(self.library_label_frame)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.file_tree_columns = ("Path", "Type")
        self.file_tree = ttk.Treeview(tree_frame, columns=self.file_tree_columns, 
                                     selectmode="extended")
        
        # Configure tree columns
        self.file_tree.heading("#0", text="Name")
        self.file_tree.heading("Path", text="Path")
        self.file_tree.heading("Type", text="Type")
        
        self.file_tree.column("#0", width=150, stretch=tk.YES)
        self.file_tree.column("Path", width=200, stretch=tk.YES)
        self.file_tree.column("Type", width=60, stretch=tk.NO)
        
        # Add scrollbars to treeview
        self.tree_y_scroll = ttk.Scrollbar(tree_frame, orient="vertical", 
                                         command=self.file_tree.yview)
        self.tree_x_scroll = ttk.Scrollbar(tree_frame, orient="horizontal", 
                                         command=self.file_tree.xview)
        
        self.file_tree.configure(xscrollcommand=self.tree_x_scroll.set, 
                               yscrollcommand=self.tree_y_scroll.set)
        
        # Place tree and scrollbars
        self.tree_y_scroll.pack(side="right", fill="y")
        self.file_tree.pack(side="left", fill="both", expand=True)
        self.tree_x_scroll.pack(side="bottom", fill="x")
        
        # File operations buttons
        self.file_ops_frame = ttk.Frame(self.library_label_frame)
        self.file_ops_frame.pack(fill="x", padx=5, pady=5)
        
        self.new_file_btn = ttk.Button(self.file_ops_frame, text="New File", 
                                     command=self._create_new_file)
        self.new_folder_btn = ttk.Button(self.file_ops_frame, text="New Folder", 
                                       command=self._create_new_folder)
        self.delete_btn = ttk.Button(self.file_ops_frame, text="Delete", 
                                   command=self._delete_selected)
        
        self.new_file_btn.pack(side="left", padx=2, pady=2)
        self.new_folder_btn.pack(side="left", padx=2, pady=2)
        self.delete_btn.pack(side="left", padx=2, pady=2)
        
        # Batch operations frame
        self.batch_ops_frame = ttk.LabelFrame(self.library_frame, text="Batch Operations")
        self.batch_ops_frame.pack(fill="x", padx=5, pady=5)
        
        # Create a frame for batch buttons
        batch_buttons_frame = ttk.Frame(self.batch_ops_frame)
        batch_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        self.send_to_batch_btn = ttk.Button(batch_buttons_frame, text="Send to Line Edit", 
                                          command=self._send_to_batch_edit)
        self.send_to_batch_btn.pack(side="left", padx=5, fill="x", expand=True)
        
        self.send_to_full_regen_btn = ttk.Button(batch_buttons_frame, text="Send to Full Regen", 
                                          command=self._send_to_full_regen)
        self.send_to_full_regen_btn.pack(side="left", padx=5, fill="x", expand=True)
        
        # Bind events
        self.file_tree.bind("<Double-1>", self._on_file_double_click)
        self.file_tree.bind("<<TreeviewSelect>>", self._on_file_select)
        
        # Initialize library
        self._populate_library()

    def _populate_library(self, directory=None):
        """Populate the library tree with files and folders."""
        # Clear existing items
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)
        
        # Get the root directory
        if directory is None:
            # Use the configured library directory from settings
            directory = config_manager.get_library_path()
            
            # Validate the directory exists
            if not os.path.exists(directory):
                try:
                    # Try to create it
                    os.makedirs(directory)
                    logger.info(f"Created library directory: {directory}")
                except Exception as e:
                    # Show error message and prompt to browse for a valid directory
                    logger.error(f"Library directory does not exist and could not be created: {str(e)}")
                    messagebox.showerror("Library Path Error", 
                                      f"The configured library path does not exist:\n{directory}\n\nPlease select a valid directory.")
                    if self._browse_library_path(show_dialog=True):
                        # If user selected a valid directory, use that
                        directory = config_manager.get_library_path()
                    else:
                        # Use the application directory as fallback
                        directory = os.path.join(
                            str(get_project_root()),
                            "showup-editor-ui",
                            "library",
                        )
                        if not os.path.exists(directory):
                            os.makedirs(directory)
        
        # Insert root directory
        root_id = self.file_tree.insert("", "end", text="Library", values=(directory, "directory"))
        
        # Populate the tree
        self._add_directory_to_tree(directory, root_id)
        
        # Expand the root
        self.file_tree.item(root_id, open=True)
    
    def _add_directory_to_tree(self, directory, parent):
        """Add a directory and its contents to the tree."""
        try:
            for item in sorted(os.listdir(directory)):
                item_path = os.path.join(directory, item)
                
                # Skip hidden files and .bak files
                if item.startswith(".") or item.endswith(".bak"):
                    continue
                
                if os.path.isdir(item_path):
                    # Insert directory
                    dir_id = self.file_tree.insert(parent, "end", text=item, 
                                                values=(item_path, "directory"))
                    # Add its contents
                    self._add_directory_to_tree(item_path, dir_id)
                elif item.lower().endswith(".md"):
                    # Only display markdown files
                    self.file_tree.insert(parent, "end", text=item, 
                                        values=(item_path, "markdown"))
                # Other file types are not displayed in the tree
        except Exception as e:
            logger.error(f"Error adding directory to tree: {str(e)}")
    
    def _refresh_library(self):
        """Refresh the library tree."""
        self._populate_library()
        
    def _filter_library(self, *args):
        """Filter library based on search text."""
        search_text = self.search_var.get().lower()
        
        # If empty search, just refresh
        if not search_text:
            self._refresh_library()
            return
        
        # Otherwise, filter items
        for item_id in self.file_tree.get_children():
            self._filter_tree_item(item_id, search_text)
    
    def _filter_tree_item(self, item_id, search_text):
        """Recursively filter tree items based on search text."""
        # Check if this item matches
        item_text = self.file_tree.item(item_id, "text").lower()
        if search_text in item_text:
            # Keep this item visible
            return True
        
        # Check children
        visible_children = False
        for child_id in self.file_tree.get_children(item_id):
            if self._filter_tree_item(child_id, search_text):
                visible_children = True
        
        # Hide this item if neither it nor any children match
        if not visible_children:
            self.file_tree.detach(item_id)
        
        return visible_children
        
    def _browse_library_path(self, show_dialog=False):
        """Browse for a library directory and update the path entry"""
        # Get current path to start from
        current_path = self.library_path_var.get()
        start_dir = current_path if os.path.exists(current_path) else os.path.expanduser("~")
        
        # Ask user to select a directory
        new_path = filedialog.askdirectory(initialdir=start_dir, title="Select Library Directory")
        
        if new_path:
            # Update the entry field
            self.library_path_var.set(new_path)
            
            # If called with show_dialog=True, immediately save and reload
            if show_dialog:
                return self._save_library_path()
            return True
        return False
            
    def _browse_prompt_path(self, show_dialog=False):
        """Browse for a prompt library directory and update the path entry"""
        # Get current path to start from
        current_path = self.prompt_path_var.get()
        start_dir = current_path if os.path.exists(current_path) else os.path.expanduser("~")
        
        # Ask user to select a directory
        new_path = filedialog.askdirectory(initialdir=start_dir, title="Select Prompt Library Directory")
        
        if new_path:
            # Update the entry field
            self.prompt_path_var.set(new_path)
            
            # If called with show_dialog=True, immediately save and reload
            if show_dialog:
                return self._save_prompt_path()
            return True
        return False
            
    def _save_prompt_path(self):
        """Save the prompt library path to config"""
        new_path = self.prompt_path_var.get()
        
        # Validate path
        if not os.path.exists(new_path):
            try:
                # Try to create it
                os.makedirs(new_path)
                logger.info(f"Created prompt library directory: {new_path}")
            except Exception as e:
                # Show error message
                logger.error(f"Cannot create prompt library directory: {str(e)}")
                messagebox.showerror("Invalid Path", 
                                  f"The specified path does not exist and could not be created:\n{new_path}")
                return False
        
        # Save to config
        if config_manager.set_setting("library_prompts_path", new_path):
            self.update_status(f"Prompt library path updated to: {new_path}")
            return True
        else:
            messagebox.showerror("Configuration Error", "Failed to save prompt library path configuration.")
            return False
            
    def _browse_prompt_path(self, show_dialog=False):
        """Browse for a prompt library directory and update the path entry"""
        # Get current path to start from
        current_path = self.prompt_path_var.get()
        start_dir = current_path if os.path.exists(current_path) else os.path.expanduser("~")
        
        # Ask user to select a directory
        new_path = filedialog.askdirectory(initialdir=start_dir, title="Select Prompt Library Directory")
        
        if new_path:
            # Update the entry field
            self.prompt_path_var.set(new_path)
            
            # If called with show_dialog=True, immediately save and reload
            if show_dialog:
                return self._save_prompt_path()
            return True
        return False
            
    def _save_prompt_path(self):
        """Save the prompt library path to config"""
        new_path = self.prompt_path_var.get()
        
        # Validate path
        if not os.path.exists(new_path):
            try:
                # Try to create it
                os.makedirs(new_path)
                logger.info(f"Created prompt library directory: {new_path}")
            except Exception as e:
                # Show error message
                logger.error(f"Cannot create prompt library directory: {str(e)}")
                messagebox.showerror("Invalid Path", 
                                  f"The specified path does not exist and could not be created:\n{new_path}")
                return False
        
        # Save to config
        if config_manager.set_setting("library_prompts_path", new_path):
            self.update_status(f"Prompt library path updated to: {new_path}")
            return True
        else:
            messagebox.showerror("Configuration Error", "Failed to save prompt library path configuration.")
            return False
    
    def _save_library_path(self):
        """Save the library path to config and refresh the tree"""
        new_path = self.library_path_var.get()
        
        # Validate path
        if not os.path.exists(new_path):
            try:
                # Try to create it
                os.makedirs(new_path)
                logger.info(f"Created library directory: {new_path}")
            except Exception as e:
                # Show error message
                logger.error(f"Cannot create library directory: {str(e)}")
                messagebox.showerror("Invalid Path", 
                                  f"The specified path does not exist and could not be created:\n{new_path}")
                return False
        
        # Save to config
        if config_manager.set_library_path(new_path):
            # Refresh the library tree
            self._refresh_library()
            self.update_status(f"Library path updated to: {new_path}")
            return True
        else:
            messagebox.showerror("Configuration Error", "Failed to save library path configuration.")
            return False
        
    def _load_profiles(self):
        """Load system profiles from the learner_profile directory"""
        self.profiles = {}
        # Use the specified path for learner profiles
        showup_root = Path(
            os.environ.get("SHOWUP_ROOT", get_project_root())

        )
        profile_dir = str(
            showup_root / "showup-library" / "Student personas"
        )
        
        # Create profiles directory if it doesn't exist
        if not os.path.exists(profile_dir):
            try:
                os.makedirs(profile_dir)
                logger.info(f"Created profiles directory at {profile_dir}")
            except Exception as e:
                logger.error(f"Failed to create profiles directory: {str(e)}")
                return
        
        # Look for profile files (JSON format)
        try:
            for filename in os.listdir(profile_dir):
                if filename.endswith(".json"):
                    profile_path = os.path.join(profile_dir, filename)
                    try:
                        with open(profile_path, 'r', encoding='utf-8') as f:
                            profile_data = json.load(f)
                            
                            # Validate profile structure
                            if 'name' in profile_data and 'system' in profile_data:
                                profile_name = profile_data['name']
                                self.profiles[profile_name] = profile_data
                                logger.info(f"Loaded profile: {profile_name}")
                            else:
                                logger.warning(f"Invalid profile structure in {filename}")
                    except Exception as e:
                        logger.error(f"Error loading profile {filename}: {str(e)}")
            
            # Set default profile if available
            if self.profiles:
                default_profile = next(iter(self.profiles.keys()))
                self.profiles_dropdown_var.set(default_profile)
                logger.info(f"Set default profile to {default_profile}")
            else:
                # Create a default profile if none exist
                default_profile = {
                    "name": "Default",
                    "system": "You are Claude, an AI assistant helping with content enhancement.",
                    "description": "Basic assistant profile for general content editing."
                }
                
                self.profiles["Default"] = default_profile
                self.profiles_dropdown_var.set("Default")
                
                # Save the default profile
                default_profile_path = os.path.join(profile_dir, "default.json")
                try:
                    with open(default_profile_path, 'w', encoding='utf-8') as f:
                        json.dump(default_profile, f, indent=4)
                    logger.info("Created default profile")
                except Exception as e:
                    logger.error(f"Failed to save default profile: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error loading profiles: {str(e)}")
            # Create a fallback profile in memory
            self.profiles["Fallback"] = {
                "name": "Fallback",
                "system": "You are Claude, an AI assistant helping with content enhancement.",
                "description": "Fallback profile when loading from disk failed."
            }
            self.profiles_dropdown_var.set("Fallback")
            
    def _register_tabs_with_manager(self):
        """Register all tabs with the tab manager to ensure proper visibility tracking."""
        try:
            if not hasattr(self.tab_manager, 'tab_vars'):
                logger.warning("Tab manager is not properly initialized, cannot register tabs")
                return
                
            # Only register tabs that are actually managed by the notebook
            try:
                # Ensure the Enrich Lesson tab is properly added to the notebook
                enrich_tab_index = self.notebook.index(self.enrich_lesson_tab)
                if enrich_tab_index >= 0 and hasattr(self.tab_manager, 'tab_vars'):
                    if enrich_tab_index not in self.tab_manager.tab_vars:
                        # Add the tab to the tab manager's tracking
                        self.tab_manager.tab_frames[enrich_tab_index] = self.enrich_lesson_tab
                        self.tab_manager.tab_names[enrich_tab_index] = "Enrich Lesson"
                        # Create a visibility variable
                        var = tk.BooleanVar(value=True)
                        self.tab_manager.tab_vars[enrich_tab_index] = var
                        logger.info(f"Successfully registered Enrich Lesson tab at index {enrich_tab_index}")
            except Exception as e:
                # If there's an error, just log it but don't let it stop the application
                logger.warning(f"Non-critical error registering Enrich Lesson tab: {str(e)}")
        except Exception as e:
            # Catch any other exceptions to prevent startup failures
            logger.error(f"Error in tab registration: {str(e)}")
            # Don't raise the exception - allow the application to continue
    
    def _setup_file_tree_context_menu(self):
        """Set up the right-click context menu for the file tree."""
        # Create context menu
        self.file_tree_menu = tk.Menu(self, tearoff=0)
        self.file_tree_menu.add_command(label="Send to Batch Edit", command=self._send_to_batch_edit)
        self.file_tree_menu.add_command(label="Send to Full Document Regeneration", command=self._send_to_full_regen)
        self.file_tree_menu.add_command(label="Send to Markdown Splitter", command=self._send_to_md_splitter)
        self.file_tree_menu.add_command(label="Send to Markdown Converter", command=self._send_to_md_converter)
        self.file_tree_menu.add_separator()
        self.file_tree_menu.add_command(label="Rename", command=self._rename_selected)
        self.file_tree_menu.add_command(label="Delete", command=self._delete_selected)
        self.file_tree_menu.add_separator()
        self.file_tree_menu.add_command(label="Show in Explorer", command=self._show_in_explorer)
        
        # Bind right-click event to file tree
        self.file_tree.bind("<Button-3>", self._show_file_tree_context_menu)
        
        # Also set up context menu for text widgets
        self._setup_text_widget_context_menu()
        
    def _setup_text_widget_context_menu(self):
        """Set up right-click context menu for text widgets."""
        # Create context menu for text widgets
        self.text_widget_menu = tk.Menu(self, tearoff=0)
        
        # Add standard edit options
        self.text_widget_menu.add_command(label="Cut", command=lambda: self._text_widget_cut(),
                                       accelerator="Ctrl+X")
        self.text_widget_menu.add_command(label="Copy", command=lambda: self._text_widget_copy(),
                                       accelerator="Ctrl+C")
        self.text_widget_menu.add_command(label="Paste", command=lambda: self._text_widget_paste(),
                                       accelerator="Ctrl+V")
        self.text_widget_menu.add_separator()
        self.text_widget_menu.add_command(label="Select All", command=lambda: self._text_widget_select_all(),
                                       accelerator="Ctrl+A")
        self.text_widget_menu.add_separator()
        # Add AI analysis option
        self.text_widget_menu.add_command(label="Analyze Selected Text for AI Writing", 
                                       command=lambda: self._analyze_context_menu_selection())
        
        # Apply this context menu to all relevant text widgets
        self._bind_text_widget_context_menu()
    
    def _bind_text_widget_context_menu(self):
        """Bind the context menu to all relevant text widgets."""
        # Bind to selected text widget
        if hasattr(self, "selected_text_widget"):
            self._bind_context_menu_to_text_widget(self.selected_text_widget)
        
        # Bind to markdown editor if it exists
        if hasattr(self, "markdown_editor") and hasattr(self.markdown_editor, "text_editor"):
            self._bind_context_menu_to_text_widget(self.markdown_editor.text_editor)
        
        # Can add more bindings for other text widgets as needed
    
    def _bind_context_menu_to_text_widget(self, widget):
        """Bind the context menu to a specific text widget."""
        widget.bind("<Button-3>", self._show_text_widget_context_menu)
        
    def _show_text_widget_context_menu(self, event):
        """Show the context menu for text widgets."""
        # Get the widget that triggered the event
        widget = event.widget
        
        # Try to identify if there's a selection
        try:
            selected_text = widget.get(tk.SEL_FIRST, tk.SEL_LAST)
            # Enable the analyze option if text is selected
            self.text_widget_menu.entryconfig("Analyze Selected Text for AI Writing", state=tk.NORMAL)
        except tk.TclError:
            # Disable the analyze option if no text is selected
            self.text_widget_menu.entryconfig("Analyze Selected Text for AI Writing", state=tk.DISABLED)
        
        # Show the menu
        self.text_widget_menu.post(event.x_root, event.y_root)
    
    def _analyze_context_menu_selection(self):
        """Analyze text selected via context menu."""
        # This will be called from the context menu; we can just use the editor selection method
        self._analyze_editor_selection()
    
    def _text_widget_cut(self):
        """Cut selected text from the widget that has focus."""
        try:
            widget = self.focus_get()
            if hasattr(widget, "cut"):
                widget.cut()
            else:
                widget.event_generate("<<Cut>>")
        except:
            pass
    
    def _text_widget_copy(self):
        """Copy selected text from the widget that has focus."""
        try:
            widget = self.focus_get()
            if hasattr(widget, "copy"):
                widget.copy()
            else:
                widget.event_generate("<<Copy>>")
        except:
            pass
    
    def _text_widget_paste(self):
        """Paste text to the widget that has focus."""
        try:
            widget = self.focus_get()
            if hasattr(widget, "paste"):
                widget.paste()
            else:
                widget.event_generate("<<Paste>>")
        except:
            pass
    
    def _text_widget_select_all(self):
        """Select all text in the widget that has focus."""
        try:
            widget = self.focus_get()
            widget.tag_add(tk.SEL, "1.0", tk.END)
            widget.mark_set(tk.INSERT, "1.0")
            widget.see(tk.INSERT)
            return "break"
        except:
            pass
    
    def _show_file_tree_context_menu(self, event):
        """Show the context menu for the file tree on right-click."""
        # Select the item under cursor
        item = self.file_tree.identify_row(event.y)
        if item:
            self.file_tree.selection_set(item)
        
        # Show context menu
        try:
            self.file_tree_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.file_tree_menu.grab_release()
    
    def _on_file_double_click(self, event):
        """Handle double click on a file."""
        item_id = self.file_tree.focus()
        if not item_id:
            return
        
        # Get the file path
        item_values = self.file_tree.item(item_id, "values")
        if not item_values:
            return
        
        file_path = item_values[0]
        file_type = item_values[1] if len(item_values) > 1 else ""
        
        # Only handle files, not directories
        if file_type != "directory":
            # Open the file in the editor
            self._open_file(file_path)
    
    def _on_file_select(self, event):
        """Handle selection of files in the tree.

        If a Markdown file is selected, load its contents into the
        ``EnrichLessonPanel`` so the lesson appears in the "Original
        Lesson Content" editor.
        """
        """Handle selection of files in the tree."""
        selected = self.file_tree.selection()
        if not selected:
            return

        item_values = self.file_tree.item(selected[0], "values")
        if not item_values or len(item_values) < 2:
            return

        file_path = item_values[0]
        file_type = item_values[1]

        if file_type != "directory" and os.path.isfile(file_path):
            if file_path.endswith(".md") or file_path.endswith(".txt"):
                try:
                    self.enrich_lesson.load_current_lesson(file_path)
                except Exception as exc:
                    logger.error(f"Failed to load lesson for enrichment: {exc}")
    
    def _open_file(self, file_path):
        """Open a file in the appropriate panel."""
        try:
            if not os.path.isfile(file_path):
                logger.warning(f"Cannot open non-file: {file_path}")
                return
                
            # Check file extension to determine how to open it
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext in [".md", ".txt"]:
                # Open in the Markdown Editor tab by default
                self.notebook.select(self.markdown_editor_tab)
                self.markdown_editor.open_file(file_path)
                try:
                    self.enrich_lesson.load_current_lesson(file_path)
                except Exception as exc:
                    logger.error(f"Failed to load lesson for enrichment: {exc}")
                logger.info(f"Opened file: {file_path}")
            else:
                logger.warning(f"Unsupported file type: {ext}")
                messagebox.showwarning("Unsupported File", f"Files with extension {ext} are not supported for editing.")
        except Exception as e:
            logger.error(f"Error opening file: {str(e)}")
            messagebox.showerror("Error", f"Could not open file: {str(e)}")

    def on_close(self) -> None:
        """Handle closing of the main window."""
        try:
            if self.enrich_lesson:
                self.enrich_lesson.cleanup()
        except Exception as exc:
            logger.error(f"Error during EnrichLessonPanel cleanup: {exc}")
        finally:
            self.parent.destroy()
    
    def _create_new_file(self):
        """Create a new file in the selected directory."""
        # Get selected directory
        selected = self.file_tree.selection()
        parent_dir = None
        
        if selected:
            item_values = self.file_tree.item(selected[0], "values")
            if item_values and len(item_values) > 1:
                if item_values[1] == "directory":
                    parent_dir = item_values[0]
                else:
                    # If file is selected, use its parent directory
                    parent_id = self.file_tree.parent(selected[0])
                    if parent_id:
                        parent_values = self.file_tree.item(parent_id, "values")
                        if parent_values:
                            parent_dir = parent_values[0]
        
        # If no directory selected, use root
        if not parent_dir:
            root_id = self.file_tree.get_children()[0]  # First item should be root
            root_values = self.file_tree.item(root_id, "values")
            if root_values:
                parent_dir = root_values[0]
        
        # Ask for filename
        if parent_dir:
            filename = simpledialog.askstring("New File", "Enter filename (with .md extension):", 
                                           initialvalue="new_file.md")
            if filename:
                # Create the file
                file_path = os.path.join(parent_dir, filename)
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write("# New Document\n\nStart writing here...")
                    
                    # Refresh tree and open the new file
                    self._refresh_library()
                    self._open_file(file_path)
                    logger.info(f"Created new file: {file_path}")
                except Exception as e:
                    logger.error(f"Error creating file {file_path}: {str(e)}")
                    messagebox.showerror("Error", f"Could not create file: {str(e)}")
    
    def _create_new_folder(self):
        """Create a new folder in the selected directory."""
        # Get selected directory (similar to _create_new_file)
        selected = self.file_tree.selection()
        parent_dir = None
        
        if selected:
            item_values = self.file_tree.item(selected[0], "values")
            if item_values and len(item_values) > 1:
                if item_values[1] == "directory":
                    parent_dir = item_values[0]
                else:
                    # If file is selected, use its parent directory
                    parent_id = self.file_tree.parent(selected[0])
                    if parent_id:
                        parent_values = self.file_tree.item(parent_id, "values")
                        if parent_values:
                            parent_dir = parent_values[0]
        
        # If no directory selected, use root
        if not parent_dir:
            root_id = self.file_tree.get_children()[0]  # First item should be root
            root_values = self.file_tree.item(root_id, "values")
            if root_values:
                parent_dir = root_values[0]
        
        # Ask for folder name
        if parent_dir:
            folder_name = simpledialog.askstring("New Folder", "Enter folder name:")
            if folder_name:
                # Create the folder
                folder_path = os.path.join(parent_dir, folder_name)
                try:
                    os.makedirs(folder_path, exist_ok=True)
                    
                    # Refresh tree
                    self._refresh_library()
                    logger.info(f"Created new folder: {folder_path}")
                except Exception as e:
                    logger.error(f"Error creating folder {folder_path}: {str(e)}")
                    messagebox.showerror("Error", f"Could not create folder: {str(e)}")
    
    def _delete_selected(self):
        """Delete the selected files or directories."""
        selected_items = self.file_tree.selection()
        if not selected_items:
            return
            
        # Get selected files/directories info
        items_to_delete = []
        for item_id in selected_items:
            item_values = self.file_tree.item(item_id, "values")
            if not item_values:
                continue
                
            path = item_values[0]
            item_type = item_values[1]
            
            items_to_delete.append((path, item_type))
            
        if not items_to_delete:
            return
            
        # Confirm deletion
        total_files = len(items_to_delete)
        if total_files == 1:
            item_path = items_to_delete[0][0]
            msg = f"Delete {os.path.basename(item_path)}?"
        else:
            msg = f"Delete {total_files} selected items?"
            
        if not messagebox.askyesno("Confirm Deletion", msg):
            return
            
        # Perform deletion
        for path, item_type in items_to_delete:
            try:
                if item_type == "directory" or os.path.isdir(path):
                    shutil.rmtree(path)
                    logger.info(f"Deleted directory: {path}")
                else:
                    os.remove(path)
                    logger.info(f"Deleted file: {path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete {path}: {str(e)}")
                logger.error(f"Failed to delete {path}: {str(e)}")
                
        # Refresh the library
        self._refresh_library()
    
    def _send_to_batch_edit(self):
        """Send selected files to batch edit tab."""
        selected_items = self.file_tree.selection()
        
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select files to add to batch processing.")
            return
        
        # Get paths for the selected items
        selected_files = []
        for item_id in selected_items:
            # Get the full path from the tree view
            full_path = self.file_tree.item(item_id, "values")[0]
            
            # Check if it's a file
            if os.path.isfile(full_path):
                selected_files.append(full_path)
        
        if not selected_files:
            messagebox.showinfo("No Files", "No files were selected. Only files can be processed in batch.")
            return
        
        # Send the files to the batch processor
        self.batch_processor.prepare_batch_edit(selected_files)
        
        # Switch to the batch tab
        self.notebook.select(self.batch_tab)
        
        # Log the action
        logger.info(f"Sent {len(selected_files)} files to batch edit tab")
    
    def _send_to_full_regen(self):
        """Send selected files to the full document regeneration tab."""
        selected_items = self.file_tree.selection()
        
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select files to add to full document regeneration.")
            return
        
        # Get paths for the selected items
        selected_files = []
        for item_id in selected_items:
            # Get the full path from the tree view
            full_path = self.file_tree.item(item_id, "values")[0]
            
            # Check if it's a file
            if os.path.isfile(full_path):
                selected_files.append(full_path)
        
        if not selected_files:
            messagebox.showinfo("No Files", "No files were selected. Only files can be processed in batch.")
            return
        
        # Send the files to the full document regenerator
        self.full_doc_regenerator.prepare_batch_edit(selected_files)
        
        # Switch to the full document regeneration tab
        self.notebook.select(self.full_regen_tab)
        
        # Log the action
        logger.info(f"Sent {len(selected_files)} files to full document regeneration tab")
    
    def _send_to_md_splitter(self):
        """Send selected markdown files to the MD Splitter tab."""
        # Check if any markdown files are selected
        selected_markdown_files = []
        for item_id in self.file_tree.selection():
            item_values = self.file_tree.item(item_id, "values")
            if item_values and len(item_values) > 1:
                file_path = item_values[0]
                file_type = item_values[1]
                
                if file_type != "directory" and os.path.isfile(file_path) and file_path.lower().endswith(".md"):
                    selected_markdown_files.append(file_path)
        
        if not selected_markdown_files:
            messagebox.showinfo("No Markdown Files", "Please select at least one markdown (.md) file to split.")
            return
        
        # Switch to the splitter tab
        self.notebook.select(self.md_splitter_tab)
        
        # Trigger the split process if there's only one file
        if len(selected_markdown_files) == 1 and hasattr(self.markdown_splitter, "split_selected_files"):
            # Set the output directory to the same as the file if not already set
            if not self.markdown_splitter.output_dir_var.get().strip():
                self.markdown_splitter.output_dir_var.set(os.path.dirname(selected_markdown_files[0]))
            
            # Call the split function
            self.markdown_splitter.split_selected_files()
    
    def _send_to_md_converter(self):
        """Send selected markdown files to the MD to HTML converter tab."""
        # First switch to the MD to HTML tab
        self.notebook.select(self.md_to_html_tab)
        
        # Then trigger the conversion
        if hasattr(self.markdown_converter, "convert_selected_files"):
            self.markdown_converter.convert_selected_files()
        else:
            logger.error("Markdown Converter doesn't have convert_selected_files method")
            messagebox.showerror("Error", "Unable to convert files - Markdown Converter not properly initialized")
            
    def _send_to_file_renamer(self):
        """Send selected markdown files to the File Renamer tab for standardizing filenames."""
        # First switch to the File Renamer tab
        self.notebook.select(self.file_renamer_tab)
        
        # Then trigger the filename preview
        if hasattr(self.file_renamer, "preview_rename_files"):
            self.file_renamer.preview_rename_files()
        else:
            logger.error("File Renamer doesn't have preview_rename_files method")
            messagebox.showerror("Error", "Unable to preview files - File Renamer not properly initialized")
    
    def add_text_editor_tool_button(self, parent_frame):
        """
        Add a button for using Claude's text editor tool for token-efficient batch editing
        """
        text_editor_frame = ttk.LabelFrame(parent_frame, text="Token-Efficient Editing (Claude Opus 4)")
        text_editor_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Add an explanation
        explanation = ttk.Label(text_editor_frame, text="Use Claude's text editor tool for more token-efficient markdown editing")
        explanation.pack(padx=10, pady=5, anchor="w")
        
        # Create input field for edit instructions
        ttk.Label(text_editor_frame, text="Edit Instructions:").pack(padx=10, pady=2, anchor="w")
        self.text_editor_instructions = scrolledtext.ScrolledText(text_editor_frame, height=4, width=60)
        self.text_editor_instructions.pack(padx=10, pady=5, fill="both", expand=True)
        
        # Add a button for running the text editor tool
        text_editor_button = ttk.Button(
            text_editor_frame, 
            text="Process Selected Files with Text Editor Tool", 
            command=self.run_text_editor_tool
        )
        text_editor_button.pack(padx=10, pady=10)
        
        # Add a label for displaying token savings
        self.token_savings_label = ttk.Label(text_editor_frame, text="Token savings: 0")
        self.token_savings_label.pack(padx=10, pady=5)
        
    def run_text_editor_tool(self):
        """
        Process selected files with the text editor tool
        """
        # Check if batch processing is already happening
        if self.processing_batch:
            messagebox.showinfo("Already Processing", "Batch processing is already in progress.")
            return
            
        # Get the edit instructions from the text editor tool interface
        edit_instructions = self.batch_processor.edit_instructions_text.get("1.0", tk.END).strip()
        if not edit_instructions:
            messagebox.showinfo("Missing Instructions", "Please provide editing instructions.")
            return
            
        # Get any additional context (optional)
        context = self.batch_processor.context_text.get("1.0", tk.END).strip()
        
        # Check if any files are selected
        if not self.batch_processor.batch_files:
            messagebox.showinfo("No Files Selected", "Please select files for batch processing first.")
            return
            
        # Start batch processing
        self.processing_batch = True
        self.update_status("Processing files with text editor tool...")
        
        # Update UI
        self.batch_processor.cancel_batch_button.config(state="normal")
        
        # Start processing in a thread
        threading.Thread(
            target=self._run_text_editor_tool_thread,
            args=(edit_instructions, self.batch_processor.batch_files, context),
            daemon=True
        ).start()
    
    def _run_text_editor_tool_thread(self, edit_instructions, files, context=""):
        """Thread function for running the text editor tool"""
        try:
            # Call the batch processor's edit_files_with_text_editor method
            results = self.batch_processor.edit_files_with_text_editor(
                edit_instructions=edit_instructions,
                target_files=files,
                context=context
            )
            
            # Update UI when done
            self.parent.after(100, lambda: self._text_editor_tool_complete(results))
            
        except Exception as e:
            logger.error(f"Error in text editor tool thread: {str(e)}")
            self.parent.after(100, lambda: self._text_editor_tool_error(str(e)))
    
    def _text_editor_tool_complete(self, results):
        """Called when text editor tool processing is complete"""
        self.processing_batch = False
        self.batch_processor.cancel_batch_button.config(state="disabled")
        self.update_status(f"Text editor tool completed processing {len(results)} files")
        
    def _text_editor_tool_error(self, error_msg):
        """Called when text editor tool processing encounters an error"""
        self.processing_batch = False
        self.batch_processor.cancel_batch_button.config(state="disabled")
        self.update_status(f"Error in text editor tool: {error_msg}")
        messagebox.showerror("Error", f"An error occurred during text editor tool processing: {error_msg}")
    
    def toggle_local_cache(self):
        """
        Toggle the use of local cache based on user preference
        """
        from cache_utils import set_local_cache_enabled
        
        # Get the current setting
        use_local_cache = self.use_local_cache_var.get()
        
        # Update the global setting
        set_local_cache_enabled(use_local_cache)
        
        # Log the change
        if use_local_cache:
            logger.info("Local cache enabled (redundant with Claude's native caching)")
            self.update_status("Local cache enabled. Both caching systems are active.")
        else:
            logger.info("Local cache disabled in favor of Claude's native caching")
            self.update_status("Local cache disabled. Using only Claude's native caching.")

    def update_status(self, message):
        """Update the status display with a message.
        
        This method can be called by any module to update the main status area.
        
        Args:
            message: The message to display
        """
        # Log the status message
        logger.info(message)
        
        # If we're running in a main app with a status bar, update it
        if hasattr(self.main_app, 'status_bar') and self.main_app.status_bar:
            self.main_app.status_bar.config(text=message)
            self.main_app.update_idletasks()

    def _setup_selected_text_analysis(self):
        """Add UI elements for analyzing selected text for AI writing patterns."""
        # Create a frame for selected text analysis in the AI detection tab
        selected_text_frame = ttk.LabelFrame(self.ai_detect_tab, text="Analyze Selected Text")
        selected_text_frame.pack(fill="x", padx=5, pady=5)
        
        # Add button to analyze currently selected text in the editor
        editor_selection_frame = ttk.Frame(selected_text_frame)
        editor_selection_frame.pack(fill="x", padx=5, pady=5)
        
        analyze_selected_btn = ttk.Button(
            editor_selection_frame, 
            text="Analyze Currently Selected Text in Editor", 
            command=self._analyze_editor_selection
        )
        analyze_selected_btn.pack(side="left", padx=5, pady=5)
        
        editor_info_label = ttk.Label(
            editor_selection_frame, 
            text="Select text in any editor tab, then click to analyze"
        )
        editor_info_label.pack(side="left", padx=10, pady=5)
        
        # Add separator
        ttk.Separator(selected_text_frame, orient="horizontal").pack(fill="x", padx=5, pady=5)
        
        # Create text widget for pasting or editing text to analyze
        text_frame = ttk.Frame(selected_text_frame)
        text_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add label
        text_label = ttk.Label(text_frame, text="Or enter/paste text to analyze:")
        text_label.pack(side="top", anchor="w", padx=5, pady=2)
        
        # Add text widget with scrollbars
        text_widget_frame = ttk.Frame(text_frame)
        text_widget_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.selected_text_widget = scrolledtext.ScrolledText(text_widget_frame, wrap=tk.WORD, height=10)
        self.selected_text_widget.pack(side="left", fill="both", expand=True)
        
        # Create buttons frame
        buttons_frame = ttk.Frame(selected_text_frame)
        buttons_frame.pack(fill="x", padx=5, pady=5)
        
        # Add analyze button
        analyze_btn = ttk.Button(buttons_frame, text="Analyze Text", 
                              command=self._analyze_current_text)
        analyze_btn.pack(side="left", padx=5, pady=5)
        
        # Add clear button
        clear_btn = ttk.Button(buttons_frame, text="Clear", 
                            command=lambda: self.selected_text_widget.delete(1.0, tk.END))
        clear_btn.pack(side="left", padx=5, pady=5)
        
        # Add info label
        info_label = ttk.Label(buttons_frame, 
                             text="Analyzes text for AI writing patterns and generates a report")
        info_label.pack(side="left", padx=10, pady=5)
    
    def _analyze_current_text(self):
        """Analyze the text currently in the selected text widget."""
        # Get the text from the widget
        selected_text = self.selected_text_widget.get(1.0, tk.END)
        
        # Pass to the AI detector for analysis
        self.ai_detector.analyze_selected_text(selected_text)
    
    def _analyze_editor_selection(self):
        """Analyze text selected in any active editor tab."""
        # Find the active tab and get selected text
        selected_text = self._get_selected_text_from_active_editor()
        
        if selected_text:
            # Pass to the AI detector for analysis
            self.ai_detector.analyze_selected_text(selected_text)
        else:
            messagebox.showinfo("No Text Selected", "Please select some text in an editor tab first.")
    
    def _get_selected_text_from_active_editor(self):
        """Get selected text from the currently active editor tab."""
        # Check if we're in markdown editor tab
        if self.notebook.select() == str(self.markdown_editor_tab):
            if hasattr(self.markdown_editor, "text_editor") and self.markdown_editor.text_editor:
                try:
                    return self.markdown_editor.text_editor.get(tk.SEL_FIRST, tk.SEL_LAST)
                except tk.TclError:
                    # No selection
                    pass
        
        # Try to get selection from other text widgets in active tab
        active_tab = self.notebook.select()
        if active_tab:
            active_frame = self.notebook.nametowidget(active_tab)
            for widget in self._find_all_text_widgets(active_frame):
                try:
                    return widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                except (tk.TclError, AttributeError):
                    # No selection or not a text widget with selection capability
                    continue
        
        return None
    
    def _find_all_text_widgets(self, parent):
        """Recursively find all text widgets in a parent widget."""
        text_widgets = []
        
        for widget in parent.winfo_children():
            if isinstance(widget, (tk.Text, scrolledtext.ScrolledText)):
                text_widgets.append(widget)
            elif widget.winfo_children():
                text_widgets.extend(self._find_all_text_widgets(widget))
        
        return text_widgets

    def get_selected_files(self) -> list:
        """Get paths of files selected in the library panel
        
        Returns:
            list: List of absolute paths to the selected files
        """
        selected_items = self.file_tree.selection()
        selected_files = []
        
        for item_id in selected_items:
            # Get the item's values
            item_values = self.file_tree.item(item_id, "values")
            if item_values and len(item_values) >= 2:
                path = item_values[0]
                item_type = item_values[1]
                
                # Only add files, not directories
                if item_type.lower() in ["file", "markdown"]:
                    selected_files.append(path)
                elif os.path.isfile(path):  # Fallback check if it's actually a file
                    selected_files.append(path)
        
        # Store the selected files as an instance variable for other components to access
        self.selected_files = selected_files
        
        logger.info(f"Get selected files from library: {len(selected_files)} files selected")
        return selected_files

    def _open_file_in_editor(self):
        """Open the selected file in the markdown editor."""
        selected_items = self.file_tree.selection()
        
        if not selected_items:
            return
        
        for item_id in selected_items:
            item_values = self.file_tree.item(item_id, 'values')
            
            if not item_values or len(item_values) < 2:
                continue
            
            file_path = item_values[0]
            item_type = item_values[1]
            
            if item_type == "file" and os.path.isfile(file_path):
                # If it's a markdown file, open it in the editor
                if file_path.endswith(".md") or file_path.endswith(".txt"):
                    # Switch to the markdown editor tab
                    self.notebook.select(self.markdown_editor_tab)
                    
                    # Tell the markdown editor to open the file
                    self.markdown_editor.open_file(file_path)
                    
                    logger.info(f"Opened file in markdown editor: {file_path}")
                    break
                else:
                    # Try to open in system editor
                    self._open_in_system_editor()
    
    def _open_in_system_editor(self):
        """Open the selected file in the system's default editor."""
        selected_items = self.file_tree.selection()
        if not selected_items:
            return
            
        for item_id in selected_items:
            item_values = self.file_tree.item(item_id, "values")
            if not item_values or len(item_values) < 2:
                continue
                
            file_path = item_values[0]
            item_type = item_values[1]
            
            # Only open files, not directories
            if item_type != "directory" and os.path.isfile(file_path):
                try:
                    # Use the system's default application to open the file
                    os.startfile(file_path)
                    logger.info(f"Opened file in system editor: {file_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to open file: {str(e)}")
                    logger.error(f"Failed to open file in system editor: {str(e)}")
    
    def _rename_selected(self):
        """Rename the selected file or directory."""
        selected_items = self.file_tree.selection()
        if not selected_items:
            return
            
        # Get the selected item
        item_id = selected_items[0]  # Only rename one at a time
        item_values = self.file_tree.item(item_id, "values")
        if not item_values or len(item_values) < 2:
            return
            
        path = item_values[0]
        item_type = item_values[1]
        
        # Get current name and ask for new name
        current_name = os.path.basename(path)
        parent_dir = os.path.dirname(path)
        
        new_name = simpledialog.askstring("Rename", "Enter new name:", initialvalue=current_name)
        if not new_name or new_name == current_name:
            return
            
        # Create full new path
        new_path = os.path.join(parent_dir, new_name)
        
        # Check if target already exists
        if os.path.exists(new_path):
            messagebox.showerror("Error", f"Cannot rename: {new_name} already exists.")
            return
            
        try:
            # Rename the file or directory
            os.rename(path, new_path)
            logger.info(f"Renamed {path} to {new_path}")
            
            # Refresh tree
            self._refresh_library()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename: {str(e)}")
            logger.error(f"Failed to rename {path}: {str(e)}")
    
    def _show_in_explorer(self):
        """Show the selected file or directory in Windows Explorer."""
        selected_items = self.file_tree.selection()
        if not selected_items:
            return
            
        for item_id in selected_items:
            item_values = self.file_tree.item(item_id, "values")
            if not item_values:
                continue
                
            path = item_values[0]
            
            try:
                # If it's a file, select it in Explorer
                if os.path.isfile(path):
                    # Open explorer and select the file
                    subprocess.run(["explorer", "/select,", path])
                else:
                    # Open the directory
                    os.startfile(path)
                    
                logger.info(f"Opened in Explorer: {path}")
                break  # Only show one item
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open in Explorer: {str(e)}")
                logger.error(f"Failed to open in Explorer: {str(e)}")


            item_type = item_values[1]
            
            # Only add files, not directories
            if item_type != "directory" and os.path.isfile(path):
                regen_files.append(path)
                
        if not regen_files:
            messagebox.showinfo("No Files", "No valid files were selected.")
            return
            
        # Switch to full regeneration tab
        self.notebook.select(self.full_regen_tab)
        
        # Update full document regenerator with the files
        if hasattr(self, "full_doc_regenerator"):
            self.full_doc_regenerator.set_file_list(regen_files)
            
        logger.info(f"Sent {len(regen_files)} files to full document regeneration")
    
    def _send_to_md_splitter(self):
        """Send selected files to the markdown splitter tab."""
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select a file to split.")
            return
            
        # Get the selected markdown file (only process the first one)
        item_id = selected_items[0]  # Only send one file at a time
        item_values = self.file_tree.item(item_id, "values")
        if not item_values or len(item_values) < 2:
            return
            
        path = item_values[0]
        item_type = item_values[1]
        
        # Verify it's a markdown file
        if item_type != "directory" and os.path.isfile(path) and path.lower().endswith((".md", ".markdown")):
            # Switch to markdown splitter tab
            self.notebook.select(self.md_splitter_tab)
            
            # Set the file in the markdown splitter
            if hasattr(self, "md_splitter"):
                self.md_splitter.set_input_file(path)
                
            logger.info(f"Sent file to markdown splitter: {path}")
        else:
            messagebox.showinfo("Invalid File", "Please select a Markdown file (.md, .markdown).")
    
    def _send_to_md_converter(self):
        """Send selected files to the markdown converter tab."""
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("No Selection", "Please select files to convert.")
            return
            
        # Get paths of selected markdown files
        md_files = []
        for item_id in selected_items:
            item_values = self.file_tree.item(item_id, "values")
            if not item_values or len(item_values) < 2:
                continue
                
            path = item_values[0]
            item_type = item_values[1]
            
            # Only add markdown files
            if item_type != "directory" and os.path.isfile(path) and path.lower().endswith((".md", ".markdown")):
                md_files.append(path)
                
        if not md_files:
            messagebox.showinfo("No Files", "No valid Markdown files were selected.")
            return
            
        # Switch to markdown converter tab
        self.notebook.select(self.md_to_html_tab)
        
        # Update markdown converter with the files
        if hasattr(self, "md_converter"):
            self.md_converter.set_input_files(md_files)
            
        logger.info(f"Sent {len(md_files)} files to markdown converter")

    def _open_in_system_editor(self):
        """Open the selected file in the system's default editor."""
        selected_items = self.file_tree.selection()
        if not selected_items:
            return
            
        for item_id in selected_items:
            item_values = self.file_tree.item(item_id, "values")
            if not item_values or len(item_values) < 2:
                continue
                
            file_path = item_values[0]
            item_type = item_values[1]
            
            # Only open files, not directories
            if item_type != "directory" and os.path.isfile(file_path):
                try:
                    # Use the system's default application to open the file
                    os.startfile(file_path)
                    logger.info(f"Opened file in system editor: {file_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to open file: {str(e)}")
                    logger.error(f"Failed to open file in system editor: {str(e)}")
    
    def _rename_selected(self):
        """Rename the selected file or directory."""
        selected_items = self.file_tree.selection()
        if not selected_items:
            return
            
        # Get the selected item
        item_id = selected_items[0]  # Only rename one at a time
        item_values = self.file_tree.item(item_id, "values")
        if not item_values or len(item_values) < 2:
            return
            
        path = item_values[0]
        item_type = item_values[1]
        
        # Get current name and ask for new name
        current_name = os.path.basename(path)
        parent_dir = os.path.dirname(path)
        
        new_name = simpledialog.askstring("Rename", "Enter new name:", initialvalue=current_name)
        if not new_name or new_name == current_name:
            return
            
        # Create full new path
        new_path = os.path.join(parent_dir, new_name)
        
        # Check if target already exists
        if os.path.exists(new_path):
            messagebox.showerror("Error", f"Cannot rename: {new_name} already exists.")
            return
            
        try:
            # Rename the file or directory
            os.rename(path, new_path)
            logger.info(f"Renamed {path} to {new_path}")
            
            # Refresh tree
            self._refresh_library()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to rename: {str(e)}")
            logger.error(f"Failed to rename {path}: {str(e)}")
    
    def _show_in_explorer(self):
        """Show the selected file or directory in Windows Explorer."""
        selected_items = self.file_tree.selection()
        if not selected_items:
            return
            
        for item_id in selected_items:
            item_values = self.file_tree.item(item_id, "values")
            if not item_values:
                continue
                
            path = item_values[0]
            
            try:
                # If it's a file, select it in Explorer
                if os.path.isfile(path):
                    # Open explorer and select the file
                    subprocess.run(["explorer", "/select,", path])
                else:
                    # Open the directory
                    os.startfile(path)
                    
                logger.info(f"Opened in Explorer: {path}")
                break  # Only show one item
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open in Explorer: {str(e)}")
                logger.error(f"Failed to open in Explorer: {str(e)}")

    def _open_selected_file(self):
        """Open the selected file in the markdown editor."""
        selected_items = self.file_tree.selection()
        
        if not selected_items:
            return
        
        for item_id in selected_items:
            item_values = self.file_tree.item(item_id, 'values')
            
            if not item_values or len(item_values) < 2:
                continue
            
            file_path = item_values[0]
            item_type = item_values[1]
            
            if item_type == "file" and os.path.isfile(file_path):
                # If it's a markdown file, open it in the editor
                if file_path.endswith(".md") or file_path.endswith(".txt"):
                    # Switch to the markdown editor tab
                    self.notebook.select(self.markdown_editor_tab)
                    
                    # Tell the markdown editor to open the file
                    self.markdown_editor.open_file(file_path)
                    
                    logger.info(f"Opened file in markdown editor: {file_path}")
                    break
                else:
                    # Try to open in system editor
                    self._open_in_system_editor()
    
    def _on_file_double_click(self, event):
        """Handle double click on a file."""
        item_id = self.file_tree.focus()
        if not item_id:
            return
        
        # Get the file path
        item_values = self.file_tree.item(item_id, "values")
        if not item_values:
            return
        
        file_path = item_values[0]
        file_type = item_values[1] if len(item_values) > 1 else ""
        
        # Only handle files, not directories
        if file_type != "directory":
            # Open the file in the editor
            self._open_file(file_path)
    
    def _on_file_select(self, event):
        """Load the selected file into the Enrich Lesson panel."""
        selected = self.file_tree.selection()
        if not selected:
            return

        item_id = selected[0]
        item_values = self.file_tree.item(item_id, "values")
        if not item_values:
            return

        path = item_values[0]
        try:
            self.enrich_lesson.load_current_lesson(path)
        except Exception as exc:
            logger.error(f"Failed to load lesson for enrichment: {exc}")
    
    def _open_file(self, file_path):
        """Open a file in the appropriate panel."""
        try:
            if not os.path.isfile(file_path):
                logger.warning(f"Cannot open non-file: {file_path}")
                return
                
            # Check file extension to determine how to open it
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext in [".md", ".txt"]:
                # Open in the Markdown Editor tab by default
                self.notebook.select(self.markdown_editor_tab)
                self.markdown_editor.open_file(file_path)
                try:
                    # Also load the lesson into the Enrich panel so the
                    # "Original Lesson Content" editor shows the file
                    # contents immediately upon opening.
                    self.enrich_lesson.load_current_lesson(file_path)
                except Exception as exc:
                    logger.error(
                        f"Failed to load lesson for enrichment: {exc}",
                    )
                logger.info(f"Opened file: {file_path}")
            else:
                logger.warning(f"Unsupported file type: {ext}")
                messagebox.showwarning("Unsupported File", f"Files with extension {ext} are not supported for editing.")
        except Exception as e:
            logger.error(f"Error opening file: {str(e)}")
            messagebox.showerror("Error", f"Could not open file: {str(e)}")
    
    def _open_in_system_editor(self):
        """Open the selected file in the system's default editor."""
        selected_items = self.file_tree.selection()
        if not selected_items:
            return
            
        for item_id in selected_items:
            item_values = self.file_tree.item(item_id, "values")
            if not item_values or len(item_values) < 2:
                continue
                
            file_path = item_values[0]
            item_type = item_values[1]
            
            # Only open files, not directories
            if item_type != "directory" and os.path.isfile(file_path):
                try:
                    # Use the system's default application to open the file
                    os.startfile(file_path)
                    logger.info(f"Opened file in system editor: {file_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to open file: {str(e)}")
                    logger.error(f"Failed to open file in system editor: {str(e)}")
    
    def _show_in_explorer(self):
        """Show the selected file or directory in Windows Explorer."""
        selected_items = self.file_tree.selection()
        if not selected_items:
            return
            
        for item_id in selected_items:
            item_values = self.file_tree.item(item_id, "values")
            if not item_values:
                continue
                
            path = item_values[0]
            
            try:
                # If it's a file, select it in Explorer
                if os.path.isfile(path):
                    # Open explorer and select the file
                    subprocess.run(["explorer", "/select,", path])
                else:
                    # Open the directory
                    os.startfile(path)
                    
                logger.info(f"Opened in Explorer: {path}")
                break  # Only show one item
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open in Explorer: {str(e)}")
                logger.error(f"Failed to open in Explorer: {str(e)}")
    
    def _show_file_tree_context_menu(self, event):
        """Show the context menu for the file tree."""
        # Select the item under cursor
        item = self.file_tree.identify_row(event.y)
        if item:
            # If clicking on a new item, select it
            if item not in self.file_tree.selection():
                self.file_tree.selection_set(item)
            
            # Show the context menu
            self.file_tree_menu.post(event.x_root, event.y_root)
    
    def _open_selected_file(self):
        """Open the selected file in the markdown editor."""
        selected_items = self.file_tree.selection()
        
        if not selected_items:
            return
        
        for item_id in selected_items:
            item_values = self.file_tree.item(item_id, 'values')
            
            if not item_values or len(item_values) < 2:
                continue
            
            file_path = item_values[0]
            item_type = item_values[1]
            
            if item_type == "file" and os.path.isfile(file_path):
                # If it's a markdown file, open it in the editor
                if file_path.endswith(".md") or file_path.endswith(".txt"):
                    # Switch to the markdown editor tab
                    self.notebook.select(self.markdown_editor_tab)
                    
                    # Tell the markdown editor to open the file
                    self.markdown_editor.open_file(file_path)
                    
                    logger.info(f"Opened file in markdown editor: {file_path}")
                    break
                else:
                    # Try to open in system editor
                    self._open_in_system_editor()
    
    def _on_file_double_click(self, event):
        """Handle double click on a file."""
        item_id = self.file_tree.focus()
        if not item_id:
            return
        
        # Get the file path
        item_values = self.file_tree.item(item_id, "values")
        if not item_values:
            return
        
        file_path = item_values[0]
        file_type = item_values[1] if len(item_values) > 1 else ""
        
        # Only handle files, not directories
        if file_type != "directory":
            # Open the file in the editor
            self._open_file(file_path)
    
    def _on_file_select(self, event):
        """Load the selected file into the Enrich Lesson panel."""
        selected = self.file_tree.selection()
        if not selected:
            return

        item_id = selected[0]
        item_values = self.file_tree.item(item_id, "values")
        if not item_values:
            return

        path = item_values[0]
        try:
            self.enrich_lesson.load_current_lesson(path)
        except Exception as exc:
            logger.error(f"Failed to load lesson for enrichment: {exc}")
    
    def _open_file(self, file_path):
        """Open a file in the appropriate panel."""
        try:
            if not os.path.isfile(file_path):
                logger.warning(f"Cannot open non-file: {file_path}")
                return
                
            # Check file extension to determine how to open it
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext in [".md", ".txt"]:
                # Open in the Markdown Editor tab by default
                self.notebook.select(self.markdown_editor_tab)
                self.markdown_editor.open_file(file_path)
                try:
                    # Keep Enrich Lesson panel in sync when files are opened
                    self.enrich_lesson.load_current_lesson(file_path)
                except Exception as exc:
                    logger.error(
                        f"Failed to load lesson for enrichment: {exc}",
                    )
                logger.info(f"Opened file: {file_path}")
            else:
                logger.warning(f"Unsupported file type: {ext}")
                messagebox.showwarning("Unsupported File", f"Files with extension {ext} are not supported for editing.")
        except Exception as e:
            logger.error(f"Error opening file: {str(e)}")
            messagebox.showerror("Error", f"Could not open file: {str(e)}")
