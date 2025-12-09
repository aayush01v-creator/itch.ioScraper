import os
import subprocess
import sys
import shutil

HAR_FILE = "new_capture.har"
EXTRACT_SCRIPT = "extract_har.py"
FETCH_SCRIPT = "fetch_assets.py"
ORGANIZED_DIR = "organized_src"
INDEX_HTML = os.path.join(ORGANIZED_DIR, "index.html")
SHIM_FILE = "api_shim.js"

def run_command(cmd):
    print(f"Running: {cmd}")
    try:
        subprocess.check_call(cmd, shell=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running {cmd}: {e}")
        sys.exit(1)

def main():
    if not os.path.exists(HAR_FILE):
        print(f"Error: {HAR_FILE} not found. Run better_capture.py first.")
        sys.exit(1)

    print("=== Step 1: Extracting HAR ===")
    run_command(f"python3 {EXTRACT_SCRIPT} {HAR_FILE}")

    print("=== Step 2: Running Organization Script ===")
    # organize.py handles file sync, asset fetching, and API shim generation
    if os.path.exists("organize.py"):
        run_command("python3 organize.py")
    else:
        print("Error: organize.py not found!")
        sys.exit(1)

    print("=== Processing Complete ===")
    print(f"Open http://localhost:8081/index.html to view.")

if __name__ == "__main__":
    main()
