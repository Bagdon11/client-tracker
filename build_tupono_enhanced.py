#!/usr/bin/env python3
"""
Enhanced build script for TuPono Tracker with icon and embedded resources
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_requirements():
    """Check if PyInstaller is installed"""
    try:
        import PyInstaller
        print("✓ PyInstaller is available")
        return True
    except ImportError:
        print("⚠ PyInstaller not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("✓ PyInstaller installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("✗ Failed to install PyInstaller")
            return False

def clean_build_dirs():
    """Clean previous build directories"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"✓ Cleaned {dir_name} directory")

def create_spec_file():
    """Create enhanced PyInstaller spec file with icon and resources"""
    
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

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
'''
    
    with open('TuPonoTracker_enhanced.spec', 'w') as f:
        f.write(spec_content)
    
    print("✓ Enhanced spec file created")

def build_executable():
    """Build the executable using PyInstaller"""
    
    print("🔨 Building TuPono Tracker executable...")
    
    try:
        # Build using the spec file
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm", 
            "TuPonoTracker_enhanced.spec"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Build completed successfully!")
            
            # Check if executable was created
            exe_path = Path("dist") / "TuPonoTracker.exe"
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"✓ Executable created: {exe_path}")
                print(f"✓ File size: {size_mb:.1f} MB")
                print(f"✓ Icon embedded: Tu_pono_icon.ico")
                print(f"✓ Logo embedded: Tu_pono_logo.png")
                return True
            else:
                print("✗ Executable not found in dist folder")
                return False
        else:
            print("✗ Build failed!")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"✗ Build error: {e}")
        return False

def create_readme():
    """Create README for the executable"""
    
    readme_content = """# TuPono Tracker - Executable Version

## About
This is the compiled executable version of the TuPono Tracker application.

## Features
- ✅ Professional UI with Tu Pono branding
- ✅ Animated splash screen with logo
- ✅ 4-tab interface (Participants, Progress, Reports, Data)
- ✅ Enhanced progress visualization with weekly tracking
- ✅ PDF report generation
- ✅ Custom Tu Pono icon
- ✅ All resources embedded (no external files needed)

## Running the Application
Simply double-click `TuPonoTracker.exe` to run the application.

## File Information
- The executable includes all necessary dependencies
- Logo and images are embedded within the executable
- No additional installation required
- Data is saved to `participants.json` in the same directory

## System Requirements
- Windows 7 or later
- No Python installation required
- Approximately 100MB disk space

## Version
Built with enhanced UI and Tu Pono branding
Date: October 2025
"""
    
    with open('dist/README_TuPonoTracker.txt', 'w') as f:
        f.write(readme_content)
    
    print("✓ README created in dist folder")

def main():
    """Main build process"""
    
    print("🚀 TuPono Tracker - Enhanced Build Process")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        return False
    
    # Verify required files exist
    required_files = ['Tupono_trackerV3.py', 'Tu_pono_logo.png', 'Tu_pono_icon.ico']
    for file in required_files:
        if not os.path.exists(file):
            print(f"✗ Required file missing: {file}")
            return False
        else:
            print(f"✓ Found: {file}")
    
    # Clean previous builds
    clean_build_dirs()
    
    # Create spec file
    create_spec_file()
    
    # Build executable
    if build_executable():
        create_readme()
        print("\\n🎉 Build completed successfully!")
        print("📁 Executable location: dist/TuPonoTracker.exe")
        print("📋 README: dist/README_TuPonoTracker.txt")
        return True
    else:
        print("\\n💥 Build failed!")
        return False

if __name__ == "__main__":
    success = main()
    input("\\nPress Enter to exit...")
    sys.exit(0 if success else 1)