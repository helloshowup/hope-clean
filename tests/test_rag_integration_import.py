import importlib
import os
import sys


def test_enhanced_generate_content_import():
    module = importlib.import_module('simplified_workflow.rag_system.rag_integration')
    assert hasattr(module, 'enhanced_generate_content')
