import os
import sys
import subprocess
import shutil
import re

def get_current_version_string():
    """Retrieves the dynamic version string."""
    # We can import the module directly to use its logic
    # But we need to ensure we don't pick up a frozen state
    import flight_manager.version as v
    # Reload in case it was imported before
    import importlib
    importlib.reload(v)
    return v.__version__

def build():
    # 1. Get the current dynamic version
    version = get_current_version_string()
    print(f"Building version: {version}")

    version_file = os.path.join("flight_manager", "version.py")
    
    # Read original content
    with open(version_file, "r", encoding="utf-8") as f:
        original_content = f.read()

    try:
        # 2. Hardcode the version in version.py
        new_content = re.sub(
            r'__version__ = .*', 
            f'__version__ = "{version}"', 
            original_content
        )
        
        with open(version_file, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        # 3. Run PyInstaller
        # If a name is passed as argument, use it. Otherwise use FlightManager-{version}
        target_name = sys.argv[1] if len(sys.argv) > 1 else f"FlightManager-{version}"
        
        cmd = [
            "pyinstaller",
            "--noconfirm",
            "--onefile",
            "--windowed",
            "--name", target_name,
            "--hidden-import", "babel.numbers",
            "main.py"
        ]
        
        print(f"Running: {' '.join(cmd)}")
        subprocess.check_call(cmd)
        
        print(f"Build complete. Executable: dist/{exe_name}.exe")
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
    finally:
        # 4. Revert version.py
        print("Reverting version.py...")
        with open(version_file, "w", encoding="utf-8") as f:
            f.write(original_content)

if __name__ == "__main__":
    build()
