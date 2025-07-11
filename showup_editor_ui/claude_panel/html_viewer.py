"""HTML Viewer Module for ClaudeAIPanel"""

import os
import logging
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from .path_utils import get_project_root

# Get logger
logger = logging.getLogger("output_library_editor")

class HTMLViewerPanel:
    """Panel for viewing HTML files and copying their content to clipboard"""
    
    def __init__(self, parent):
        """
        Initialize the HTML viewer panel.
        
        Args:
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        self.selected_html_file = None
        self.html_files = {}
    
    def setup_html_viewer_tab(self):
        """Set up the HTML viewer tab."""
        tab = self.parent.html_viewer_tab
        
        # Create a PanedWindow to divide the tab
        self.paned_window = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left panel for file list
        self.left_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.left_frame, weight=1)
        
        # Right panel for HTML content
        self.right_frame = ttk.Frame(self.paned_window)
        self.paned_window.add(self.right_frame, weight=3)
        
        # Set up the left panel (file list)
        self._setup_file_tree()
        
        # Set up the right panel (HTML content viewer)
        self._setup_html_viewer()
        
        # Bind event to refresh when tab is selected
        self.parent.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        
        # Initial refresh
        self.refresh_file_tree()
        
        logger.info("HTML Viewer tab setup complete")
    
    def _on_tab_changed(self, event):
        """Handle tab change event to auto-refresh file list"""
        current_tab = self.parent.notebook.select()
        if current_tab == str(self.parent.html_viewer_tab):
            self.refresh_file_tree()
    
    def _setup_file_tree(self):
        """Set up the file tree view panel"""
        # Header with title and refresh button
        header_frame = ttk.Frame(self.left_frame)
        header_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(header_frame, text="HTML Files").pack(side="left")
        ttk.Button(header_frame, text="↻", width=3, command=self.refresh_file_tree).pack(side="right")
        
        # Search box
        search_frame = ttk.Frame(self.left_frame)
        search_frame.pack(fill="x", pady=(0, 5))
        
        ttk.Label(search_frame, text="Filter:").pack(side="left")
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self.filter_files())
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side="left", fill="x", expand=True)
        
        # Create tree view with scrollbars
        tree_frame = ttk.Frame(self.left_frame)
        tree_frame.pack(fill="both", expand=True)
        
        # Create scrollbars
        yscroll = ttk.Scrollbar(tree_frame, orient="vertical")
        yscroll.pack(side="right", fill="y")
        
        xscroll = ttk.Scrollbar(tree_frame, orient="horizontal")
        xscroll.pack(side="bottom", fill="x")
        
        # Create treeview
        self.file_tree = ttk.Treeview(tree_frame, yscrollcommand=yscroll.set, 
                                    xscrollcommand=xscroll.set, selectmode="browse")
        self.file_tree.pack(side="left", fill="both", expand=True)
        
        # Configure scrollbars
        yscroll.config(command=self.file_tree.yview)
        xscroll.config(command=self.file_tree.xview)
        
        # Configure treeview columns
        self.file_tree["columns"] = ("fullpath",)
        self.file_tree.column("#0", width=200, minwidth=100, stretch=tk.YES)
        self.file_tree.column("fullpath", width=0, stretch=tk.NO)  # Hidden column for path data
        
        self.file_tree.heading("#0", text="HTML Files", anchor="w")
        self.file_tree.heading("fullpath", text="Path", anchor="w")
        
        # Bind selection event
        self.file_tree.bind("<<TreeviewSelect>>", self.on_file_select)
    
    def _setup_html_viewer(self):
        """Set up the HTML content viewer panel."""
        # Header with title and copy button
        header_frame = ttk.Frame(self.right_frame)
        header_frame.pack(fill="x", pady=(0, 5))
        
        self.file_label = ttk.Label(header_frame, text="No file selected")
        self.file_label.pack(side="left")
        
        self.copy_button = ttk.Button(header_frame, text="Copy to Clipboard", 
                                     command=self.copy_to_clipboard)
        self.copy_button.pack(side="right")
        self.copy_button.config(state="disabled")  # Disabled until a file is selected
        
        # HTML content text area
        self.html_text = scrolledtext.ScrolledText(self.right_frame, wrap=tk.WORD, 
                                                 width=80, height=30, font=("Courier", 10))
        self.html_text.pack(fill="both", expand=True)
        self.html_text.config(state="disabled")
    
    def refresh_file_tree(self):
        """Refresh the HTML file tree."""
        try:
            # Clear existing items
            for item in self.file_tree.get_children():
                self.file_tree.delete(item)
            
            self.html_files = {}
            
            # Get the library directory path
            library_dir = self._get_library_dir()
            if not library_dir:
                return
            
            # Create the root node
            root_node = self.file_tree.insert("", "end", text="Library", open=True,
                                            values=(library_dir,))
            
            # Populate the tree recursively
            self._populate_tree(library_dir, root_node)
            
            # Expand the root node
            self.file_tree.item(root_node, open=True)
            
            logger.info(f"Found {len(self.html_files)} HTML files in library")
        except Exception as e:
            logger.error(f"Error refreshing HTML file tree: {str(e)}")
            messagebox.showerror("Error", f"Failed to refresh file tree: {str(e)}")
    
    def _get_library_dir(self):
        """Get the library directory path."""
        # Try multiple methods to find the library directory
        library_dir = None
        
        # Method 1: Try accessing through standard location
        base_dir = os.path.join(str(get_project_root()), "showup-editor-ui")
        potential_library_dir = os.path.join(base_dir, "library")
        if os.path.exists(potential_library_dir) and os.path.isdir(potential_library_dir):
            library_dir = potential_library_dir
        
        # Method 2: Try accessing through parent object, if Method 1 failed
        if library_dir is None and hasattr(self.parent, "main_app") and hasattr(self.parent.main_app, "file_browser"):
            library_dir = self.parent.main_app.file_browser.library_dir
        
        # Log the found directory
        if library_dir:
            logger.info(f"Using library directory: {library_dir}")
        else:
            logger.error("Could not determine library directory path")
            messagebox.showerror("Error", "Could not determine library directory path")
        
        return library_dir
    
    def _populate_tree(self, directory, parent_node):
        """Recursively populate the tree with directories and HTML files."""
        try:
            items = sorted(os.listdir(directory))
            
            # First, add all directories
            for item in items:
                # Skip hidden files and directories
                if item.startswith("."):
                    continue
                
                full_path = os.path.join(directory, item)
                if os.path.isdir(full_path):
                    # Create a directory node
                    dir_node = self.file_tree.insert(parent_node, "end", text=item,
                                                  values=(full_path,))
                    
                    # Recursively populate the directory
                    self._populate_tree(full_path, dir_node)
            
            # Then, add all HTML files
            for item in items:
                if item.startswith("."):
                    continue
                
                full_path = os.path.join(directory, item)
                if os.path.isfile(full_path) and item.endswith(".html"):
                    # Create a file node
                    file_node = self.file_tree.insert(parent_node, "end", text=item,
                                                   values=(full_path,))
                    
                    # Store the file path for later use
                    self.html_files[file_node] = full_path
        except Exception as e:
            logger.error(f"Error populating tree for {directory}: {str(e)}")
    
    def filter_files(self):
        """Filter files based on search text."""
        search_text = self.search_var.get().lower()
        
        if not search_text:
            # If search is empty, just show everything
            self.refresh_file_tree()
            return
        
        try:
            # Hide all nodes first
            for item_id in self._get_all_nodes():
                self.file_tree.detach(item_id)
            
            # Then, show only matching items and their parents
            for item_id in self._get_all_nodes():
                item_text = self.file_tree.item(item_id, "text").lower()
                if search_text in item_text and item_id in self.html_files:
                    # This is a matching HTML file, make sure it and its ancestors are visible
                    self._ensure_visible(item_id)
        except Exception as e:
            logger.error(f"Error filtering files: {str(e)}")
    
    def _get_all_nodes(self):
        """Get all node IDs in the tree."""
        def get_children(node):
            children = self.file_tree.get_children(node)
            result = list(children)
            for child in children:
                result.extend(get_children(child))
            return result
        
        return get_children("")
    
    def _ensure_visible(self, item_id):
        """Make sure an item and all its ancestors are visible."""
        # First, reattach the item itself
        parent = self.file_tree.parent(item_id)
        if parent:
            self._ensure_visible(parent)  # Recursively ensure parent is visible
            
            # Reattach this item to its parent
            self.file_tree.move(item_id, parent, "end")
            
            # Make sure parent is expanded
            self.file_tree.item(parent, open=True)
    
    def on_file_select(self, event):
        """Handle file selection event."""
        try:
            # Get selected item
            selection = self.file_tree.selection()
            if not selection:
                return
            
            selected_id = selection[0]
            if selected_id in self.html_files:
                # This is an HTML file, load its content
                file_path = self.html_files[selected_id]
                self.selected_html_file = file_path
                self.load_html_content(file_path)
                
                # Update UI
                rel_path = os.path.relpath(file_path, self._get_library_dir())
                self.file_label.config(text=f"File: {rel_path}")
                self.copy_button.config(state="normal")
            else:
                # This is a directory, just expand/collapse it
                is_open = self.file_tree.item(selected_id, "open")
                self.file_tree.item(selected_id, open=not is_open)
                
                # Clear content area
                self.html_text.config(state="normal")
                self.html_text.delete(1.0, tk.END)
                self.html_text.config(state="disabled")
                self.file_label.config(text="No file selected")
                self.copy_button.config(state="disabled")
                self.selected_html_file = None
        except Exception as e:
            logger.error(f"Error selecting file: {str(e)}")
            messagebox.showerror("Error", f"Failed to select file: {str(e)}")
    
    def load_html_content(self, file_path):
        """Load HTML content from the selected file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # Update text widget
            self.html_text.config(state="normal")
            self.html_text.delete(1.0, tk.END)
            self.html_text.insert(tk.END, content)
            self.html_text.config(state="disabled")  # Set it back to disabled after loading
            
            logger.info(f"Loaded HTML content from {file_path}")
        except Exception as e:
            logger.error(f"Error loading HTML content: {str(e)}")
            messagebox.showerror("Error", f"Failed to load HTML content: {str(e)}")
    
    def copy_to_clipboard(self):
        """Copy the HTML content to clipboard."""
        if self.selected_html_file:
            try:
                content = self.html_text.get(1.0, tk.END)
                self.parent.clipboard_clear()
                self.parent.clipboard_append(content)
                
                # Show a temporary success message
                original_text = self.copy_button.cget("text")
                self.copy_button.config(text="Copied!")
                
                # Reset button text after a delay
                def reset_button_text():
                    self.copy_button.config(text=original_text)
                
                self.copy_button.after(1500, reset_button_text)
                
                logger.info(f"Copied HTML content to clipboard from {self.selected_html_file}")
            except Exception as e:
                logger.error(f"Error copying to clipboard: {str(e)}")
                messagebox.showerror("Error", f"Failed to copy to clipboard: {str(e)}")
