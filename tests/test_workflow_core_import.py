import importlib
import importlib.machinery
import importlib.util
import sys
import shutil
import types
from pathlib import Path


def setup_temp_environment(tmp_path: Path):
    root = tmp_path / "project_root"
    simplified_dir = root / "showup_tools"
    simplified_dir.mkdir(parents=True)
    (simplified_dir / "__init__.py").write_text("from .workflow import run_workflow, setup_logging\n")
    (simplified_dir / "workflow.py").write_text(
        "def run_workflow(*a, **k):\n    return {'status': 'ok'}\n"
        "def setup_logging(log_level=None):\n    return 'log.txt'\n"
    )
    return root, simplified_dir


def add_stubs():
    pass


def clear_stubs():
    pass


def test_main_adds_project_root(tmp_path):
    root, tools_dir = setup_temp_environment(tmp_path)
    main_src = Path(__file__).resolve().parents[1] / 'main.py'
    shutil.copy2(main_src, root / 'main.py')

    if str(root) in sys.path:
        sys.path.remove(str(root))

    orig_workflow = sys.modules.get('showup_tools.workflow')
    for k in list(sys.modules.keys()):
        if k.startswith('showup_tools') or k.startswith('showup_core') or k == 'main':
            sys.modules.pop(k, None)

    add_stubs()

    loader = importlib.machinery.SourceFileLoader('main', str(root / 'main.py'))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    main_module = importlib.util.module_from_spec(spec)
    loader.exec_module(main_module)

    try:
        assert str(root) in sys.path
        wf = importlib.import_module('showup_tools.workflow')
        assert wf.run_workflow() == {'status': 'ok'}
    finally:
        if str(root) in sys.path:
            sys.path.remove(str(root))
        clear_stubs()
        sys.modules.pop('showup_tools.workflow', None)
        if orig_workflow is not None:
            sys.modules['showup_tools.workflow'] = orig_workflow
        sys.modules.pop('main', None)

