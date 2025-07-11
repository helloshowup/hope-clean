import unittest
import importlib
import sys
import os
import types

# Setup paths similar to application
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
paths = [root_dir, os.path.join(root_dir, 'showup_tools')]
for p in paths:
    if p not in sys.path:
        sys.path.insert(0, p)

# Provide stub for dotenv if missing
if 'dotenv' not in sys.modules:
    sys.modules['dotenv'] = types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None)

class TestClaudeModules(unittest.TestCase):
    def test_batch_processor_import(self):
        importlib.import_module('showup_editor_ui.claude_panel.batch_processor')

    def test_content_enhancer_import(self):
        importlib.import_module('showup_editor_ui.claude_panel.content_enhancer')

if __name__ == '__main__':
    unittest.main()
