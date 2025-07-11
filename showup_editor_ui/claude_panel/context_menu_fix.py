# Add these methods to the ClaudeAIPanel class to fix the context menu

def _setup_file_tree_context_menu(self):
    """Set up right-click context menu for the file tree."""
    # Create context menu for file tree
    self.file_tree_menu = tk.Menu(self.file_tree, tearoff=0)
    
    # Add menu items
    self.file_tree_menu.add_command(label="Open", command=self._open_file_in_editor)
    self.file_tree_menu.add_command(label="Open in Default App", command=self._open_in_system_editor)
    self.file_tree_menu.add_separator()
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

def _show_file_tree_context_menu(self, event):
    """Show the context menu for the file tree."""
    # Select the item under the cursor
    item = self.file_tree.identify_row(event.y)
    if item:
        # If clicking on a new item, select it
        if item not in self.file_tree.selection():
            self.file_tree.selection_set(item)
        
        # Show the context menu
        self.file_tree_menu.post(event.x_root, event.y_root)

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
        item_type = item_values[1] if len(item_values) > 1 else ""
        
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
