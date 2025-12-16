import subprocess
import sys
import os
import shutil

def install_package(package):
    print(f"[+] Installing {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def check_dependencies():
    required = ['customtkinter', 'requests', 'pyinstaller', 'Pillow']
    for package in required:
        try:
            if package == 'Pillow':
                __import__('PIL')
            else:
                __import__(package)
        except ImportError:
            print(f"[-] {package} not found. Attempting install...")
            install_package(package)

def build_exe():
    print("========================================")
    print("   Cambridge Downloader Build Script    ")
    print("========================================\n")
    
    print("1. Checking Dependencies...")
    check_dependencies()
    import customtkinter
    ctk_path = os.path.dirname(customtkinter.__file__)
    print(f"[+] CustomTkinter found at: {ctk_path}")
    print("[+] All dependencies ready.\n")
    
    print("2. Cleaning previous builds...")
    # if os.path.exists("dist"): shutil.rmtree("dist") # Locked file avoidance
    if os.path.exists("build"): shutil.rmtree("build")
    if os.path.exists("CambridgeDownloader.spec"): os.remove("CambridgeDownloader.spec")
    
    print("3. Building EXE with PyInstaller...")
    # CTK needs its json/theme files. We add them via --add-data
    # Windows format: source;dest
    add_data_arg = f"{ctk_path};customtkinter/"
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--name", "CambridgeDownloader_v2",
        "--add-data", add_data_arg,
        "--hidden-import", "PIL._tkinter_finder", 
        "cambridge_downloader_gui.py"
    ]
    
    try:
        subprocess.check_call(cmd)
        print("\n[SUCCESS] Build Complete!")
        print(f"Your app is located at: {os.path.abspath('dist/CambridgeDownloader_v2.exe')}")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Build Failed: {e}")

if __name__ == "__main__":
    build_exe()
