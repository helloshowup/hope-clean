# enrich_lesson_view.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import json
import logging

logger = logging.getLogger(__name__)

class EnrichLessonView(ttk.Frame):
    def __init__(self, parent_tk_frame, controller):
        super().__init__(parent_tk_frame)
        self.controller = controller
        self.parent_tk_frame = parent_tk_frame # Used for .after() calls

        self._initialize_vars()
        self._setup_widgets()
        self._load_saved_handbook_path()

    def _initialize_vars(self):
        self.handbook_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        self.processing_stage_var = tk.StringVar(value="")
        
        # Widget references, initialized in _setup_widgets
        self.original_text: scrolledtext.ScrolledText = None
        self.enriched_text: scrolledtext.ScrolledText = None
        self.progress_bar: ttk.Progressbar = None
        self.processing_label: ttk.Label = None
        self.progress_frame_container: ttk.Frame = None # The frame holding progress bar and label
        self.result_content_frame: ttk.LabelFrame = None # Frame holding the notebook

    def _setup_widgets(self):
        # Title and description
        title_label = ttk.Label(self, text="Enrich Lesson Content", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 5), anchor="w")
        
        description_label = ttk.Label(self, text="Enhance lesson content with relevant sections from the project handbook using vector search.")
        description_label.pack(pady=(0, 10), anchor="w")
        
        # Handbook selection frame
        handbook_frame = ttk.LabelFrame(self, text="Project Handbook")
        handbook_frame.pack(fill="x", pady=5)
        
        handbook_path_entry = ttk.Entry(handbook_frame, textvariable=self.handbook_path_var, width=60)
        handbook_path_entry.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        
        browse_button = ttk.Button(handbook_frame, text="Browse...", command=self._browse_handbook_action)
        browse_button.pack(side="right", padx=5, pady=5)
        
        # Control buttons frame
        control_frame = ttk.Frame(self)
        control_frame.pack(fill="x", pady=10)
        
        # Button commands now call methods on self.controller
        # These controller methods will be named like _ui_request_action
        load_button = ttk.Button(control_frame, text="Load Current Lesson", command=self.controller._ui_request_load_lesson)
        load_button.pack(side="left", padx=5)
        
        enrich_button = ttk.Button(control_frame, text="Enrich Content", command=self.controller._ui_request_enrich_content)
        enrich_button.pack(side="left", padx=5)
        
        submit_button = ttk.Button(control_frame, text="Submit Enriched Content", command=self.controller._ui_request_submit_to_api)
        submit_button.pack(side="left", padx=5)
        
        # Status bar
        status_frame = ttk.Frame(self)
        status_frame.pack(fill="x", pady=(0, 5))
        
        status_label_text = ttk.Label(status_frame, text="Status:")
        status_label_text.pack(side="left", padx=5)
        
        status_value_label = ttk.Label(status_frame, textvariable=self.status_var)
        status_value_label.pack(side="left", padx=5)
        
        # Progress indicator frame (initially hidden)
        self.progress_frame_container = ttk.Frame(self)
        self.processing_label = ttk.Label(self.progress_frame_container, textvariable=self.processing_stage_var)
        self.processing_label.pack(side="top", fill="x", padx=5, pady=(0, 2))
        self.progress_bar = ttk.Progressbar(self.progress_frame_container, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side="top", fill="x", padx=5)
        # self.progress_frame_container.pack_forget() # Is hidden by not packing initially
        
        # Result frame with notebook for original and enriched content
        self.result_content_frame = ttk.LabelFrame(self, text="Content")
        self.result_content_frame.pack(fill="both", expand=True, pady=5)
        
        content_notebook = ttk.Notebook(self.result_content_frame)
        content_notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        original_tab = ttk.Frame(content_notebook)
        content_notebook.add(original_tab, text="Original Content")
        self.original_text = scrolledtext.ScrolledText(original_tab, wrap=tk.WORD, height=15) # Adjusted height
        self.original_text.pack(fill="both", expand=True, padx=5, pady=5)
        
        enriched_tab = ttk.Frame(content_notebook)
        content_notebook.add(enriched_tab, text="Enriched Content")
        self.enriched_text = scrolledtext.ScrolledText(enriched_tab, wrap=tk.WORD, height=15) # Adjusted height
        self.enriched_text.pack(fill="both", expand=True, padx=5, pady=5)

    def _browse_handbook_action(self):
        filetypes = [("Markdown files", "*.md"), ("Text files", "*.txt"), ("All files", "*.*")]
        file_path = filedialog.askopenfilename(filetypes=filetypes, title="Select Project Handbook")
        if file_path:
            self.handbook_path_var.set(file_path)
            self._save_handbook_path(file_path) # Call own method to save

    def _get_settings_path(self) -> str:
        # Helper to find settings.json, trying a couple of common locations relative to this file
        # Assumes claude_panel is a subdirectory of showup-editor-ui, and settings.json is in showup-editor-ui
        current_dir = os.path.dirname(os.path.abspath(__file__)) # claude_panel directory
        project_root_guess1 = os.path.dirname(current_dir) # showup-editor-ui directory
        settings_path1 = os.path.join(project_root_guess1, "settings.json")

        if os.path.exists(settings_path1):
            return settings_path1
        
        # Fallback if structure is different (e.g. settings.json is alongside claude_panel's parent)
        project_root_guess2 = os.path.dirname(project_root_guess1) 
        settings_path2 = os.path.join(project_root_guess2, "settings.json")
        if os.path.exists(settings_path2):
            return settings_path2
        
        logger.warning(f"settings.json not found at expected locations: {settings_path1} or {settings_path2}. Using default {settings_path1}")
        return settings_path1 # Default to one, save will create dirs if needed

    def _load_saved_handbook_path(self):
        try:
            settings_path = self._get_settings_path()
            if os.path.exists(settings_path):
                with open(settings_path, "r") as f:
                    settings = json.load(f)
                    if "handbook_path" in settings:
                        self.handbook_path_var.set(settings["handbook_path"])
            else:
                logger.info(f"Settings file not found at {settings_path}. No handbook path loaded.")
        except Exception as e:
            logger.error(f"Error loading saved handbook path: {e}", exc_info=True)

    def _save_handbook_path(self, path: str):
        try:
            settings_path = self._get_settings_path()
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            settings = {}
            if os.path.exists(settings_path):
                try:
                    with open(settings_path, "r") as f:
                        settings = json.load(f)
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode {settings_path}, will overwrite.")
            
            settings["handbook_path"] = path
            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving handbook path: {e}", exc_info=True)

    # --- UI Update Methods (called by Controller) ---
    def set_status(self, message: str):
        self.parent_tk_frame.after(0, lambda: self.status_var.set(message))

    def set_processing_stage(self, message: str):
        self.parent_tk_frame.after(0, lambda: self.processing_stage_var.set(message))

    def set_progress(self, value: float):
        self.parent_tk_frame.after(0, lambda: self.progress_var.set(value))

    def show_progress_indicators(self):
        # Ensure this is called on the main thread
        self.parent_tk_frame.after(0, self._do_show_progress_indicators)

    def _do_show_progress_indicators(self):
        if self.progress_frame_container and not self.progress_frame_container.winfo_ismapped():
            # Pack it before the result_content_frame
            self.progress_frame_container.pack(fill="x", pady=(0, 5), before=self.result_content_frame)

    def hide_progress_indicators(self):
        # Ensure this is called on the main thread
        self.parent_tk_frame.after(0, self._do_hide_progress_indicators)

    def _do_hide_progress_indicators(self):
        if self.progress_frame_container and self.progress_frame_container.winfo_ismapped():
            self.progress_frame_container.pack_forget()
        self.processing_stage_var.set("") # Reset stage text
        self.progress_var.set(0) # Reset progress bar

    def set_original_content(self, content: str):
        def _task():
            if self.original_text:
                self.original_text.delete(1.0, tk.END)
                self.original_text.insert(tk.END, content)
        self.parent_tk_frame.after(0, _task)

    def set_enriched_content(self, content: str):
        def _task():
            if self.enriched_text:
                self.enriched_text.delete(1.0, tk.END)
                self.enriched_text.insert(tk.END, content)
        self.parent_tk_frame.after(0, _task)

    def show_message(self, title: str, message: str, type: str = "info"):
        def _task():
            if type == "error":
                messagebox.showerror(title, message)
            elif type == "warning":
                messagebox.showwarning(title, message)
            else:
                messagebox.showinfo(title, message)
        self.parent_tk_frame.after(0, _task)

    # --- UI Data Retrieval Methods (called by Controller) ---
    def get_handbook_path(self) -> str:
        return self.handbook_path_var.get().strip()

    def get_original_content(self) -> str:
        return self.original_text.get(1.0, tk.END).strip() if self.original_text else ""

    def get_enriched_content(self) -> str:
        return self.enriched_text.get(1.0, tk.END).strip() if self.enriched_text else ""

if __name__ == '__main__':
    root = tk.Tk()
    root.title("Test EnrichLessonView")
    root.geometry("700x600")

    class MockController:
        # Mimic the parent ClaudeAIPanel's 'after' method for the view's UI updates
        def after(self, ms, callback, *args):
            return root.after(ms, callback, *args)

        def _ui_request_load_lesson(self):
            print("MockController: Load lesson requested")
            # Simulate getting content and updating view
            view.set_original_content("This is **original** lesson content from mock controller.")
            view.set_status("Mock lesson loaded.")

        def _ui_request_enrich_content(self):
            print("MockController: Enrich content requested")
            view.show_progress_indicators()
            view.set_processing_stage("Mock enriching step 1...")
            view.set_progress(30)
            root.after(1000, lambda: (
                view.set_processing_stage("Mock enriching step 2..."),
                view.set_progress(70),
                root.after(1000, lambda: (
                    view.set_progress(100),
                    view.set_processing_stage("Mock enrichment complete."),
                    view.set_enriched_content("This is the **enriched** mock content. It's much better now!"),
                    view.hide_progress_indicators(),
                    view.set_status("Enrichment complete."),
                    view.show_message("Success", "Lesson enriched successfully!")
                ))
            ))
            
        def _ui_request_submit_to_api(self):
            print("MockController: Submit to API requested")
            view.show_message("Info", "Submit to API clicked. Actual submission not implemented in mock.")

        def _load_saved_handbook_path(self):
            # This is called by the View itself, so the View's method will call this if it exists
            print("MockController: (View called) _load_saved_handbook_path")
            # view.handbook_path_var.set("/mock/path/handbook.txt") # View handles this now

        def _save_handbook_path(self, path):
            # This is called by the View itself
            print(f"MockController: (View called) _save_handbook_path with: {path}")

    # In a real app, the controller would be EnrichLessonPanel, and parent_tk_frame would be a tab from ClaudeAIPanel
    mock_controller = MockController()
    # The view needs its parent Tkinter frame (root in this test) and the controller
    view = EnrichLessonView(parent_tk_frame=root, controller=mock_controller)
    view.pack(fill="both", expand=True, padx=10, pady=10)
    root.mainloop()
