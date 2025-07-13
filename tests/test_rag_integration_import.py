import importlib
import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)


def test_enhanced_generate_content_import():
    module = importlib.import_module('simplified_workflow.rag_system.rag_integration')
    assert hasattr(module, 'enhanced_generate_content')
