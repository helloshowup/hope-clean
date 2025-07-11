import importlib


def test_enhanced_generate_content_import():
    module = importlib.import_module('showup_tools.simplified_app.rag_system.rag_integration')
    assert hasattr(module, 'enhanced_generate_content')
