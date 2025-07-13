import unittest
import os
import sys

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

    def test_file_chooser_uses_app_user_data_dir(self):
        app = WorkflowApp()
        root_widget = app.build()
        root_widget.show_file_chooser()
        chooser_path = root_widget.file_chooser_popup.ids.file_chooser.path
        self.assertEqual(chooser_path, app.user_data_dir)

if __name__ == '__main__':
    unittest.main()
