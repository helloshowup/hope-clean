import unittest
import os
import sys
from unittest.mock import patch

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

os.environ['KIVY_NO_ARGS'] = '1'

from main import WorkflowApp

class TestWorkflowApp(unittest.TestCase):
    def test_build_loads_kv(self):
        app = WorkflowApp()
        root_widget = app.build()
        self.assertIsNotNone(root_widget.csv_path_input)
        self.assertIsNotNone(root_widget.handbook_checkbox)
        self.assertIsNotNone(root_widget.handbook_path_input)
        self.assertIsNotNone(root_widget.output_dir_input)
        self.assertIsNotNone(root_widget.save_to_input)
        self.assertIsNotNone(root_widget.learner_profile_preview)

    def test_select_csv_updates_profile(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, "sample.csv")
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write("learner_profile\nProfile text")
            app = WorkflowApp()
            root_widget = app.build()
            root_widget.select_csv_file(tmpdir, ["sample.csv"])
            self.assertEqual(root_widget.learner_profile_preview.text, "Profile text")

    def test_file_chooser_updates_csv_path(self):
        app = WorkflowApp()
        root_widget = app.build()
        with patch('tkinter.filedialog.askopenfilename', return_value='/tmp/test.csv'):
            root_widget.show_file_chooser()
        self.assertEqual(root_widget.csv_path_input.text, '/tmp/test.csv')

    def test_handbook_selection_updates_config(self):
        app = WorkflowApp()
        root_widget = app.build()
        root_widget.handbook_checkbox.active = True
        root_widget.select_handbook_file('/tmp', ['handbook.md'])
        self.assertEqual(root_widget.config.get('reference_handbook_path'), '/tmp/handbook.md')
        self.assertTrue(root_widget.config.get('use_reference_handbook'))

    def test_update_handbook_progress(self):
        app = WorkflowApp()
        root_widget = app.build()
        root_widget.update_handbook_progress('Loading', 50)
        from kivy.clock import Clock
        Clock.tick()
        self.assertEqual(root_widget.status_label.text, 'Processing Handbook: Loading')
        self.assertEqual(root_widget.progress_bar.value, 50)

if __name__ == '__main__':
    unittest.main()
