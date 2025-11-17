# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_all

# Collect all matplotlib and PIL data
matplotlib_datas, matplotlib_binaries, matplotlib_hiddenimports = collect_all('matplotlib')
pil_datas, pil_binaries, pil_hiddenimports = collect_all('PIL')

a = Analysis(
    ['Tupono_trackerV3.py'],
    pathex=[],
    binaries=matplotlib_binaries + pil_binaries,
    datas=[
        # Embed the logo image
        ('Tu_pono_logo.png', '.'),
        # Include matplotlib data files
        *matplotlib_datas,
        *pil_datas,
    ],
    hiddenimports=[
        'matplotlib.backends.backend_tkagg',
        'matplotlib.figure',
        'matplotlib.pyplot',
        'PIL._tkinter_finder',
        'tkinter',
        'tkinter.ttk',
        'PIL',
        'PIL.Image',
        'PIL.ImageTk',
        *matplotlib_hiddenimports,
        *pil_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'test',
        'tests',
        'testing',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='TuPonoTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='Tu_pono_icon.ico',  # Use our custom icon
    version_file=None,
)
