import kivy
kivy.require('2.3.1')  # Ensure minimum Kivy version

import sys
import os

# --- CRITICAL FIX: Add project root to sys.path before any local imports ---
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- END OF CRITICAL FIX ---

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.properties import StringProperty, BooleanProperty, NumericProperty

import asyncio
import threading
import queue
import json
import logging
import datetime
import traceback

# Import the full workflow implementation with planning and refinement
try:
    from showup_tools.workflow import run_workflow, setup_logging
except ImportError as e:
    logging.error(f"Failed to import workflow module: {e}")
    run_workflow = None
    setup_logging = None

kivy_logger = logging.getLogger('kivy')
kivy_logger.setLevel(logging.INFO)

class WorkflowApp(App):
    status_message = StringProperty("Ready to start workflow.")
    progress_value = NumericProperty(0)
    workflow_running = BooleanProperty(False)
    output_info = StringProperty("")

    def build(self):
        self.title = "ShowUp AI Content Generation"

        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        input_grid = BoxLayout(orientation='vertical', size_hint_y=None, height=300, spacing=5)

        input_grid.add_widget(Label(text="CSV File Path:", halign='left', size_hint_x=1))
        self.csv_path_input = TextInput(text="data/sample_input.csv", multiline=False, size_hint_x=1)
        input_grid.add_widget(self.csv_path_input)
        csv_browse_button = Button(text="Browse CSV", size_hint_y=None, height=40)
        csv_browse_button.bind(on_release=lambda btn: self.show_file_chooser(self.csv_path_input, 'csv'))
        input_grid.add_widget(csv_browse_button)

        input_grid.add_widget(Label(text="Student Handbook (Optional):", halign='left', size_hint_x=1))
        self.handbook_path_input = TextInput(text="showup-library/Handbooks textbookx Guides for Enrichment/Grit for Academic Success_.md", multiline=False, size_hint_x=1)
        input_grid.add_widget(self.handbook_path_input)
        handbook_browse_button = Button(text="Browse Handbook", size_hint_y=None, height=40)
        handbook_browse_button.bind(on_release=lambda btn: self.show_file_chooser(self.handbook_path_input, 'handbook'))
        input_grid.add_widget(handbook_browse_button)

        input_grid.add_widget(Label(text="Course Name:", halign='left', size_hint_x=1))
        self.course_name_input = TextInput(text="Introduction to Academic Grit", multiline=False, size_hint_x=1)
        input_grid.add_widget(self.course_name_input)

        input_grid.add_widget(Label(text="Learner Profile:", halign='left', size_hint_x=1))
        self.learner_profile_input = TextInput(text="A high school student preparing for college.", multiline=True, size_hint_x=1)
        input_grid.add_widget(self.learner_profile_input)

        main_layout.add_widget(input_grid)

        self.start_button = Button(text="Start Workflow", size_hint_y=None, height=50)
        self.start_button.bind(on_release=self.start_workflow)
        main_layout.add_widget(self.start_button)

        self.progress_bar = ProgressBar(max=100, value=self.progress_value, size_hint_y=None, height=30)
        main_layout.add_widget(self.progress_bar)

        self.status_label = Label(text=self.status_message, size_hint_y=None, height=40, markup=True)
        main_layout.add_widget(self.status_label)

        self.output_label = Label(text=self.output_info, size_hint_y=None, height=100, markup=True)
        main_layout.add_widget(self.output_label)

        self.bind(status_message=self.status_label.setter('text'))
        self.bind(progress_value=self.progress_bar.setter('value'))
        self.bind(output_info=self.output_label.setter('text'))
        self.bind(workflow_running=self.update_button_state)

        self.progress_queue = queue.Queue()
        Clock.schedule_interval(self.check_progress_queue, 0.1)

        if run_workflow is None:
            self.status_message = "[color=ff0000]ERROR: Core workflow module not loaded. Check console for details.[/color]"
            self.start_button.disabled = True

        return main_layout

    def update_button_state(self, instance, value):
        self.start_button.disabled = value or (run_workflow is None)

    def show_file_chooser(self, target_text_input, file_type):
        file_chooser = FileChooserListView(path=os.getcwd())

        def select_file(instance, selection, touch=None):
            if selection:
                target_text_input.text = selection[0]
            popup.dismiss()

        file_chooser.bind(on_submit=select_file)
        file_chooser.bind(on_select=select_file)

        popup = Popup(title=f"Select {file_type.capitalize()} File", content=file_chooser, size_hint=(0.9, 0.9))
        popup.open()

    def start_workflow(self, instance):
        if self.workflow_running:
            return
        if run_workflow is None:
            self.status_message = "[color=ff0000]Cannot start: Core workflow module failed to load.[/color]"
            return

        self.workflow_running = True
        self.status_message = "Workflow started..."
        self.progress_value = 0
        self.output_info = ""

        csv_path = self.csv_path_input.text
        handbook_path = self.handbook_path_input.text
        course_name = self.course_name_input.text
        learner_profile = self.learner_profile_input.text

        current_dir = os.path.dirname(os.path.abspath(__file__))
        abs_csv_path = os.path.join(current_dir, csv_path)
        if not os.path.exists(abs_csv_path):
            self.status_message = f"[color=ff0000]Error: CSV file not found at {abs_csv_path}[/color]"
            self.workflow_running = False
            return

        abs_handbook_path = ""
        if handbook_path:
            abs_handbook_path = os.path.join(current_dir, handbook_path)
            if not os.path.exists(abs_handbook_path):
                if os.path.exists(handbook_path):
                    abs_handbook_path = handbook_path
                else:
                    self.status_message = f"[color=ff8c00]Warning: Handbook file not found at {abs_handbook_path}. Proceeding without handbook.[/color]"
                    abs_handbook_path = ""

        ui_settings = {
            "use_reference_handbook": bool(abs_handbook_path),
            "reference_handbook_path": abs_handbook_path,
            "selected_model": "claude-3-haiku-20240307",
            "initial_generation_model": "claude-3-haiku-20240307",
            "planning_model": "claude-3-haiku-20240307",
            "refinement_model": "claude-3-haiku-20240307",
            "planning_max_tokens": 1000,
            "refinement_max_tokens": 1000,
            "planning_temperature": 0.3,
            "refinement_temperature": 0.3,
            "use_dynamic_blocks": True,
            "ai_patterns_path": "data/ai_patterns.json",
        }

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_base_dir = "output"
        run_output_dir = os.path.join(current_dir, output_base_dir, f"run_{timestamp}")
        os.makedirs(run_output_dir, exist_ok=True)

        try:
            workflow_log_file_path = setup_logging(log_level=logging.DEBUG)
        except Exception as e:
            self.status_message = f"[color=ff0000]Error setting up workflow logging: {e}[/color]"
            self.workflow_running = False
            return

        self.output_info = (
            f"[color=0000ff]Workflow Log:[/color] {workflow_log_file_path}\n"
            f"[color=0000ff]Output Directory:[/color] {os.path.abspath(run_output_dir)}"
        )
        self.status_message = "Workflow starting in background..."

        workflow_thread = threading.Thread(
            target=self.run_workflow_in_thread,
            args=(abs_csv_path, course_name, learner_profile, ui_settings, run_output_dir)
        )
        workflow_thread.daemon = True
        workflow_thread.start()

    def run_workflow_in_thread(self, csv_path, course_name, learner_profile, ui_settings, output_dir):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            workflow_summary = loop.run_until_complete(
                run_workflow(
                    csv_path=csv_path,
                    course_name=course_name,
                    learner_profile=learner_profile,
                    ui_settings=ui_settings,
                    output_dir=output_dir,
                    progress_queue=self.progress_queue
                )
            )
            self.progress_queue.put({"final_summary": workflow_summary})
        except Exception as e:
            error_message = f"Workflow thread error: {type(e).__name__}: {e}"
            detailed_error = traceback.format_exc()
            kivy_logger.error(f"{error_message}\n{detailed_error}")
            self.progress_queue.put({"error": error_message})
        finally:
            loop.close()

    def check_progress_queue(self, dt):
        while not self.progress_queue.empty():
            item = self.progress_queue.get_nowait()
            if isinstance(item, int):
                self.progress_value = item
                self.status_message = f"Workflow progress: {item}%"
            elif isinstance(item, dict):
                if "final_summary" in item:
                    summary = item["final_summary"]
                    self.status_message = f"Workflow finished: {summary.get('status', 'unknown')}"
                    success_count = summary.get('success_count', 0)
                    error_count = summary.get('error_count', 0)
                    log_file_display = os.path.abspath(summary.get('log_file', 'N/A')) if summary.get('log_file') else 'N/A'
                    output_dir_display = os.path.abspath(summary.get('output_dir', 'N/A')) if summary.get('output_dir') else 'N/A'
                    self.output_info = (
                        f"[color=0000ff]Workflow Log:[/color] {log_file_display}\n"
                        f"[color=0000ff]Output Directory:[/color] {output_dir_display}\n"
                        f"[color=008000]Successful:[/color] {success_count}, [color=ff0000]Errors:[/color] {error_count}"
                    )
                    self.workflow_running = False
                elif "error" in item:
                    self.status_message = f"[color=ff0000]Workflow Error: {item['error']}[/color]"
                    self.workflow_running = False

if __name__ == '__main__':
    WorkflowApp().run()
