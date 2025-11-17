"""
Build script to create executable for Tupono_trackerV3.py
"""
import os
import sys
import subprocess
import shutil

def install_pyinstaller():
    """Install PyInstaller if not available"""
    try:
        import PyInstaller
        print("PyInstaller is already installed")
        return True
    except ImportError:
        print("Installing PyInstaller...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("PyInstaller installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Failed to install PyInstaller: {e}")
            return False

def create_spec_file():
    """Create a custom spec file for the executable"""
    spec_content = """# -*- mode: python ; coding: utf-8 -*-

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
"""
    
    with open('TuPonoTracker.spec', 'w') as f:
        f.write(spec_content)
    print("Spec file created: TuPonoTracker.spec")

def build_executable():
    """Build the executable using PyInstaller"""
    if not install_pyinstaller():
        return False
    
    print("Creating spec file...")
    create_spec_file()
    
    print("Building executable...")
    try:
        # Use the spec file to build
        subprocess.check_call([
            sys.executable, "-m", "PyInstaller", 
            "--clean", 
            "TuPonoTracker.spec"
        ])
        print("Executable built successfully!")
        
        # Check if executable was created
        exe_path = os.path.join("dist", "TuPonoTracker.exe")
        if os.path.exists(exe_path):
            print(f"Executable created at: {exe_path}")
            print(f"File size: {os.path.getsize(exe_path) / (1024*1024):.2f} MB")
            return True
        else:
            print("Executable not found in expected location")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"Failed to build executable: {e}")
        return False

def check_dependencies():
    """Check if all required dependencies are installed"""
    required_packages = [
        'tkinter', 'matplotlib', 'PIL', 'pandas', 'fpdf2'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'PIL':
                import PIL
            elif package == 'tkinter':
                import tkinter
            elif package == 'fpdf2':
                import fpdf
            else:
                __import__(package)
            print(f"✓ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package} is missing")
    
    return missing_packages

def install_missing_packages(packages):
    """Install missing packages"""
    if not packages:
        return True
    
    print(f"Installing missing packages: {', '.join(packages)}")
    
    # Map package names to pip install names
    pip_names = {
        'PIL': 'Pillow',
        'fpdf2': 'fpdf2'
    }
    
    for package in packages:
        pip_name = pip_names.get(package, package)
        if package == 'tkinter':
            print("tkinter should be included with Python. If it's missing, you may need to reinstall Python with tkinter support.")
            continue
            
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
            print(f"✓ Installed {pip_name}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install {pip_name}: {e}")
            return False
    
    return True

if __name__ == "__main__":
    print("=" * 50)
    print("Tu Pono Tracker - Executable Builder")
    print("=" * 50)
    
    # Change to the directory containing the Python file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"Working directory: {os.getcwd()}")
    
    # Check dependencies
    print("\nChecking dependencies...")
    missing = check_dependencies()
    
    if missing:
        print(f"\nMissing packages detected: {missing}")
        if input("Install missing packages? (y/n): ").lower().strip() == 'y':
            if not install_missing_packages(missing):
                print("Failed to install some packages. Exiting.")
                sys.exit(1)
        else:
            print("Cannot proceed without required packages. Exiting.")
            sys.exit(1)
    
    print("\nAll dependencies are available!")
    
    # Build executable
    print("\nBuilding executable...")
    if build_executable():
        print("\n" + "=" * 50)
        print("SUCCESS! Executable created successfully!")
        print("You can find the executable in the 'dist' folder.")
        print("The executable is standalone and can be run on Windows machines without Python installed.")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("FAILED! Could not create executable.")
        print("Check the error messages above for details.")
        print("=" * 50)
    
    input("\nPress Enter to exit...")