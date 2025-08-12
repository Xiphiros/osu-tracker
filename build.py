import PyInstaller.__main__
import os
import shutil

APP_NAME = "OsuTracker"
SCRIPT_FILE = os.path.join('backend', 'app.py')

def build():
    """Generates the executable using PyInstaller."""
    print("Starting build process...")
    
    # This command bundles the backend script, adds the entire frontend 
    # directory, and creates a single, windowed executable.
    pyinstaller_args = [
        f'--name={APP_NAME}',
        '--onefile',
        '--windowed',
        f'--add-data=frontend{os.pathsep}frontend',
        '--noconfirm',
        SCRIPT_FILE,
    ]

    PyInstaller.__main__.run(pyinstaller_args)

    print(f"\nBuild completed successfully.")
    print(f"Executable is located in: {os.path.join(os.getcwd(), 'dist')}")

    # Clean up build artifacts that are no longer needed
    print("Cleaning up build files...")
    if os.path.exists('build'):
        shutil.rmtree('build')
    spec_file = f'{APP_NAME}.spec'
    if os.path.exists(spec_file):
        os.remove(spec_file)
    print("Cleanup complete.")

if __name__ == '__main__':
    build()