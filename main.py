import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.properties import ObjectProperty, StringProperty, NumericProperty
from kivy.clock import Clock
from kivy.lang import Builder
import os
import threading
import pandas as pd
import logging
import tkinter as tk
from tkinter import filedialog

kivy.require('2.0.0')
logger = logging.getLogger(__name__)

class WorkflowAppLayout(BoxLayout):
    """Main layout for the Workflow Application."""
    csv_path_input = ObjectProperty(None)
    handbook_checkbox = ObjectProperty(None)
    handbook_path_input = ObjectProperty(None)
    output_dir_input = ObjectProperty(None)
    save_to_input = ObjectProperty(None)
    learner_profile_preview = ObjectProperty(None)
    status_label = ObjectProperty(None)
    progress_bar = ObjectProperty(None)
    output_display = ObjectProperty(None)
    config = ObjectProperty(None)

    current_stage_name = StringProperty("Idle")
    current_progress_value = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.workflow_stages = [
            "Initializing...",
            "Planning Stage...",
            "Refinement Stage...",
            "Generation Stage...",
            "Comparison & Review...",
            "AI Detection...",
            "Saving Output...",
            "Workflow Complete!",
        ]
        self.current_stage_index = 0
        self.mock_workflow_event = None
        self.config = {}

    def show_file_chooser(self):
        """Open a native dialog to select a CSV file."""
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        root.destroy()
        if file_path:
            self.csv_path_input.text = file_path
            self.load_learner_profile(file_path)
            self.status_label.text = "CSV file selected."
        else:
            self.status_label.text = "No CSV file selected."

    def show_handbook_chooser(self):
        """Open a native dialog to select the reference handbook file."""
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            title="Select Handbook File",
            filetypes=[("PDF files", "*.pdf"), ("Markdown files", "*.md"), ("All files", "*.*")],
        )
        root.destroy()
        if file_path:
            if not file_path.lower().endswith((".pdf", ".md")):
                self.status_label.text = "Unsupported file type. Please select a PDF or Markdown file."
                return
            self.handbook_path_input.text = file_path
            self.config["reference_handbook_path"] = file_path
            self.config["use_reference_handbook"] = bool(self.handbook_checkbox.active)
            self.status_label.text = "Handbook file selected."
        else:
            self.status_label.text = "No handbook file selected."

    def show_output_dir_chooser(self):
        """Open a native dialog to select the output directory."""
        root = tk.Tk()
        root.withdraw()
        directory = filedialog.askdirectory(title="Select Output Directory")
        root.destroy()
        if directory:
            self.output_dir_input.text = directory
            self.status_label.text = "Output directory selected."
        else:
            self.status_label.text = "No output directory selected."

    def show_save_to_chooser(self):
        """Open a native dialog to select directory for generated content."""
        root = tk.Tk()
        root.withdraw()
        directory = filedialog.askdirectory(title="Save Generated Content To")
        root.destroy()
        if directory:
            self.save_to_input.text = directory
            self.status_label.text = "Save directory selected."
        else:
            self.status_label.text = "No save directory selected."

    def select_csv_file(self, path, filename):
        """Set the selected CSV path. Intended for testing."""
        if filename and filename[0].endswith('.csv'):
            full_path = os.path.join(path, filename[0])
            self.csv_path_input.text = full_path
            self.load_learner_profile(full_path)
        else:
            self.status_label.text = "Please select a .csv file."

    def select_handbook_file(self, path, filename):
        """Callback to set the selected reference handbook file."""
        if filename:
            full_path = os.path.join(path, filename[0])
            if not full_path.lower().endswith(('.pdf', '.md')):
                self.status_label.text = 'Unsupported file type. Please select a PDF or Markdown file.'
                return
            self.handbook_path_input.text = full_path
            self.config['reference_handbook_path'] = full_path
            self.config['use_reference_handbook'] = bool(self.handbook_checkbox.active)
        else:
            self.status_label.text = "Please select a file."

    def update_handbook_usage(self, active):
        """Update config when handbook usage checkbox changes."""
        self.config['use_reference_handbook'] = bool(active)
        if not active:
            self.config['reference_handbook_path'] = ''


    def update_handbook_progress(self, message: str, percent: float):
        """Update status and progress bar from background handbook indexing."""
        def update(_dt):
            self.status_label.text = f"Processing Handbook: {message}"
            self.progress_bar.value = percent
            self.status_label.color = (1, 1, 1, 1)
        Clock.schedule_once(update, 0)

    def load_learner_profile(self, csv_path: str):
        """Load the learner profile from the first row of the CSV, if present."""
        try:
            df = pd.read_csv(csv_path)
        except Exception as exc:
            self.status_label.text = f"Failed to read CSV: {exc}"
            return
        if 'learner_profile' in df.columns and not df['learner_profile'].isna().all():
            profile = df['learner_profile'].dropna().iloc[0]
            self.learner_profile_preview.text = str(profile)
        else:
            self.learner_profile_preview.text = ""

    def start_workflow(self):
        """Simulates starting the content generation workflow."""
        csv_file = self.csv_path_input.text
        if not csv_file or not os.path.exists(csv_file) or not csv_file.endswith('.csv'):
            self.status_label.text = "Please load a valid CSV file first."
            return

        def begin_mock_workflow(dt=None):
            if self.mock_workflow_event:
                self.mock_workflow_event.cancel()
            self.progress_bar.value = 0
            self.status_label.text = "Workflow started..."
            self.mock_workflow_event = Clock.schedule_interval(self._update_mock_workflow, 1.5)

        def progress_callback(message, percent):
            self.update_handbook_progress(message, percent)

        def index_and_start():
            try:
                from showup_tools.simplified_app.rag_system.textbook_vector_db import get_vector_db
                from showup_tools.simplified_app.rag_system.ingest_textbook import extract_text_from_file
                import hashlib

                handbook_path = self.handbook_path_input.text
                if not handbook_path.lower().endswith(('.pdf', '.md')):
                    raise RuntimeError('Unsupported file type. Please select a PDF or Markdown file.')
                handbook_text = extract_text_from_file(handbook_path)
                if not handbook_text:
                    raise RuntimeError('Failed to read handbook text')

                textbook_id = hashlib.md5(handbook_path.encode()).hexdigest()
                db = get_vector_db()
                db.index_textbook(handbook_text, textbook_id, progress_callback=progress_callback)

                Clock.schedule_once(begin_mock_workflow, 0)
            except Exception as exc:
                logger.exception("Handbook indexing failed")
                def update(_dt):
                    self.status_label.text = f"Error: Handbook indexing failed. See logs."
                    self.status_label.color = (1, 0, 0, 1)
                Clock.schedule_once(update, 0)
            finally:
                Clock.schedule_once(lambda _dt: setattr(self.ids._start_button, 'disabled', False), 0)

        self.current_stage_index = 0
        self.current_progress_value = 0
        self.output_display.text = ""
        self.status_label.text = "Workflow started..."

        self.config = {
            "csv_path": csv_file,
            "reference_handbook_path": self.handbook_path_input.text,
            "use_reference_handbook": bool(self.handbook_checkbox.active),
            "output_dir": self.output_dir_input.text,
            "save_to": self.save_to_input.text,
            "learner_profile": self.learner_profile_preview.text,
        }

        if self.config.get("use_reference_handbook") and self.config.get("reference_handbook_path"):
            self.ids._start_button.disabled = True
            threading.Thread(target=index_and_start, daemon=True).start()
        else:
            begin_mock_workflow()

    def _update_mock_workflow(self, dt):
        """Internal method to simulate workflow progression."""
        if self.current_stage_index < len(self.workflow_stages):
            self.current_stage_name = self.workflow_stages[self.current_stage_index]
            self.current_progress_value = (self.current_stage_index + 1) / len(self.workflow_stages) * 100
            self.status_label.text = f"Status: {self.current_stage_name}"

            if self.current_stage_name == "Workflow Complete!":
                self.mock_workflow_event.cancel()
                self.output_display.text = (
                    "Workflow finished successfully!\n\n"
                    "Sample Final Content:\n\n"
                    "## The Amazing World of Photosynthesis\n"
                    "Photosynthesis is the process by which green plants and some other organisms use sunlight to synthesize foods with the help of chlorophyll. This process is vital for life on Earth as it provides the oxygen we breathe and the food we eat.\n\n"
                    "### Scene 1: Sunlight and Leaves\n"
                    "Imagine a tiny factory inside a plant leaf, working tirelessly. Sunlight, water, and carbon dioxide are the raw materials. The chlorophyll in the leaves captures the sun's energy, turning it into chemical energy.\n\n"
                    "### Scene 2: The Chemical Reaction\n"
                    "Inside the factory, water and carbon dioxide undergo a magical transformation. With the captured sunlight energy, they are converted into glucose (sugar), which is the plant's food, and oxygen, which is released into the atmosphere.\n\n"
                    "### AI Detection Flags:\n"
                    " - Pattern: 'In conclusion,', Category: 'Overly Formal Phrases', Index: 500\n"
                    " - Pattern: 'It is important to note that', Category: 'Redundancy', Index: 650"
                )
                self.view_final_content()

            self.current_stage_index += 1
        else:
            self.mock_workflow_event.cancel()

    def view_final_content(self):
        """Displays mock final content in the output area."""
        self.output_display.text = (
            "## Sample Final Content\n\n"
            "This is where the polished, reviewed content would appear.\n\n"
            "It would be the best version, potentially merged and enhanced, ready for use.\n\n"
            "**Key Learning Points:**\n"
            "- Point 1\n"
            "- Point 2\n"
            "- Point 3\n\n"
            "AI Detection Flags would also be listed here if found."
        )

    def view_initial_plan(self):
        """Displays mock initial plan JSON in the output area."""
        self.output_display.text = (
            "## Sample Initial Plan (JSON)\n\n"
            "```json\n"
            "{\n"
            "  \"content_blocks\": [\n"
            "    {\n"
            "      \"block_type\": \"lesson_metadata\",\n"
            "      \"title\": \"Photosynthesis Basics\",\n"
            "      \"module_id\": \"BIO101\"\n"
            "    },\n"
            "    {\n"
            "      \"block_type\": \"introduction\",\n"
            "      \"content_summary\": \"An overview of how plants convert sunlight into energy\"\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "```"
        )

    def view_ai_flags(self):
        """Displays mock AI detection flags in the output area."""
        self.output_display.text = (
            "## Sample AI Detection Flags\n\n"
            "This section would list any detected AI-generated patterns or phrases.\n\n"
            "**Detected Flags:**\n"
            "- **Pattern:** 'In conclusion,', **Category:** 'Overly Formal Phrases', **Index:** 123\n"
            "- **Pattern:** 'It is important to note that', **Category:** 'Redundancy', **Index:** 456\n"
            "- **Pattern:** 'As an AI language model,', **Category:** 'AI Disclosure', **Index:** 789\n"
            "- **Pattern:** 'I hope this helps!', **Category:** 'Common AI Phrase', **Index:** 900"
        )


class WorkflowApp(App):
    """The main Kivy application class."""
    def build(self):
        Builder.load_file('workflow_app.kv')
        return WorkflowAppLayout()

if __name__ == '__main__':
    WorkflowApp().run()
