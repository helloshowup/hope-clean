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
    """Install kivy stub modules into ``sys.modules``.

    ``main.py`` imports several submodules from the real ``kivy`` package. The
    test environment does not have Kivy installed, so we provide lightweight
    stand-ins located under ``tests.kivy_stub``.  This function registers the
    stub package and all required submodules under the names that ``main.py``
    expects so import statements succeed without the real dependency.
    """

    import importlib
    from pathlib import Path

    kivy_stub_path = Path(__file__).resolve().parent / 'kivy_stub'
    spec = importlib.util.spec_from_file_location(
        'kivy_stub', kivy_stub_path / '__init__.py',
        submodule_search_locations=[str(kivy_stub_path)]
    )
    kivy_stub = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kivy_stub)
    sys.modules['kivy'] = kivy_stub

    # Core subpackages/modules referenced by main.py
    mappings = {
        'kivy.app': 'kivy_stub.app',
        'kivy.clock': 'kivy_stub.clock',
        'kivy.properties': 'kivy_stub.properties',
        'kivy.uix': 'kivy_stub.uix',
        'kivy.uix.boxlayout': 'kivy_stub.uix.boxlayout',
        'kivy.uix.label': 'kivy_stub.uix.label',
        'kivy.uix.textinput': 'kivy_stub.uix.textinput',
        'kivy.uix.button': 'kivy_stub.uix.button',
        'kivy.uix.progressbar': 'kivy_stub.uix.progressbar',
        # Additional stubs that exist in the stub package
        'kivy.uix.filechooser': 'kivy_stub.uix.filechooser',
        'kivy.uix.popup': 'kivy_stub.uix.popup',
    }

    for target, source in mappings.items():
        sys.modules[target] = importlib.import_module(source)


def clear_stubs():
    """Remove any stub modules that were inserted by :func:`add_stubs`."""

    prefixes = [
        'kivy',
        'kivy.app',
        'kivy.clock',
        'kivy.properties',
        'kivy.uix',
        'kivy.uix.boxlayout',
        'kivy.uix.label',
        'kivy.uix.textinput',
        'kivy.uix.button',
        'kivy.uix.progressbar',
        'kivy.uix.filechooser',
        'kivy.uix.popup',
    ]

    for name in prefixes:
        sys.modules.pop(name, None)



def test_main_executes_with_standard_path(tmp_path):
    root, tools_dir = setup_temp_environment(tmp_path)
    main_src = Path(__file__).resolve().parents[1] / 'main.py'
    shutil.copy2(main_src, root / 'main.py')

    orig_workflow = sys.modules.get('showup_tools.workflow')
    for k in list(sys.modules.keys()):
        if k.startswith('showup_tools') or k.startswith('showup_core') or k == 'main':
            sys.modules.pop(k, None)

    add_stubs()

    # Load the temporary workflow package without modifying sys.path
    pkg_spec = importlib.util.spec_from_file_location(
        'showup_tools', tools_dir / '__init__.py', submodule_search_locations=[str(tools_dir)]
    )
    pkg = importlib.util.module_from_spec(pkg_spec)
    sys.modules['showup_tools'] = pkg
    pkg_spec.loader.exec_module(pkg)

    wf_spec = importlib.util.spec_from_file_location('showup_tools.workflow', tools_dir / 'workflow.py')
    wf = importlib.util.module_from_spec(wf_spec)
    sys.modules['showup_tools.workflow'] = wf
    wf_spec.loader.exec_module(wf)

    try:
        loader = importlib.machinery.SourceFileLoader('main', str(root / 'main.py'))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        main_module = importlib.util.module_from_spec(spec)
        loader.exec_module(main_module)

        wf = importlib.import_module('showup_tools.workflow')
        assert wf.run_workflow() == {'status': 'ok'}
    finally:
        clear_stubs()
        sys.modules.pop('showup_tools.workflow', None)
        if orig_workflow is not None:
            sys.modules['showup_tools.workflow'] = orig_workflow
        sys.modules.pop('main', None)

