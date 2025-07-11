"""Cache Management Module for ClaudeAIPanel"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import logging
from .path_utils import get_project_root

# Import cache utilities
from cache_utils import get_cache_instance

# Get logger
logger = logging.getLogger("output_library_editor")

class CacheManager:
    """Handles cache management for the ClaudeAIPanel."""
    
    def __init__(self, parent):
        """Initialize the cache manager.
        
        Args:
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        
    def setup_cache_tab(self):
        """Set up the cache management tab."""
        tab = self.parent.cache_tab
        
        # Create buttons frame
        buttons_frame = ttk.Frame(tab)
        buttons_frame.pack(fill="x", padx=10, pady=5)
        
        # Add refresh button
        self.refresh_btn = ttk.Button(buttons_frame, text="Refresh Cache List", command=self.refresh_cache_list)
        self.refresh_btn.pack(side="left", padx=5)
        
        # Add clear button
        self.clear_btn = ttk.Button(buttons_frame, text="Clear All Cache", command=self.clear_cache)
        self.clear_btn.pack(side="left", padx=5)
        
        # Add delete button
        self.delete_btn = ttk.Button(buttons_frame, text="Delete Selected Cache", command=self.delete_selected_cache)
        self.delete_btn.pack(side="left", padx=5)
        
        # Add cache info label
        self.cache_info_label = ttk.Label(buttons_frame, text="")
        self.cache_info_label.pack(side="right", padx=5)
        
        # Create cache list frame
        list_frame = ttk.LabelFrame(tab, text="Cache Items")
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Add cache list
        self.cache_list = tk.Listbox(list_frame, selectmode=tk.SINGLE)
        self.cache_list.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        # Add scrollbar to cache list
        list_scrollbar = ttk.Scrollbar(list_frame)
        list_scrollbar.pack(side="right", fill="y")
        self.cache_list.config(yscrollcommand=list_scrollbar.set)
        list_scrollbar.config(command=self.cache_list.yview)
        
        # Initialize cache list
        self.refresh_cache_list()
    
    def refresh_cache_list(self):
        """Refresh the cache list."""
        try:
            # Get cache instance
            cache = get_cache_instance()
            
            # Get cache items
            cache_items = cache.get_cache_items()
            cache_size = cache.get_cache_size()
            
            # Update info label
            self.cache_info_label.config(text=f"Cache Size: {cache_size:.2f} MB | Items: {len(cache_items)}")
            
            # Update list
            self.cache_list.delete(0, tk.END)
            for item in cache_items:
                self.cache_list.insert(tk.END, item)
                
            logger.info(f"Refreshed cache list: {len(cache_items)} items, {cache_size:.2f} MB")
        except Exception as e:
            logger.error(f"Error refreshing cache list: {str(e)}")
            messagebox.showerror("Cache Error", f"Error refreshing cache: {str(e)}")
    
    def clear_cache(self):
        """Clear the entire cache."""
        # Confirm operation
        if not messagebox.askyesno("Confirm Clear Cache",
                                  "Are you sure you want to clear the entire cache?"):
            return
        
        # Get cache instance
        cache = get_cache_instance()
        
        # Clear cache - pass max_age_days=0 to clear all files regardless of age
        count = cache.clear_cache(max_age_days=0)
        
        # Update cache list
        self.refresh_cache_list()
        
        # Show confirmation
        messagebox.showinfo("Cache Cleared", f"Successfully cleared {count} cache files.")
        logger.info(f"Cleared {count} cache files")
    
    def delete_selected_cache(self):
        """Delete the selected cache item."""
        # Get selected item
        try:
            selection = self.cache_list.curselection()
            if not selection:
                messagebox.showinfo("No Selection", "Please select a cache item to delete.")
                return
                
            selected_item = self.cache_list.get(selection[0])
            
            # Confirm operation
            if not messagebox.askyesno("Confirm Delete",
                                    f"Are you sure you want to delete\n{selected_item}"):
                return
            
            # Get cache instance
            cache = get_cache_instance()
            
            # Delete item
            if cache.delete_cache_item(selected_item):
                # Update cache list
                self.refresh_cache_list()
                logger.info(f"Deleted cache item: {selected_item}")
            else:
                messagebox.showerror("Delete Error", "Failed to delete cache item.")
                
        except Exception as e:
            logger.error(f"Error deleting cache item: {str(e)}")
            messagebox.showerror("Delete Error", f"Error deleting cache item: {str(e)}")
