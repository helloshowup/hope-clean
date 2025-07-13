import unittest
import unittest.mock
import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

os.environ['KIVY_NO_ARGS'] = '1'

import types

# Make the stub Kivy package available under the real package name
kivy_stub_path = os.path.join(os.path.dirname(__file__), 'kivy_stub')
if kivy_stub_path not in sys.path:
    sys.path.insert(0, kivy_stub_path)
import kivy_stub
sys.modules['kivy'] = kivy_stub

from main import WorkflowApp

class TestWorkflowApp(unittest.TestCase):
    def setUp(self):
        dummy_pkg = types.ModuleType('showup_tools')
        dummy_mod = types.ModuleType('showup_tools.workflow')

        def dummy_run_workflow(*a, **k):
            return {'status': 'ok'}

        dummy_run_workflow.__module__ = 'showup_tools.workflow'

        def dummy_setup_logging(*a, **k):
            return 'test.log'

        dummy_mod.run_workflow = dummy_run_workflow
        dummy_mod.setup_logging = dummy_setup_logging
        dummy_pkg.run_workflow = dummy_run_workflow
        dummy_pkg.setup_logging = dummy_setup_logging
        sys.modules['showup_tools'] = dummy_pkg
        sys.modules['showup_tools.workflow'] = dummy_mod

        self.app = WorkflowApp()
        self.root_widget = self.app.build()

    def tearDown(self):
        sys.modules.pop('showup_tools', None)
        sys.modules.pop('showup_tools.workflow', None)

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

    def test_show_file_chooser_sets_text(self):
        with unittest.mock.patch('main.filedialog.askopenfilename', return_value='/tmp/file.csv'):
            class DummyTk:
                def withdraw(self):
                    pass
                def destroy(self):
                    pass
            with unittest.mock.patch('main.Tk', return_value=DummyTk()):
                self.app.show_file_chooser(self.app.csv_path_input, 'csv')
        self.assertEqual(self.app.csv_path_input.text, '/tmp/file.csv')

    def test_start_workflow_invokes_workflow_run(self):
        self.app.csv_path_input.text = 'data/sample_input.csv'
        self.app.handbook_path_input.text = ''
        self.app.course_name_input.text = 'Course'
        self.app.learner_profile_input.text = 'Learner'

        # ensure the imported run_workflow comes from showup_tools
        import main
        self.assertEqual(main.run_workflow.__module__, 'showup_tools.workflow')

        class DummyThread:
            def __init__(self, target, args):
                self.target = target
                self.args = args
            def start(self):
                # call target synchronously for testing
                self.target(*self.args)

        with unittest.mock.patch('threading.Thread', DummyThread):
            with unittest.mock.patch.object(self.app, 'run_workflow_in_thread') as mock_run:
                self.app.start_workflow(None)
                mock_run.assert_called_once()

if __name__ == '__main__':
    unittest.main()
