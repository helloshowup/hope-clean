import unittest
import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

os.environ['KIVY_NO_ARGS'] = '1'

from main import WorkflowApp

class TestWorkflowApp(unittest.TestCase):
    def setUp(self):
        self.app = WorkflowApp()
        self.root_widget = self.app.build()

    def test_build_has_inputs(self):
        self.assertIsNotNone(self.app.csv_path_input)
        self.assertIsNotNone(self.app.handbook_path_input)
        self.assertIsNotNone(self.app.course_name_input)
        self.assertIsNotNone(self.app.learner_profile_input)
        self.assertIsNotNone(self.app.start_button)

    def test_start_workflow_invalid_csv(self):
        self.app.csv_path_input.text = 'nonexistent.csv'
        self.app.start_workflow(None)
        self.assertIn('Error', self.app.status_message)
        self.assertFalse(self.app.workflow_running)

    def test_progress_queue_updates(self):
        self.app.progress_queue.put(25)
        self.app.check_progress_queue(0)
        self.assertEqual(self.app.progress_value, 25)
        self.assertIn('25%', self.app.status_message)

if __name__ == '__main__':
    unittest.main()
