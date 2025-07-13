import importlib
import sys
import shutil
import types
from pathlib import Path


def setup_temp_environment(tmp_path: Path):
    root = tmp_path / "project_root"
    tools_dir = root / "showup_tools"
    tools_dir.mkdir(parents=True)
    workflow_src = Path(__file__).resolve().parents[1] / "showup_tools" / "workflow.py"
    shutil.copy2(workflow_src, tools_dir / "workflow.py")
    (tools_dir / "__init__.py").write_text("")
    core_dir = root / "showup_core"
    core_dir.mkdir()
    (core_dir / "__init__.py").write_text("")
    (core_dir / "api_client.py").write_text("def generate_with_claude():\n    return 'ok'\n")
    return root, tools_dir


def add_stubs():
    stubs = {
        'showup_tools.csv_processor': ['read_csv', 'extract_variables', 'get_output_path'],
        'showup_tools.context_builder': ['build_context_from_adjacent_steps', 'build_context_for_comparison'],
        'showup_tools.content_generator': ['generate_three_versions_from_plan', 'extract_educational_content', 'load_content_generation_template'],
        'showup_tools.content_comparator': ['compare_and_combine'],
        'showup_tools.content_reviewer': ['review_content'],
        'showup_tools.ai_detector': ['run_ai_detection_stage'],
        'showup_tools.planning_stage': ['run_planning_stage'],
        'showup_tools.refinement_stage': ['run_refinement_stage'],
        'showup_tools.learning_sections': ['generate_lo_and_kt_from_content'],
        'showup_tools.markdown_utils': ['insert_sections_in_markdown'],
        'showup_tools.constants': ['EXCEL_CLARIFICATION'],
        'showup_tools.output_manager': ['save_as_markdown', 'create_output_directory', 'save_generation_summary', 'save_workflow_log'],
        'showup_tools.simplified_app.rag_system.token_counter': ['count_tokens'],
        'showup_tools.simplified_app.rag_system.cache_manager': ['cache'],
        'showup_tools.simplified_app.rag_system.textbook_vector_db': ['get_vector_db'],
        'showup_tools.simplified_app.rag_system.ingest_textbook': ['extract_text_from_file'],
    }
    for name, attrs in stubs.items():
        mod = types.ModuleType(name)
        for attr in attrs:
            setattr(mod, attr, lambda *a, **k: None)
        sys.modules[name] = mod
    sys.modules['showup_tools.constants'].EXCEL_CLARIFICATION = ''


def clear_stubs():
    for k in list(sys.modules.keys()):
        if k.startswith('showup_tools.') and k not in ('showup_tools.workflow',):
            sys.modules.pop(k, None)


def test_import_adds_project_root(tmp_path):
    root, tools_dir = setup_temp_environment(tmp_path)
    if str(root) in sys.path:
        sys.path.remove(str(root))
    orig_workflow = sys.modules.get('showup_tools.workflow')
    for k in list(sys.modules.keys()):
        if k.startswith('showup_tools') or k.startswith('showup_core'):
            sys.modules.pop(k, None)
    add_stubs()
    sys.path.insert(0, str(tools_dir.parent))
    try:
        wf = importlib.import_module('showup_tools.workflow')
        assert str(root) in sys.path
        assert wf.generate_with_claude() == 'ok'
    finally:
        sys.path.remove(str(tools_dir.parent))
        if str(root) in sys.path:
            sys.path.remove(str(root))
        clear_stubs()
        sys.modules.pop('showup_tools.workflow', None)
        if orig_workflow is not None:
            sys.modules['showup_tools.workflow'] = orig_workflow
        sys.modules.pop('showup_tools', None)
        sys.modules.pop('showup_core', None)
        sys.modules.pop('showup_core.api_client', None)
