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

if __name__ == '__main__':
    unittest.main()
