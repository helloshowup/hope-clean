"""Enrich Lesson Panel - Enriches lesson content using vector search against handbook

Simplified implementation that works independently without depending on tab manager registration."""

import os
import sys
import time
import logging
import re
import json
import threading
import tkinter as tk  # Keep for type hints if necessary, but avoid direct use
from tkinter import ttk, filedialog, messagebox, scrolledtext
from .utils import (
    calculate_cosine_similarity,
    extract_local_keywords,
    DEFAULT_STOP_WORDS,
)
import pathlib
from collections import Counter
from typing import List, Optional
import concurrent.futures
import multiprocessing  # Added for ProcessPoolExecutor

# Import logging
logger = logging.getLogger(__name__)

# Import vector search modules from showup_tools package
try:
    logger.info("Attempting to import RAG system modules...")
    from showup_tools.simplified_app.rag_system.textbook_vector_db import TextbookVectorDB
    from showup_tools.simplified_app.rag_system.claude_api_client import ClaudeAPIClient
    logger.info(" RAG system modules imported successfully")
    logger.info(f"TextbookVectorDB: {TextbookVectorDB}")
    logger.info(f"ClaudeAPIClient: {ClaudeAPIClient}")
except ImportError as e:
    logger.error(f" Failed to import RAG system components: {e}")
    import traceback
    logger.error(f"Full traceback: {traceback.format_exc()}")
    # Keep them as None if import fails

# Top-level function to be run in a separate process for handbook indexing
def _perform_handbook_indexing_subprocess(
    handbook_content: str,
    textbook_id: str,
    force_rebuild: bool = False,
    pythonpath: str = "",
) -> tuple[bool, list[tuple[str, int]]]:
    """Performs handbook indexing in a subprocess.
    Instantiates ``TextbookVectorDB`` within the subprocess and returns
    progress data.

    Args:
        handbook_content: The content of the handbook.
        textbook_id: The ID of the textbook.
        force_rebuild: If ``True``, rebuild the index even if cached data exists.
        pythonpath: ``PYTHONPATH`` to apply inside the subprocess.

    Returns:
        Tuple ``(success, progress_log)`` where ``success`` indicates whether
        indexing completed and ``progress_log`` is a list of ``(stage, percent)``
        tuples collected during execution.

    Raises:
        Exception: If any error occurs during indexing.
    """
    # Ensure the subprocess has the correct PYTHONPATH before importing
    if pythonpath:
        os.environ["PYTHONPATH"] = pythonpath

    # Ensure RAG components are available in the subprocess context
    # We need to re-import TextbookVectorDB here because the subprocess
    # doesn't inherit the global context in the same way a thread does.
    local_tvdb_module = None
    try:
        # Attempt to import directly from the installed package
        from showup_tools.simplified_app.rag_system.textbook_vector_db import TextbookVectorDB as TVDB_Subprocess
        local_tvdb_module = TVDB_Subprocess
        if local_tvdb_module is None:
            raise ImportError("TextbookVectorDB imported as None in subprocess")
        local_vector_db = local_tvdb_module()
        print(f"[Subprocess] Successfully imported and instantiated TextbookVectorDB.")
    except ImportError as e_sub:
        print(f"[Subprocess ERROR] Failed to import TextbookVectorDB in subprocess: {e_sub}. Check sys.path.")
        # This is a critical failure for the subprocess.
        raise RuntimeError(f"Subprocess: TextbookVectorDB could not be imported or instantiated: {e_sub}") from e_sub

    print(f"[Subprocess] Starting index_textbook for {textbook_id}")
    progress: list[tuple[str, int]] = []

    def subprocess_progress_callback(stage: str, percent: int) -> None:
        print(
            f"[Subprocess Indexing Progress] {textbook_id} - {stage}: {percent}%"
        )
        progress.append((stage, percent))

    try:
        success = local_vector_db.index_textbook(
            textbook_content=handbook_content,
            textbook_id=textbook_id,
            force_rebuild=force_rebuild,
            progress_callback=subprocess_progress_callback,
        )
        logging.info(
            f"[Subprocess] index_textbook for {textbook_id} returned: {success}"
        )
        return success, progress
    except Exception as e_idx:
        print(f"[Subprocess ERROR] Exception during textbook indexing for {textbook_id}: {e_idx}")
        raise

class EnrichLessonView(ttk.Frame):
    """
    View class for the Enrich Lesson tab.
    Handles the creation and layout of all UI components.
    """
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.parent_frame = parent
        self.controller = controller
        self.pack(fill="both", expand=True)
        self.setup_ui()

    def setup_ui(self):
        """Creates and arranges the UI widgets."""
        # Main frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Handbook selection frame
        handbook_frame = ttk.LabelFrame(main_frame, text="Project Handbook")
        handbook_frame.pack(fill="x", pady=5)

        ttk.Label(handbook_frame, text="Path:").pack(side="left", padx=5, pady=5)
        self.handbook_path_var = tk.StringVar()
        self.handbook_path_entry = ttk.Entry(handbook_frame, textvariable=self.handbook_path_var, width=80)
        self.handbook_path_entry.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        self.browse_button = ttk.Button(handbook_frame, text="Browse...", command=self.controller.select_handbook)
        self.browse_button.pack(side="left", padx=5, pady=5)

        # Paned window for content areas
        content_panes = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        content_panes.pack(fill="both", expand=True, pady=5)

        # Original content frame
        original_frame = ttk.LabelFrame(content_panes, text="Original Lesson Content")
        content_panes.add(original_frame, weight=1)
        self.original_content_text = scrolledtext.ScrolledText(original_frame, wrap=tk.WORD, height=15)
        self.original_content_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Enriched content frame
        enriched_frame = ttk.LabelFrame(content_panes, text="Enriched Content (Preview)")
        content_panes.add(enriched_frame, weight=1)
        self.enriched_content_text = scrolledtext.ScrolledText(enriched_frame, wrap=tk.WORD, height=15, state="disabled")
        self.enriched_content_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Control frame
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill="x", pady=5)

        self.enrich_button = ttk.Button(
            control_frame,
            text="Enrich Content",
            command=self.controller.enrich_content,
            state="disabled",
        )
        self.enrich_button.pack(side="left", padx=(0, 5))

        # Enable/disable enrich button based on presence of original content
        self.original_content_text.bind("<<Modified>>", self._on_original_text_modified)

        self.apply_button = ttk.Button(control_frame, text="Apply to Lesson", command=self.controller.apply_enrichment_to_lesson)
        self.apply_button.pack(side="left", padx=5)

        self.force_rebuild_var = tk.BooleanVar(value=False)
        self.force_rebuild_cb = ttk.Checkbutton(
            control_frame,
            text="Force rebuild index",
            variable=self.force_rebuild_var,
        )
        self.force_rebuild_cb.pack(side=tk.RIGHT, padx=5)

        # Status bar
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", pady=(5, 0))
        
        self.status_label_var = tk.StringVar(value="Status: Ready")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_label_var)
        self.status_label.pack(side="left", fill="x", expand=True)
        
        self.progress_bar = ttk.Progressbar(status_frame, orient="horizontal", mode="indeterminate")
        # Do not pack it until it's needed

    def show_progress_bar(self):
        self.progress_bar.pack(side="right", fill="x", expand=True, padx=5)
        self.progress_bar.start()

    def hide_progress_bar(self):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()

    def _update_enrich_button_state(self) -> None:
        """Enable or disable enrich button based on original content."""
        if self.get_original_content():
            self.enrich_button.config(state="normal")
        else:
            self.enrich_button.config(state="disabled")

    def _on_original_text_modified(self, event=None) -> None:
        """Callback to update button state when original text changes."""
        self._update_enrich_button_state()
        if event:
            self.original_content_text.edit_modified(False)

    def set_status(self, message, busy=False):
        """Updates the status label and progress bar."""
        self.status_label_var.set(f"Status: {message}")
        if busy:
            self.show_progress_bar()
            self.enrich_button.config(state="disabled")
        else:
            self.hide_progress_bar()
            self._update_enrich_button_state()
        self.parent_frame.update_idletasks()

    def get_original_content(self):
        """Returns the text from the original content area."""
        return self.original_content_text.get("1.0", tk.END).strip()

    def set_enriched_content(self, content):
        """Sets the text in the enriched content area."""
        self.enriched_content_text.config(state="normal")
        self.enriched_content_text.delete("1.0", tk.END)
        self.enriched_content_text.insert(tk.END, content)
        self.enriched_content_text.config(state="disabled")

    def get_handbook_path(self):
        """Returns the handbook path from the entry field."""
        return self.handbook_path_var.get().strip()

    def set_original_content(self, content: str):
        """Sets the text in the original content text area."""
        self.original_content_text.delete("1.0", tk.END)
        if content:
            self.original_content_text.insert("1.0", content)
        self._update_enrich_button_state()

    def set_handbook_path(self, path):
        """Sets the handbook path in the entry field."""
        self.handbook_path_var.set(path)


class EnrichLessonPanel:
    """Controller for the lesson enrichment feature."""
    ClaudeAPIClient_instance: Optional[ClaudeAPIClient] = None

    def __init__(self, enrich_tab_frame, parent_controller, markdown_editor):
        self.parent_controller = parent_controller
        self.markdown_editor = markdown_editor
        self.parent_frame = enrich_tab_frame
        self.view = EnrichLessonView(self.parent_frame, self)
        
        self.executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=1,
            mp_context=multiprocessing.get_context("spawn"),
        )

        # State variables
        self.current_lesson_content: str = ""
        self.enriched_content: str = ""
        self.current_file_path: Optional[str] = None
        self.textbook_id: Optional[str] = None
        self._loading_active: bool = False
        self.timeout_timer: Optional[threading.Timer] = None

        # Initialize API clients and services
        if EnrichLessonPanel.ClaudeAPIClient_instance is None and ClaudeAPIClient:
            EnrichLessonPanel.ClaudeAPIClient_instance = ClaudeAPIClient()
        self.claude_client = EnrichLessonPanel.ClaudeAPIClient_instance
        
        if TextbookVectorDB:
            self.vector_db = TextbookVectorDB()
        else:
            self.vector_db = None
            messagebox.showerror("Initialization Error", "Vector DB components could not be loaded.")
            self.view.set_status("Error: Vector DB not available.")

        # Load last used handbook path
        self.load_settings()

    def load_lesson(self, file_path: str, content: str):
        """
        Loads the content of a lesson file into the enrichment panel UI.
        This method is called by the parent controller when a file is selected.
        """
        logger.info(f"Attempting to load lesson: {file_path}")
        self.current_file_path = file_path
        self.current_lesson_content = content
        self.view.set_original_content(content)
        if file_path:
            logger.info(f"Lesson content for '{os.path.basename(file_path)}' loaded into Enrich panel.")
        else:
            logger.info("Enrich panel cleared.")

    def cleanup(self):
        """Clean up resources, like the thread/process pool."""
        logging.info("Shutting down ProcessPoolExecutor.")
        if self.executor:
            self.executor.shutdown(wait=False, cancel_futures=True)
        if self.timeout_timer:
            self.timeout_timer.cancel()

    def get_settings_path(self) -> str:
        """Returns the path to the settings file."""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        settings_path = os.path.join(current_dir, '..', '..', 'settings.json')
        return os.path.normpath(settings_path)

    def save_settings(self):
        """Saves the last used handbook path."""
        settings_path = self.get_settings_path()
        try:
            settings = {}
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
            settings['last_handbook_path'] = self.view.get_handbook_path()
            with open(settings_path, 'w') as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving settings: {e}")

    def load_settings(self):
        """Loads the last used handbook path."""
        settings_path = self.get_settings_path()
        if not os.path.exists(settings_path):
            return
        try:
            with open(settings_path, 'r') as f:
                settings = json.load(f)
                last_path = settings.get('last_handbook_path')
                if last_path and os.path.exists(last_path):
                    self.view.set_handbook_path(last_path)
                    logging.info(f"Loaded last handbook path: {last_path}")
        except Exception as e:
            logging.error(f"Error loading settings: {e}")

    def _ui_request_load_lesson(self):
        """Load the lesson currently selected in the editor or library."""
        path = self.current_file_path or self.markdown_editor.current_file_path
        if path:
            self.load_current_lesson(path)
        else:
            messagebox.showinfo(
                "No file",
                "Select a lesson in the Library pane first.",
            )

    def _ui_request_enrich_content(self):
        """Start the enrichment process from the UI."""
        self.enrich_content()

    def _ui_request_submit_to_api(self):
        """Apply enriched content back to the main editor from the UI."""
        self.apply_enrichment_to_lesson()

    def select_handbook(self):
        """Opens a file dialog to select the handbook file."""
        path = filedialog.askopenfilename(
            title="Select Handbook File",
            filetypes=[("Text & Markdown", "*.txt *.md"), ("All files", "*.*")]
        )
        if path:
            self.view.set_handbook_path(path)
            self.save_settings()

    def load_current_lesson(self, file_path: str):
        """Loads lesson content from the given file path."""
        if not file_path or not os.path.isfile(file_path):
            messagebox.showerror("File Error", "Invalid file path provided.")
            return

        if not file_path.lower().endswith(('.md', '.txt')):
            messagebox.showinfo("File Type", "Please select a Markdown (.md) or Text (.txt) file.")
            return

        try:
            with open(file_path, "r", encoding="utf-8", errors='ignore') as f:
                self.current_lesson_content = f.read()

            normalized_path = os.path.normpath(file_path)
            self.current_file_path = normalized_path
            if hasattr(self.parent_controller, "set_path_field"):
                try:
                    self.parent_controller.set_path_field(normalized_path)
                except Exception as e:
                    logging.error(f"Error syncing path field: {e}")
            self.view.original_content_text.delete("1.0", tk.END)
            self.view.original_content_text.insert("1.0", self.current_lesson_content)
            self.view.set_status(f"Loaded: {os.path.basename(file_path)}")
            logging.info(f"Loaded lesson content from {file_path}")
        except Exception as e:
            logging.error(f"Error loading lesson content: {e}")
            messagebox.showerror("File Load Error", f"Failed to load lesson content: {e}")
            self.view.set_status("Error loading content")

    def enrich_content(self):
        """Starts the lesson enrichment process."""
        handbook_path = self.view.get_handbook_path()
        original_content = self.view.get_original_content()

        if not handbook_path or not os.path.exists(handbook_path):
            messagebox.showerror("Handbook Error", "Handbook file not found. Please select a valid handbook.")
            return

        if not original_content:
            messagebox.showerror("Content Error", "Please load or enter lesson content first.")
            return

        if self._loading_active:
            messagebox.showinfo("In Progress", "Enrichment is already in progress.")
            return

        self._loading_active = True
        self.current_lesson_content = original_content
        self.view.set_status("Starting enrichment...", busy=True)

        enrich_thread = threading.Thread(
            target=self._run_enrichment_flow,
            args=(handbook_path,),
            daemon=True
        )
        enrich_thread.start()

    def _run_enrichment_flow(self, handbook_path: str):
        """Orchestrates the enrichment process with robust error handling."""
        try:
            # --- 1. Read Handbook File ---
            try:
                self.parent_controller.after(0, lambda: self.view.set_status("Reading handbook file...", busy=True))
                with open(handbook_path, 'r', encoding='utf-8', errors='ignore') as f:
                    handbook_content = f.read()
                self.textbook_id = os.path.splitext(os.path.basename(handbook_path))[0]
            except FileNotFoundError:
                raise RuntimeError(f"Handbook file not found at: {handbook_path}")
            except Exception as e:
                raise RuntimeError(f"Failed to read handbook file: {e}")

            # --- 2. Index Handbook in Subprocess ---
            try:
                self.parent_controller.after(
                    0,
                    lambda: self.view.set_status(
                        "Indexing handbook (this may take a moment)...", busy=True
                    ),
                )
                future = self.executor.submit(
                    _perform_handbook_indexing_subprocess,
                    handbook_content,
                    self.textbook_id,
                    self.view.force_rebuild_var.get(),
                    os.environ.get("PYTHONPATH", ""),
                )
                self.parent_controller.after(
                    0,
                    lambda: self.view.set_status(
                        "Indexing handbook… (working)", busy=True
                    ),
                )

                indexing_success, progress_log = future.result(timeout=600)
                for stage, pct in progress_log:
                    self.view.set_status(f"{stage} ({pct}%)", busy=True)
                if not indexing_success:
                    raise RuntimeError(
                        "Handbook indexing process failed internally."
                    )
            except TimeoutError:
                raise RuntimeError("Handbook indexing timed out after 10 minutes.")
            except Exception as e:
                raise RuntimeError(f"An error occurred during handbook indexing: {e}")

            # --- 3. Query Vector DB for Context (RAG) ---
            try:
                self.parent_controller.after(0, lambda: self.view.set_status("Handbook indexed. Searching for relevant content...", busy=True))
                query_text = self.current_lesson_content[:1000]
                retrieved_docs = self.vector_db.query_textbook(
                    self.textbook_id, query_text, top_k=3
                )
                if not retrieved_docs:
                    logging.warning("No relevant context found in the handbook for the given lesson.")
                    retrieved_context = "No specific context was found in the handbook for this lesson."
                else:
                    retrieved_context = "\n\n---\n\n".join([doc['content'] for doc in retrieved_docs])
                logging.info(f"Retrieved context for enrichment:\n{retrieved_context}")
            except Exception as e:
                raise RuntimeError(f"Failed to query the vector database: {e}")

            # --- 4. Call Claude API for Enrichment ---
            try:
                self.parent_controller.after(0, lambda: self.view.set_status("Enriching with AI...", busy=True))
                prompt = (
                    "You are an expert instructional designer. Your task is to enrich the following lesson content "
                    "by integrating relevant information from the provided handbook context. The goal is to make the lesson more comprehensive, practical, and insightful.\n\n"
                    "Here is the context from the handbook:\n--- (Handbook Context) ---\n"
                    + retrieved_context + 
                    "\n--- (End of Handbook Context) ---\n\n"
                    "Here is the original lesson content:\n--- (Original Lesson) ---\n"
                    + self.current_lesson_content + 
                    "\n--- (End of Original Lesson) ---\n\n"
                    "Please rewrite and enrich the original lesson content. Ensure the final output is a complete, coherent lesson, not just a list of suggestions. "
                    "Maintain a consistent and engaging tone. Format the output in Markdown."
                )
                api_response = self.claude_client.call_claude(prompt, max_tokens=2048, temperature=0.5)
                if not api_response:
                    raise RuntimeError("The AI model did not return a response. Please check API status or logs.")
                self.enriched_content = api_response
            except Exception as e:
                raise RuntimeError(f"Failed to get enrichment from AI: {e}")

            # --- 5. Final UI Updates ---
            self.parent_controller.after(0, lambda: self.view.set_enriched_content(self.enriched_content))
            self.parent_controller.after(0, lambda: self.view.set_status("Enrichment complete!", busy=False))

        except Exception as e:
            error_message = str(e)
            logging.error(f"Enrichment flow failed: {error_message}", exc_info=True)
            self.parent_controller.after(0, lambda: self.view.set_status(f"Error: {error_message}", busy=False))
            self.parent_controller.after(0, lambda: messagebox.showerror("Enrichment Error", error_message))
        finally:
            self.parent_controller.after(0, self._set_loading_inactive)

    def _set_loading_inactive(self):
        """Sets the loading flag to False. Must be called on the main thread."""
        self._loading_active = False

    def apply_enrichment_to_lesson(self):
        """Applies the enriched content back to the main lesson editor."""
        if not self.enriched_content:
            messagebox.showwarning("No Content", "There is no enriched content to apply.")
            return

        if not hasattr(self.parent_controller, 'text_area'):
            messagebox.showerror("Error", "Could not find the main text editor to apply changes.")
            return

        if messagebox.askyesno(
            "Confirm Apply",
            "This will replace the content of the current lesson in the main editor with the enriched version. Are you sure you want to continue?"
        ):
            try:
                self.view.set_status("Applying enriched content...", busy=True)
                main_text_area = self.parent_controller.text_area
                main_text_area.delete("1.0", "end")
                main_text_area.insert("1.0", self.enriched_content)
                self.view.set_status("Enriched content applied to lesson.", busy=False)
                logging.info(f"Applied enriched content to file: {self.current_file_path}")
            except Exception as e:
                logging.error(f"Failed to apply enriched content: {e}", exc_info=True)
                messagebox.showerror("Error", f"An error occurred while applying the content: {e}")
                self.view.set_status(f"Error applying content: {e}", busy=False)
