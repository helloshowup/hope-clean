"""Simple Markdown Editor Module for ClaudeAIPanel"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog, Menu
from .path_utils import get_project_root

# Try to import pyperclip, but gracefully handle if it's missing
try:
    import pyperclip
    CLIPBOARD_AVAILABLE = True
except ImportError:
    CLIPBOARD_AVAILABLE = False
import logging

# Get logger
logger = logging.getLogger("output_library_editor")


class ToolTip:
    """Simple tooltip implementation for tkinter widgets."""
    
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
    
    def show_tooltip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        # Create a toplevel window
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)  # Remove window decorations
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        # Create tooltip content
        label = ttk.Label(
            self.tooltip_window, 
            text=self.text, 
            justify=tk.LEFT,
            background="#FFFFDD", 
            relief="solid", 
            borderwidth=1,
            padding=(5, 2)
        )
        label.pack()
    
    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class MarkdownEditor:
    """Provides a simple markdown editor without API calls."""
    
    def __init__(self, parent):
        """
        Initialize the markdown editor.
        
        Args:
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        self.current_file_path = None
        self.snippets = self._load_snippets()
        
        # Get access to AI detector if available
        self.ai_detector = getattr(self.parent, 'ai_detector', None)
    
    def setup_editor_tab(self):
        """Set up the markdown editor tab."""
        tab = self.parent.markdown_editor_tab
        
        # Create main frame with padding
        main_frame = ttk.Frame(tab, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Add toolbar frame
        toolbar_frame = ttk.Frame(main_frame)
        toolbar_frame.pack(fill="x", pady=(0, 10))
        
        # Add open button
        open_btn = ttk.Button(toolbar_frame, text="Open File", command=self.open_file)
        open_btn.pack(side=tk.LEFT, padx=5)
        
        # Add save button
        self.save_btn = ttk.Button(toolbar_frame, text="Save", command=self.save_file, state="disabled")
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        # Add save as button
        save_as_btn = ttk.Button(toolbar_frame, text="Save As", command=self.save_file_as)
        save_as_btn.pack(side=tk.LEFT, padx=5)
        
        # Add reload snippets button
        reload_btn = ttk.Button(toolbar_frame, text="Reload Snippets", command=self.reload_snippets)
        reload_btn.pack(side=tk.LEFT, padx=5)
        
        # Add copy to clipboard button - conditionally enabled based on pyperclip availability
        copy_btn = ttk.Button(
            toolbar_frame, 
            text="📋 Copy to Clipboard", 
            command=self.copy_to_clipboard,
            state="normal" if CLIPBOARD_AVAILABLE else "disabled"
        )
        copy_btn.pack(side=tk.LEFT, padx=5)
        if not CLIPBOARD_AVAILABLE:
            ToolTip(copy_btn, "Requires pyperclip package. Install with: pip install pyperclip")
        
        # Add status label
        self.status_label = ttk.Label(toolbar_frame, text="No file loaded")
        self.status_label.pack(side=tk.RIGHT, padx=5)
        
        # Create content frame
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True)
        
        # Create editor with line numbers
        editor_frame = ttk.LabelFrame(content_frame, text="Markdown Editor")
        editor_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Add text editor with syntax highlighting (basic)
        self.editor = scrolledtext.ScrolledText(editor_frame, wrap=tk.WORD, height=30, width=80, undo=True)
        self.editor.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Configure tags for basic syntax highlighting
        self.editor.tag_configure("heading", foreground="blue", font=("Arial", 12, "bold"))
        self.editor.tag_configure("emphasis", foreground="dark green")
        self.editor.tag_configure("code", foreground="dark red", background="#f0f0f0")
        self.editor.tag_configure("list", foreground="purple")
        
        # Bind key events for syntax highlighting and save shortcut
        self.editor.bind("<KeyRelease>", self._on_key_release)
        self.editor.bind("<Control-s>", lambda e: self.save_file())
        self.editor.bind("<Button-3>", self._show_context_menu)
        
        # Log setup completion
        logger.info("Markdown editor tab setup complete")
    
    def open_file(self, file_path=None):
        """Open a markdown file for editing."""
        if file_path is None:
            file_path = filedialog.askopenfilename(
                title="Open Markdown File",
                filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")]
            )
        
        if file_path:
            try:
                # Read file content
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Clear and update editor
                self.editor.config(state="normal")  # Ensure the widget is editable before modifications
                self.editor.delete(1.0, tk.END)
                self.editor.insert(tk.END, content)
                self.editor.config(state="normal")  # Keep it in normal state for editing
                
                # Update file path and UI
                self.current_file_path = file_path
                self.status_label.config(text=f"Editing: {os.path.basename(file_path)}")
                self.save_btn.config(state="normal")
                
                # Apply syntax highlighting
                self._highlight_syntax()
                
                # Log file opened
                logger.info(f"Opened file for direct editing: {file_path}")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Error opening file: {error_msg}")
                messagebox.showerror("Error", f"Could not open file: {error_msg}")
    
    def save_file(self):
        """Save the current file."""
        if not self.current_file_path:
            self.save_file_as()
            return
        
        try:
            # Get content from editor
            content = self.editor.get(1.0, tk.END)
            
            # Create backup of original file
            if os.path.exists(self.current_file_path):
                from showup_core.file_utils import create_timestamped_backup

                create_timestamped_backup(self.current_file_path)
            
            # Save content to file
            with open(self.current_file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Update status
            self.status_label.config(text=f"Saved: {os.path.basename(self.current_file_path)}")
            
            # Log save operation
            logger.info(f"Saved file: {self.current_file_path}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error saving file: {error_msg}")
            messagebox.showerror("Error", f"Could not save file: {error_msg}")
    
    def save_file_as(self):
        """Save the current file with a new name."""
        file_path = filedialog.asksaveasfilename(
            title="Save Markdown File",
            defaultextension=".md",
            filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        
        if file_path:
            # Update current file path
            self.current_file_path = file_path
            
            # Save file with new path
            self.save_file()
            
            # Enable save button
            self.save_btn.config(state="normal")
    
    def reload_snippets(self):
        """Reload text snippets from the snippets file."""
        self.snippets = self._load_snippets()
        messagebox.showinfo("Snippets Reloaded", f"Loaded {len(self.snippets)} snippets")
        logger.info(f"Reloaded {len(self.snippets)} snippets")
    
    def copy_to_clipboard(self) -> None:
        """Copy the current editor content to the clipboard."""
        # Get all content from the editor
        content = self.editor.get("1.0", tk.END)
        
        if not content.strip():
            messagebox.showinfo("Copy to Clipboard", "No content to copy")
            return
        
        # Check if pyperclip is available
        if not CLIPBOARD_AVAILABLE:
            messagebox.showinfo("Copy to Clipboard", 
                             "Clipboard functionality requires the pyperclip package.\n"
                             "Please install it using: pip install pyperclip")
            logger.warning("Attempted to copy to clipboard but pyperclip is not installed")
            return
            
        try:
            # Copy to clipboard
            pyperclip.copy(content)
            
            # Show brief confirmation
            self.status_label.config(text="Content copied to clipboard")
            
            # Reset status after 3 seconds
            self.parent.after(3000, lambda: self.status_label.config(
                text="No file loaded" if not self.current_file_path else f"Editing: {os.path.basename(self.current_file_path)}"))
            
            logger.info("Content copied to clipboard")
        except Exception as e:
            messagebox.showerror("Copy Failed", f"Failed to copy to clipboard: {str(e)}")
            logger.error(f"Failed to copy to clipboard: {str(e)}")
    
    def _on_key_release(self, event):
        """Handle key release events for real-time syntax highlighting."""
        # Apply syntax highlighting
        self._highlight_syntax()
    
    def _highlight_syntax(self):
        """Apply basic syntax highlighting to the markdown text."""
        try:
            # Make sure the editor is in a normal state before making changes
            current_state = str(self.editor.cget("state"))
            if current_state == "disabled":
                self.editor.config(state="normal")
            
            # Remove existing tags
            for tag in ["heading", "emphasis", "code", "list"]:
                self.editor.tag_remove(tag, "1.0", tk.END)
            
            # Get all text
            text = self.editor.get("1.0", tk.END)
            
            # Find and tag headings (# heading)
            line_num = 1
            for line in text.split("\n"):
                # Heading
                if line.strip().startswith("#"):
                    start_index = f"{line_num}.0"
                    end_index = f"{line_num}.{len(line)}"
                    self.editor.tag_add("heading", start_index, end_index)
                
                # List items
                if line.strip().startswith("- ") or line.strip().startswith("* ") or line.strip().startswith("1. "):
                    start_index = f"{line_num}.0"
                    end_index = f"{line_num}.{len(line)}"
                    self.editor.tag_add("list", start_index, end_index)
                
                line_num += 1
            
            # Find and tag inline code (`code`)
            start_index = "1.0"
            while True:
                # Find opening backtick
                code_start = self.editor.search("`", start_index, stopindex=tk.END)
                if not code_start:
                    break
                
                # Find closing backtick
                code_end = self.editor.search("`", f"{code_start}+1c", stopindex=tk.END)
                if not code_end:
                    break
                
                # Add tag
                self.editor.tag_add("code", code_start, f"{code_end}+1c")
                
                # Move start index past this code block
                start_index = f"{code_end}+1c"
            
            # Find and tag emphasis (*text* or _text_)
            for delimiter in ["*", "_"]:
                start_index = "1.0"
                while True:
                    # Find opening delimiter
                    emph_start = self.editor.search(delimiter, start_index, stopindex=tk.END)
                    if not emph_start:
                        break
                    
                    # Find closing delimiter
                    emph_end = self.editor.search(delimiter, f"{emph_start}+1c", stopindex=tk.END)
                    if not emph_end:
                        break
                    
                    # Add tag
                    self.editor.tag_add("emphasis", emph_start, f"{emph_end}+1c")
                    
                    # Move start index past this emphasis
                    start_index = f"{emph_end}+1c"
            
            # Restore the original state if it was disabled
            if current_state == "disabled":
                self.editor.config(state="disabled")
        except Exception as e:
            logger.error(f"Error in syntax highlighting: {str(e)}")
    
    def _load_snippets(self) -> list[str]:
        """
        Load text snippets from the snippets file in the input directory.
        
        Returns:
            list[str]: List of text snippets
        """
        snippets = []
        # Construct path to snippets file in the data/input directory
        snippets_file = os.path.join(
            str(get_project_root()),
            "showup-editor-ui",
            "data",
            "input",
            "snippets.txt",
        )
        
        try:
            if os.path.exists(snippets_file):
                with open(snippets_file, 'r', encoding='utf-8') as f:
                    snippets = [line.strip() for line in f.readlines() if line.strip()]
                logger.info(f"Loaded {len(snippets)} snippets from {snippets_file}")
            else:
                logger.warning(f"Snippets file not found: {snippets_file}")
        except Exception as e:
            logger.error(f"Error loading snippets: {str(e)}")
            
        return snippets
    
    def _insert_snippet(self, snippet: str) -> None:
        """
        Insert the selected snippet at the current cursor position.
        
        Args:
            snippet: The snippet text to insert
        """
        if self.editor:
            current_pos = self.editor.index(tk.INSERT)
            self.editor.insert(current_pos, snippet)
            logger.info(f"Inserted snippet at position {current_pos}")
    
    def _show_context_menu(self, event) -> None:
        """
        Show the context menu with snippets at the cursor position.
        
        Args:
            event: The mouse event that triggered the context menu
        """
        # Create a new context menu
        context_menu = Menu(self.editor, tearoff=0)
        
        # Add default menu items
        context_menu.add_command(label="Cut", command=lambda: self.editor.event_generate("<<Cut>>"))
        context_menu.add_command(label="Copy", command=lambda: self.editor.event_generate("<<Copy>>"))
        context_menu.add_command(label="Paste", command=lambda: self.editor.event_generate("<<Paste>>"))
        context_menu.add_separator()
        
        # Add AI detection option if there's selected text
        try:
            selected_text = self.editor.get(tk.SEL_FIRST, tk.SEL_LAST)
            if selected_text and self.ai_detector:
                context_menu.add_command(label="Analyze for AI Writing", command=self._analyze_selected_text)
                context_menu.add_separator()
        except tk.TclError:
            # No selection
            pass
        
        # Add snippets submenu if snippets exist
        if self.snippets:
            snippets_menu = Menu(context_menu, tearoff=0)
            for snippet in self.snippets:
                snippets_menu.add_command(
                    label=snippet,
                    command=lambda s=snippet: self._insert_snippet(s)
                )
            context_menu.add_cascade(label="Insert Snippet", menu=snippets_menu)
        
        # Display the context menu
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            # Make sure to release the grab
            context_menu.grab_release()

    def _analyze_selected_text(self) -> None:
        """
        Analyze the selected text for AI writing patterns and insert the report.
        """
        try:
            # Get the selected text
            selected_text = self.editor.get(tk.SEL_FIRST, tk.SEL_LAST)
            
            if not selected_text or not self.ai_detector:
                return
            
            # Get selection position
            sel_start = self.editor.index(tk.SEL_FIRST)
            
            # Analyze the text using AI detector module
            detection_result = self.ai_detector._detect_ai_patterns(selected_text)
            
            # Generate report
            report = self._format_ai_analysis_report(detection_result)
            
            # Insert the report above the selected text
            self.editor.insert(sel_start, report)
            
            # Log the analysis
            logger.info(f"AI writing analysis complete: {'Patterns detected' if detection_result['detected'] else 'No patterns detected'}")
            
        except Exception as e:
            logger.error(f"Error analyzing selected text: {str(e)}")
            messagebox.showerror("Analysis Error", f"Could not analyze text: {str(e)}")
    
    def _format_ai_analysis_report(self, detection_result: dict) -> str:
        """
        Format the AI analysis results into a readable report string.
        
        Args:
            detection_result: The detection results from _detect_ai_patterns
            
        Returns:
            str: The formatted report text
        """
        # Start with the prefix message and opening bracket
        report = "[Please update your content based on the following AI writing analysis: This report identifies several AI writing patterns in your text that need revision to ensure a more authentic, human-like writing style.\n"
        
        # Continue with the report content
        report += "AI WRITING PATTERN ANALYSIS REPORT\n"
        report += "=================================\n\n"
        
        # Add summary with AI score if available
        if detection_result["detected"]:
            ai_score = detection_result.get("ai_score", 0)
            score_assessment = "Low" if ai_score < 3 else "Medium" if ai_score < 6 else "High"
            
            report += "RESULT: AI PATTERNS DETECTED\n"
            report += f"Found {detection_result['count']} potential AI patterns.\n"
            report += f"AI Score: {ai_score} - {score_assessment} likelihood of AI-generated content\n\n"
            
            # Add proximity cluster information if available
            if "proximity_clusters" in detection_result and detection_result["proximity_clusters"] > 0:
                report += f"Found {detection_result['proximity_clusters']} clusters of closely positioned AI patterns\n"
                report += "(Proximity clusters increase likelihood of AI-generated content)\n\n"
                
        else:
            report += "RESULT: NO AI PATTERNS DETECTED\n"
            report += "The analyzed text appears to be human-written.\n\n"
        
        # Add pattern summary by category
        if detection_result["detected"]:
            report += "PATTERN SUMMARY BY CATEGORY:\n"
            report += "----------------------------\n"
            
            categories = {}
            for pattern in detection_result["patterns"]:
                category = pattern["category"]
                weight = pattern.get("weight", 1.0)  # Get pattern weight
                if category not in categories:
                    categories[category] = {"count": 0, "weight": 0}
                categories[category]["count"] += 1
                categories[category]["weight"] += weight
            
            # Sort categories by total weight (descending)
            sorted_categories = sorted(categories.items(), key=lambda x: x[1]["weight"], reverse=True)
            
            for category, data in sorted_categories:
                count = data["count"]
                weight = data["weight"]
                report += f"\u2022 {category}: {count} instances (weight: {weight:.1f})\n"
            
            report += "\n"
            
            # Add detailed pattern matches
            report += "DETAILED PATTERN MATCHES:\n"
            report += "------------------------\n"
            
            for i, pattern in enumerate(detection_result["patterns"]):
                weight = pattern.get("weight", 1.0)  # Get pattern weight
                report += f"{i+1}. Category: {pattern['category']} (weight: {weight:.1f})\n"
                report += f"   Pattern: {pattern['pattern']}\n"
                report += f"   Match: \"{pattern['match']}\"\n\n"
        
        # Add alternative suggestions if available
        if detection_result.get("alternatives") and detection_result["detected"]:
            report += "SUGGESTED ALTERNATIVES:\n"
            report += "----------------------\n"
            
            for match_text, alternatives in detection_result["alternatives"].items():
                if isinstance(alternatives, list) and alternatives:
                    # For list of alternatives
                    alt_text = ", ".join(alternatives[:5])  # Limit to 5 alternatives
                    if len(alternatives) > 5:
                        alt_text += ", ..."
                    report += f"\u2022 Instead of \"{match_text}\", consider: {alt_text}\n"
                elif isinstance(alternatives, str):
                    # For single alternative
                    report += f"\u2022 Instead of \"{match_text}\", consider: {alternatives}\n"
            
            report += "\n"
        
        # Add recommendations
        report += "RECOMMENDATIONS:\n"
        report += "----------------\n"
        if detection_result["detected"]:
            report += "Consider revising the following aspects to make the text more human-like:\n\n"
            
            if any(p["category"] == "Common Phrases" for p in detection_result["patterns"]):
                report += "\u2022 Replace common AI phrases with more natural language\n"
            
            if any(p["category"] == "Scenario_Prompts" for p in detection_result["patterns"]):
                report += "\u2022 Avoid 'imagine' and 'picture this' type scenarios that are common in AI writing\n"
            
            if any(p["category"] == "Repetitive Structures" for p in detection_result["patterns"]):
                report += "\u2022 Vary the structure to avoid predictable patterns\n"
            
            if any(p["category"] == "Overused Transitions" for p in detection_result["patterns"]):
                report += "\u2022 Use more diverse transitional phrases\n"
            
            if detection_result.get("proximity_clusters", 0) > 0:
                report += "\u2022 Break up clusters of AI-like phrases throughout your text\n"
            
            report += "\nNote: This analysis is based on common patterns in AI-generated text "
            report += "and may not be 100% accurate. Use your judgment when making revisions."
        else:
            report += "No AI patterns were detected. The text appears natural and human-like."
        
        # Add closing bracket
        report += "]\n\n"
        
        return report
