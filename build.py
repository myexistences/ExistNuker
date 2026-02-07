#!/usr/bin/env python3
"""
Build Script for Discord Nuker
Creates optimized, compressed self-contained executable

Usage:
    python build.py          - Standard build with UPX (if available)
    python build.py --no-upx - Build without UPX compression
    python build.py --clean  - Clean build artifacts before building
"""

import subprocess
import sys
import os
import shutil
from pathlib import Path

# Build configuration
APP_NAME = "Nuker"
MAIN_SCRIPT = "main.py"
SPEC_FILE = "build.spec"


def get_script_dir():
    """Get directory containing this script"""
    return Path(__file__).parent.resolve()


def check_dependencies():
    """Check if required packages are installed"""
    print("Checking dependencies...")
    
    required = ['pyinstaller', 'requests', 'colorama']
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg.replace('-', '_'))
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        subprocess.run([sys.executable, '-m', 'pip', 'install'] + missing, check=True)
    
    print("All dependencies ready!")


def check_upx():
    """Check if UPX is available for compression"""
    try:
        result = subprocess.run(['upx', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            print(f"UPX found: {version}")
            return True
    except FileNotFoundError:
        pass
    
    print("UPX not found - EXE will be larger without it")
    print("Download UPX from: https://github.com/upx/upx/releases")
    return False


def clean_build():
    """Clean previous build artifacts"""
    script_dir = get_script_dir()
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    files_to_clean = [f'{APP_NAME}.spec']
    
    for d in dirs_to_clean:
        path = script_dir / d
        if path.exists():
            print(f"Removing {d}/")
            shutil.rmtree(path)
    
    for f in files_to_clean:
        path = script_dir / f
        if path.exists():
            print(f"Removing {f}")
            path.unlink()
    
    print("Clean complete!")


def build(use_upx=True, use_spec=True):
    """Build the executable"""
    script_dir = get_script_dir()
    os.chdir(script_dir)
    
    print(f"\n{'='*50}")
    print(f"Building {APP_NAME}")
    print(f"{'='*50}\n")
    
    # Check for UPX
    upx_available = check_upx()
    
    if use_spec and (script_dir / SPEC_FILE).exists():
        # Use spec file - UPX is controlled in the spec itself
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--clean',
            '--noconfirm',
            SPEC_FILE
        ]
    else:
        # Build from scratch
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--onefile',
            '--console',
            '--clean',
            '--noconfirm',
            '--strip',
            f'--name={APP_NAME}',
            # Hidden imports
            '--hidden-import=requests',
            '--hidden-import=urllib3',
            '--hidden-import=colorama',
            '--hidden-import=charset_normalizer',
            '--hidden-import=certifi',
            '--hidden-import=idna',
            # Excludes to reduce size
            '--exclude-module=tkinter',
            '--exclude-module=unittest',
            '--exclude-module=pydoc',
            '--exclude-module=test',
            '--exclude-module=setuptools',
            '--exclude-module=pip',
            MAIN_SCRIPT
        ]
        
        if use_upx and upx_available:
            cmd.insert(-1, '--upx-dir=.')
        else:
            cmd.insert(-1, '--noupx')
    
    print(f"Running: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        exe_path = script_dir / 'dist' / f'{APP_NAME}.exe'
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"\n{'='*50}")
            print(f"BUILD SUCCESSFUL!")
            print(f"{'='*50}")
            print(f"Output: {exe_path}")
            print(f"Size:   {size_mb:.2f} MB")
            if not upx_available:
                print(f"\nTip: Install UPX to reduce size by ~50%")
            print(f"{'='*50}\n")
        else:
            print("\nBuild completed but EXE not found at expected location")
    else:
        print("\nBuild failed!")
        sys.exit(1)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Build Discord Nuker executable')
    parser.add_argument('--no-upx', action='store_true', help='Disable UPX compression')
    parser.add_argument('--clean', action='store_true', help='Clean build artifacts before building')
    parser.add_argument('--no-spec', action='store_true', help='Ignore spec file, use command line args')
    args = parser.parse_args()
    
    print(f"\n{'='*50}")
    print("Discord Nuker Build Script")
    print(f"{'='*50}\n")
    
    # Clean if requested
    if args.clean:
        clean_build()
    
    # Check dependencies
    check_dependencies()
    
    # Build
    build(use_upx=not args.no_upx, use_spec=not args.no_spec)


if __name__ == '__main__':
    main()
