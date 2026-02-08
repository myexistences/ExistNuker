# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Spec File for Discord Nuker
Optimized for single-file distribution
"""

import sys
from PyInstaller.utils.hooks import collect_submodules

# Collect all hidden imports
hiddenimports = [
    'requests',
    'urllib3',
    'charset_normalizer',
    'idna',
    'certifi',
    'colorama',
    'rich',
    'rich.theme',
    'rich.console',
    'rich.style',
    'rich.panel',
    'rich.live',
    'rich.progress',
    'rich.table',
    'rich.prompt',
    'rich.cells',
    'rich._unicode_data',
    'config',
]

# Collect all rich submodules including unicode data
hiddenimports += collect_submodules('rich._unicode_data')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'test', 'unittest', 'pydoc', 'numpy', 'scipy', 'pandas', 'matplotlib'], # Exclude heavy unused modules
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Remove unnecessary binaries (optional, but keeping safe types)
a.binaries = [x for x in a.binaries if not x[0].startswith('api-ms-')]
a.binaries = [x for x in a.binaries if not x[0].startswith('ucrtbase')]

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ExistNuker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False, # Disable strip (causes errors if tool missing)
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
