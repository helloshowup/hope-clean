"""Batch Processing Module for ClaudeAIPanel"""

import os
import sys
import time
import logging
import shutil
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import json
import threading
from .path_utils import get_project_root
from showup_tools.showup_core.claude_api_consts import LINE_EDIT_HEADER

# Import Claude API functions directly from the module
from claude_api import Client  # noqa: E402

# Constants from the legacy claude-api package no longer exist, so we define
# simplified versions here for backwards compatibility.
CONTEXT_SYSTEM_PROMPT = (
    "You are a helpful assistant that prepares editing context for documents."
)
CONTEXT_USER_PROMPT_TEMPLATE = (
    "{prompt}\n\n## Learner Profile\n{learner_profile}\n\n## Content\n{file_content}"
)

# Cache utilities

# Get logger
logger = logging.getLogger("output_library_editor")


def send_claude_edit_request(cookie: str, markdown_text: str, instructions: str,
                             context: str = "") -> str:
    """Send an edit request to Claude using the modern Client API."""
    client = Client(cookie)
    conversation_id = client.create_new_chat()["uuid"]
    prompt_parts = [LINE_EDIT_HEADER, f"Instructions:\n{instructions.strip()}" ]
    if context:
        prompt_parts.append(f"Context:\n{context.strip()}")
    prompt_parts.append(f"Markdown:\n{markdown_text}")
    prompt = "\n\n".join(prompt_parts)
    return client.send_message(prompt, conversation_id)


def generate_claude_context(cookie: str, prompt: str, system_prompt: str) -> str:
    """Generate context using Claude via the modern API."""
    client = Client(cookie)
    conversation_id = client.create_new_chat()["uuid"]
    combined = f"{system_prompt}\n\n{prompt}"
    return client.send_message(combined, conversation_id)


class BatchProcessor:
    """Handles batch processing of files for the ClaudeAIPanel."""

    def __init__(self, batch_edit_tab, parent):
        """
        Initialize the batch processor.

        Args:
            batch_edit_tab: The batch edit tab
            parent: The parent ClaudeAIPanel instance
        """
        self.parent = parent
        self.batch_edit_tab = batch_edit_tab
        self.batch_files = []  # List to store batch file paths
        self.batch_results = {}  # Dictionary to store batch results
        self.processing_batch = False  # Flag to indicate batch processing
        self.batch_thread = None

    def setup_batch_tab(self):
        """Set up the batch processing tab with a simplified interface."""
        # Create the main frame for this tab
        main_frame = ttk.Frame(self.batch_edit_tab, padding="10")
        main_frame.pack(fill="both", expand=True)

        # Create side-by-side layout
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill="both", expand=True, padx=5, pady=5)

        # Left pane for file selection
        file_frame = ttk.LabelFrame(paned_window, text="Files")
        paned_window.add(file_frame, weight=1)

        # Right pane for configuration
        config_frame = ttk.LabelFrame(paned_window, text="Batch Processing")
        paned_window.add(config_frame, weight=1)

        # File selection components
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)

        add_files_btn = ttk.Button(
            btn_frame, text="Add Files", command=self.select_files_for_batch
        )
        add_files_btn.pack(side=tk.LEFT, padx=5)

        add_dir_btn = ttk.Button(
            btn_frame, text="Add Directory", command=self.select_directory_for_batch
        )
        add_dir_btn.pack(side=tk.LEFT, padx=5)

        clear_btn = ttk.Button(btn_frame, text="Clear", command=self.clear_batch)
        clear_btn.pack(side=tk.LEFT, padx=5)

        # Files listbox
        self.batch_files_listbox = tk.Listbox(
            file_frame, selectmode=tk.EXTENDED, height=15
        )
        self.batch_files_listbox.pack(fill="both", expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(
            self.batch_files_listbox,
            orient="vertical",
            command=self.batch_files_listbox.yview,
        )
        scrollbar.pack(side=tk.RIGHT, fill="y")
        self.batch_files_listbox.config(yscrollcommand=scrollbar.set)

        # Configuration components - Description
        description_frame = ttk.Frame(config_frame)
        description_frame.pack(fill="x", padx=5, pady=5)

        description = ttk.Label(description_frame, text="Batch processing uses:")
        description.pack(anchor="w")

        bullet_frame = ttk.Frame(description_frame)
        bullet_frame.pack(fill="x", padx=20, pady=5)

        bullet1 = ttk.Label(
            bullet_frame, text="• The prompt from the 'Prompt Config' tab"
        )
        bullet1.pack(anchor="w")

        bullet2 = ttk.Label(
            bullet_frame, text="• The learner profile from the 'Prompt Config' tab"
        )
        bullet2.pack(anchor="w")

        bullet3 = ttk.Label(
            bullet_frame,
            text="• Files will be processed one by one with context generation",
        )
        bullet3.pack(anchor="w")

        bullet4 = ttk.Label(
            bullet_frame, text="• Original files will be backed up with .bak extension"
        )
        bullet4.pack(anchor="w")

        # View prompt button
        view_prompt_btn = ttk.Button(
            config_frame, text="View Current Prompt", command=self._show_current_prompt
        )
        view_prompt_btn.pack(pady=10)

        # Process button
        process_frame = ttk.Frame(config_frame)
        process_frame.pack(fill="x", padx=5, pady=10)

        self.process_btn = ttk.Button(
            process_frame, text="Process Batch", command=self.process_batch_edit
        )
        self.process_btn.pack(side=tk.LEFT, padx=5)

        self.cancel_btn = ttk.Button(
            process_frame,
            text="Cancel",
            command=self.cancel_batch_processing,
            state="disabled",
        )
        self.cancel_btn.pack(side=tk.LEFT, padx=5)

        # Add status text at the bottom
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var)
        self.status_label.pack(pady=5)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            main_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.pack(fill="x", padx=10, pady=5)

        # Log setup completion
        logger.info("Batch processor tab setup")

    def prepare_batch_edit(self, files):
        """Prepare the batch edit panel with selected files."""
        # Clear existing batch files
        self.batch_files = []
        self.batch_files_listbox.delete(0, tk.END)

        # Add the new files
        self.batch_files = files
        for f in files:
            self.batch_files_listbox.insert(tk.END, f)

        # Log how many files are selected
        logger.info(f"Selected {len(files)} files for batch editing")

    def process_batch_edit(self):
        """Process all selected files with the current prompt and configuration."""
        # Check if there are files to process
        batch_files = self.get_batch_files()
        if not batch_files:
            messagebox.showwarning("No Files", "Please select files to process.")
            return

        # Get current prompt from the prompt manager
        if (
            not hasattr(self.parent, "prompt_manager")
            or not self.parent.prompt_manager.selected_prompt
        ):
            messagebox.showwarning(
                "No Prompt", "Please select a prompt in the Prompt Config tab."
            )
            return

        # Get prompt content
        prompt_text = ""
        if self.parent.prompt_manager.selected_prompt == "[Custom Prompt]":
            # Get custom prompt from text editor
            prompt_text = self.parent.prompt_manager.prompt_content.get(
                1.0, tk.END
            ).strip()
        else:
            prompt_name = self.parent.prompt_manager.selected_prompt
            if prompt_name in self.parent.prompt_manager.prompts:
                # Access the content key from the prompt dictionary
                prompt_text = self.parent.prompt_manager.prompts[prompt_name]["content"]

        if not prompt_text or not prompt_text.strip():
            messagebox.showwarning(
                "Empty Prompt",
                "The selected prompt is empty. Please select a different prompt.",
            )
            return

        prompt_text = prompt_text.strip()
        if (
            "[EDIT:" not in prompt_text.upper()
            and "INSERT" not in prompt_text.upper()
            and "REPLACE" not in prompt_text.upper()
        ):
            prompt_text = f"{LINE_EDIT_HEADER}\n\n{prompt_text}"

        # Get learner profile from the prompt manager - profiles are stored in parent.profiles
        selected_profile = self.parent.prompt_manager.selected_profile
        learner_profile = ""

        if selected_profile and selected_profile in self.parent.profiles:
            # Access the system field from the profile dictionary
            learner_profile = self.parent.profiles[selected_profile]["system"]

        # Log batch processing start
        logger.info(
            f"Starting batch processing with prompt '{self.parent.prompt_manager.selected_prompt}' and profile '{selected_profile}'"
        )
        logger.info(f"Processing {len(batch_files)} files")

        # Set UI state for processing
        self.processing_batch = True
        self.progress_var.set(0)
        self.status_var.set("Starting batch processing...")
        self.process_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        # Start processing in a thread
        self.batch_thread = threading.Thread(
            target=self._process_files, args=(batch_files, prompt_text, learner_profile)
        )
        self.batch_thread.daemon = True
        self.batch_thread.start()

    def cancel_batch_processing(self):
        """Cancel batch processing."""
        if self.processing_batch and self.batch_thread and self.batch_thread.is_alive():
            self.processing_batch = False
            logger.info("Batch processing cancelled")
            self.status_var.set("Cancelling...")
            self.cancel_btn.config(state="disabled")

    def _update_progress(self, index, total):
        """Update progress bar and status."""
        progress = (index / total) * 100
        self.progress_var.set(progress)
        self.status_var.set(f"Processing {index} of {total} files...")

    def _process_files(self, files, prompt, learner_profile):
        """Process each file in the batch with the given prompt and learner profile.

        Args:
            files (list): List of file paths to process
            prompt (str): Enhancement prompt to use
            learner_profile (str): Target learner profile to use
        """
        prompt = prompt.strip()
        if (
            "[EDIT:" not in prompt.upper()
            and "INSERT" not in prompt.upper()
            and "REPLACE" not in prompt.upper()
        ):
            prompt = f"{LINE_EDIT_HEADER}\n\n{prompt}"

        # Begin batch processing
        logger.info(
            f"Starting batch processing of {len(files)} files with prompt '{prompt[:50]}...'"
        )

        # Track progress
        start_time = time.time()
        total_files = len(files)
        processed_files = 0
        failed_files = 0

        # Process each file
        for i, file_path in enumerate(files):
            # Check if processing was cancelled
            if not self.processing_batch:
                logger.info("Batch processing cancelled")
                break

            # Update progress
            self.progress_var.set((i / total_files) * 100)
            self.status_var.set(
                f"Processing file {i+1} of {total_files}: {os.path.basename(file_path)}"
            )
            self.parent.update_idletasks()

            try:
                # Log file processing start
                logger.info(f"Processing file {i+1}/{total_files}: {file_path}")

                # Read the file
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()

                # Skip empty files
                if not file_content.strip():
                    logger.warning(f"Skipping empty file: {file_path}")
                    continue

                # First generate context based on the learner profile
                context = ""
                if learner_profile:
                    logger.info(
                        f"Generating context for {os.path.basename(file_path)}..."
                    )

                    # Replace hardcoded template with the imported template using .format()
                    full_prompt = CONTEXT_USER_PROMPT_TEMPLATE.format(
                        prompt=prompt,
                        learner_profile=learner_profile,
                        file_content=file_content,
                    )

                    try:
                        # Log context generation step
                        logger.info(
                            f"Calling Claude Haiku for context generation: {os.path.basename(file_path)}"
                        )

                        # Generate context using the modern Claude client
                        cookie = os.getenv("CLAUDE_SESSION_COOKIE", "")
                        context = generate_claude_context(
                            cookie=cookie,
                            prompt=full_prompt,
                            system_prompt=CONTEXT_SYSTEM_PROMPT,
                        )

                        # Log success
                        context_size = len(context)
                        logger.info(
                            f"Generated context of {context_size} chars for {os.path.basename(file_path)}"
                        )

                        # Save the context response for debugging
                        context_response_data = {
                            "file": os.path.basename(file_path),
                            "request_type": "context_generation",
                            "prompt": full_prompt,
                            "response": context,
                        }
                        self._save_api_response_to_log(context_response_data)

                    except Exception as e:
                        logger.error(f"Error generating context: {str(e)}")
                        context = ""

                # Now enhance the content with the context
                logger.info(f"Enhancing content for {os.path.basename(file_path)}...")

                # Generate enhanced content using Claude client
                try:
                    cookie = os.getenv("CLAUDE_SESSION_COOKIE", "")
                    enhanced_content = send_claude_edit_request(
                        cookie=cookie,
                        markdown_text=file_content,
                        instructions=prompt,
                        context=context,
                    )
                    if enhanced_content.strip() == file_content.strip():
                        raise RuntimeError(
                            "No edits applied \u2013 file left unchanged"
                        )
                except (ValueError, RuntimeError) as e:
                    error_msg = (
                        f"Error processing {os.path.basename(file_path)}: {str(e)}"
                    )
                    logger.error(error_msg)
                    self.batch_results[file_path] = "failed"
                    failed_files += 1
                    self.parent.after(
                        0,
                        lambda msg=error_msg: messagebox.showerror(
                            "Batch Processing Error", msg
                        ),
                    )
                    continue

                # Log edit response for debugging
                edit_response_data = {
                    "file": os.path.basename(file_path),
                    "request_type": "edit_markdown",
                    "markdown_text": file_content,
                    "instructions": prompt,
                    "context": context,
                    "response": enhanced_content,
                }
                self._save_api_response_to_log(edit_response_data)

                # Save the enhanced content
                if enhanced_content:
                    # Create backup file
                    from showup_core.file_utils import create_timestamped_backup

                    create_timestamped_backup(file_path)

                    # Save the enhanced content over the original file
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(enhanced_content)

                    processed_files += 1
                    logger.info(f"Successfully processed {file_path}")

            except Exception as e:
                error_msg = f"Error processing {os.path.basename(file_path)}: {str(e)}"
                logger.error(error_msg)
                self.batch_results[file_path] = "failed"
                failed_files += 1
                self.parent.after(
                    0,
                    lambda msg=error_msg: messagebox.showerror(
                        "Batch Processing Error", msg
                    ),
                )

        # Update UI when done
        elapsed_time = time.time() - start_time
        logger.info(
            f"Batch processing completed. Processed {processed_files} of {total_files} files in {elapsed_time:.2f}s. Failed: {failed_files}"
        )
        self.parent.after(
            0,
            lambda: self._update_batch_completed(
                processed_files,
                total_files,
                failed_files,
            ),
        )

    def _update_batch_completed(self, processed, total, failed=0):
        """Update UI when batch processing is completed."""
        status_message = (
            f"Batch processing completed: {processed} of {total} files processed"
        )
        if failed:
            status_message += f" \u2013 {failed} failed"
            self.status_label.config(foreground="red")
        else:
            self.status_label.config(foreground="black")
        self.status_var.set(status_message)
        self.progress_var.set(100)  # Set to 100% even if some failed
        self.process_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.processing_batch = False

    def _update_batch_cancelled(self, processed, total):
        """Update UI when batch processing is cancelled."""
        self.status_var.set(
            f"Batch processing cancelled: {processed} of {total} files processed"
        )
        self.process_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.processing_batch = False

    def get_batch_files(self):
        """Return the list of files currently in the batch."""
        return [
            self.batch_files_listbox.get(i)
            for i in range(self.batch_files_listbox.size())
        ]

    def _show_current_prompt(self):
        """Show the current prompt being used for batch editing."""
        if (
            not hasattr(self.parent, "prompt_manager")
            or not self.parent.prompt_manager.selected_prompt
        ):
            messagebox.showinfo(
                "No Prompt Selected", "Please select a prompt in the Prompt Config tab."
            )
            return

        # Show the prompt dialog using the prompt manager's function
        self.parent.prompt_manager.show_full_prompt_dialog()

    def clear_batch(self):
        """Clear the batch files list."""
        self.batch_files = []
        self.batch_files_listbox.delete(0, tk.END)
        self.status_var.set("Ready")
        self.progress_var.set(0)

    def select_files_for_batch(self):
        """Select files manually for batch processing."""
        file_paths = filedialog.askopenfilenames(
            title="Select Files for Batch Processing",
            filetypes=[
                ("Markdown Files", "*.md"),
                ("Text Files", "*.txt"),
                ("All Files", "*.*"),
            ],
        )

        if file_paths:
            # Convert to list and store
            file_paths = list(file_paths)
            self.prepare_batch_edit(file_paths)

            # Log selected files
            logger.info(f"Selected {len(file_paths)} files for batch processing")

    def select_directory_for_batch(self):
        """Select a directory and add all files with the specified extensions."""
        extensions = (".md", ".txt", ".markdown")  # Extensions to filter

        # Show directory selection dialog
        directory = filedialog.askdirectory()
        if not directory:
            return  # User cancelled

        # Find all files with the specified extensions
        files_to_add = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(extensions):
                    full_path = os.path.join(root, file)
                    files_to_add.append(full_path)

        # Add files to the batch
        if files_to_add:
            count_before = self.batch_files_listbox.size()

            for file_path in files_to_add:
                if file_path not in self.get_batch_files():
                    self.batch_files_listbox.insert(tk.END, file_path)

            count_after = self.batch_files_listbox.size()
            added = count_after - count_before

            # Update status
            if added > 0:
                self.status_var.set(f"Added {added} files from directory")
                logger.info(f"Added {added} files from directory {directory}")
            else:
                self.status_var.set("No new files added (already in batch)")
        else:
            messagebox.showinfo(
                "No Files",
                f"No files with extensions {', '.join(extensions)} found in the selected directory.",
            )
            self.status_var.set("No suitable files found in directory")

    def _save_api_response_to_log(self, response_data):
        """Save API response to a JSON file in the logs folder.

        Args:
            response_data (dict): Dictionary containing the response data to save
        """
        try:
            # Ensure logs directory exists
            logs_dir = os.path.join(
                str(get_project_root()), "showup-editor-ui", "logs", "api_responses"
            )
            os.makedirs(logs_dir, exist_ok=True)

            # Create filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            filename = f"claude_api_{response_data['request_type']}_{timestamp}.json"
            filepath = os.path.join(logs_dir, filename)

            # Write response to file
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(response_data, f, indent=2)

            logger.info(
                f"Saved {response_data['request_type']} API response to {filename}"
            )

        except Exception as e:
            logger.error(f"Error saving API response to log: {str(e)}")
