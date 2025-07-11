#!/usr/bin/env python3
"""
Correct the previous patch:
    from showup_core.core.<mod> -> from showup_core.<mod>
    import showup_core.core as core -> import showup_core as core
"""
from pathlib import Path
import re, shutil, sys

ROOT = Path(__file__).resolve().parent
FROM_BAD  = re.compile(r'\bfrom\s+showup_core\.core\.')      # bad form
IMPORT_BAD = re.compile(r'\bimport\s+showup_core\.core\s+as\s+core\b')

def fix(path: Path) -> None:
    original = path.read_text(encoding="utf-8")
    patched  = IMPORT_BAD.sub('import showup_core as core',
               FROM_BAD  .sub('from showup_core.', original))
    if patched != original:
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak2"))
        path.write_text(patched, encoding="utf-8")
        print(f'Fixed: {path.relative_to(ROOT)}', file=sys.stderr)

for py in ROOT.rglob('*.py'):
    if py.name.startswith('fix_core_imports'):          # skip the patchers
        continue
    fix(py)
