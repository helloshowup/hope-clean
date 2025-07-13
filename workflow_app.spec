# -*- mode: python ; coding: utf-8 -*-


import os
import sys

root_path = os.path.abspath(os.path.dirname(sys.argv[0] if len(sys.argv) > 0 else '.'))

a = Analysis(
    ['main.py'],
    pathex=[root_path, os.path.join(root_path, 'showup_tools'), os.path.join(root_path, 'showup_core')],
    binaries=[],
    datas=[
        ('workflow_app.kv', '.'),
        ('data/ai_patterns.json', os.path.join('data')),
        ('data/ai_phrases.json', os.path.join('data')),
        (os.path.join('showup_tools', 'prompts', '*.txt'), os.path.join('showup_tools', 'prompts')),
        ('vector_cache', 'vector_cache'),
    ],
    hiddenimports=[
        'kivy.uix.filechooser',
        'kivy.uix.progressbar',
        'kivy.uix.scrollview',
        'kivy.clock',
        'os',
        'json',
        're',
        'asyncio',
        'openai',
        'anthropic',
        'jsonschema',
        'pydantic',
        'langchain',
        'pypdf',
        'pdfminer.six',
        'sentence_transformers',
        'faiss_cpu',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='workflow_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
