import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.filechooser import FileChooserListView
from kivy.properties import ObjectProperty, StringProperty, NumericProperty
from kivy.clock import Clock
import os

kivy.require('2.0.0')

class WorkflowAppLayout(BoxLayout):
    """Main layout for the Workflow Application."""
    csv_path_input = ObjectProperty(None)
    status_label = ObjectProperty(None)
    progress_bar = ObjectProperty(None)
    output_display = ObjectProperty(None)
    file_chooser_popup = ObjectProperty(None)

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

    def show_file_chooser(self):
        """Opens a file chooser popup to select a CSV file."""
        self.file_chooser_popup = FileChooserPopup(self)
        self.add_widget(self.file_chooser_popup)

    def select_csv_file(self, path, filename):
        """Callback for file chooser to set the selected CSV path."""
        if filename and filename[0].endswith('.csv'):
            full_path = os.path.join(path, filename[0])
            self.csv_path_input.text = full_path
            self.remove_widget(self.file_chooser_popup)
            self.file_chooser_popup = None
        else:
            self.status_label.text = "Please select a .csv file."

    def cancel_file_chooser(self):
        """Cancels the file chooser popup."""
        self.remove_widget(self.file_chooser_popup)
        self.file_chooser_popup = None

    def start_workflow(self):
        """Simulates starting the content generation workflow."""
        csv_file = self.csv_path_input.text
        if not csv_file or not os.path.exists(csv_file) or not csv_file.endswith('.csv'):
            self.status_label.text = "Please load a valid CSV file first."
            return

        self.current_stage_index = 0
        self.current_progress_value = 0
        self.output_display.text = ""
        self.status_label.text = "Workflow started..."

        if self.mock_workflow_event:
            self.mock_workflow_event.cancel()

        self.mock_workflow_event = Clock.schedule_interval(self._update_mock_workflow, 1.5)

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
            "  \"video_title\": \"Photosynthesis Basics\",\n"
            "  \"target_audience\": \"Middle School Students\",\n"
            "  \"learning_objective\": \"Understand photosynthesis process\",\n"
            "  \"scenes\": [\n"
            "    {\n"
            "      \"scene_number\": 1,\n"
            "      \"scene_title\": \"Intro to Photosynthesis\",\n"
            "      \"talking_points\": [\"What is it?\", \"Why is it important?\"]\n"
            "    },\n"
            "    {\n"
            "      \"scene_number\": 2,\n"
            "      \"scene_title\": \"Ingredients & Process\",\n"
            "      \"talking_points\": [\"Sunlight, Water, CO2\", \"Chlorophyll's role\"]\n"
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

class FileChooserPopup(BoxLayout):
    """A simple file chooser popup for selecting CSV files."""
    caller = ObjectProperty(None)

    def __init__(self, caller, **kwargs):
        super().__init__(**kwargs)
        self.caller = caller

class WorkflowApp(App):
    """The main Kivy application class."""
    def build(self):
        return WorkflowAppLayout()

if __name__ == '__main__':
    WorkflowApp().run()
