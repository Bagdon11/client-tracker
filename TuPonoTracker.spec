# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['Tupono_trackerV3.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('koru_outline.png', '.'),  # Include the image file
    ],
    hiddenimports=[
        'PIL',
        'PIL._tkinter_finder',
        'matplotlib.backends.backend_tkagg',
        'pandas',
        'fpdf',
        'tkinter',
        'tkinter.ttk',
        'tkinter.messagebox',
        'tkinter.simpledialog',
        'tkinter.filedialog',
        'tempfile',
        'json',
        'os',
        'sys',
        'datetime'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
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
    icon=None,  # You can add an icon file here if you have one
)
