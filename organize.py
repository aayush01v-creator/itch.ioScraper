import os
import shutil
import glob

ORGANIZED_DIR = "organized_src"
SRC_ROOT = "src"

def main():
    print("=== Organizing Unity WebGL Capture ===")
    
    if os.path.exists(ORGANIZED_DIR):
        print(f"Cleaning existing {ORGANIZED_DIR}...")
        shutil.rmtree(ORGANIZED_DIR)
    os.makedirs(ORGANIZED_DIR)

    # 1. Find the main game index.html
    # It usually lives in src/html-classic.itch.zone/html/.../index.html OR src/studiohammergames.../index.html
    # based on our extract log: src/html-classic.itch.zone/html/14978833/index.html
    
    game_root = None
    
    # Search for the index.html that looks like the game root
    print("Searching for game root...")
    for root, dirs, files in os.walk(SRC_ROOT):
        if "index.html" in files:
            # Check if this looks like the unity export root (has Build or TemplateData usually nearby)
            if "Build" in dirs or "TemplateData" in dirs:
                game_root = root
                print(f"Found game root at: {game_root}")
                break
    
    if not game_root:
        print("Warning: Could not find obvious Unity game root. Copying everything flat-ish.")
        # Fallback: just copy everything from src/html-classic.itch.zone if exists
        potential_roots = glob.glob("src/html-classic.itch.zone/html/*")
        if potential_roots:
            game_root = potential_roots[0]
            print(f"Fallback game root: {game_root}")

    if game_root:
        print(f"Copying game files from {game_root} to {ORGANIZED_DIR}...")
        shutil.copytree(game_root, ORGANIZED_DIR, dirs_exist_ok=True)
        
        # FIX: Rename files with URL encoding (e.g. %20 -> space)
        # This is needed because Python http.server unquotes requests, so it expects "New folder.js" not "New%20folder.js"
        print("Fixing URL-encoded filenames...")
        import urllib.parse
        for root, dirs, files in os.walk(ORGANIZED_DIR, topdown=False):
            # Rename files
            for name in files:
                if "%" in name:
                    new_name = urllib.parse.unquote(name)
                    if new_name != name:
                        old_path = os.path.join(root, name)
                        new_path = os.path.join(root, new_name)
                        print(f"Renaming: {name} -> {new_name}")
                        os.rename(old_path, new_path)
            # Rename dirs if needed (though topdown=False handles children first)
            for name in dirs:
                if "%" in name:
                    new_name = urllib.parse.unquote(name)
                    if new_name != name:
                        old_path = os.path.join(root, name)
                        new_path = os.path.join(root, new_name)
                        print(f"Renaming Directory: {name} -> {new_name}")
                        os.rename(old_path, new_path)
        
        # MERGE MANUAL DOWNLOADS
        # If better_capture.py fetched extra files (like .data), copy them in
        manual_dir = "manual_downloads"
        build_dir = os.path.join(ORGANIZED_DIR, "Build")
        if os.path.exists(manual_dir) and os.path.exists(build_dir):
            print(f"Merging manual downloads from {manual_dir} to {build_dir}...")
            for manual_file in os.listdir(manual_dir):
                src_file = os.path.join(manual_dir, manual_file)
                if os.path.isfile(src_file):
                    shutil.copy2(src_file, build_dir)
                    print(f" - Copied {manual_file}")

    else:
        print("CRITICAL: Could not define a source root. Check 'src' folder structure.")
        return

    # 2. Copy shared assets (UnityLoader.js logic usually requires relative paths, but we might have absolute assets)
    # The HAR extract puts things in domain folders.
    # Unity WebGL builds are usually self-contained in their specific folder (Build/TemplateData).
    # But sometimes they reference things from static.itch.io
    
    # Let's inspect if there are any other important folders we missed
    # Check for "TemplateData" in other places or common libs
    
    print("Organization complete.")
    print(f"Your game should be ready in '{ORGANIZED_DIR}'")
    
    # Create a simple python server starter
    with open("start_server.sh", "w") as f:
        f.write("#!/bin/bash\ncd organized_src\npython3 -m http.server 8081\n")
    os.chmod("start_server.sh", 0o755)
    
    # INJECT OFFLINE PATCH
    # We write the patch file here to ensure it exists after cleanup
    patch_file = os.path.join(ORGANIZED_DIR, "offline_patch.js")
    
    patch_content = """(function() {
    console.log("[OFFLINE PATCH] Initializing WebSocket & Network Shim (Echo Mode)...");
    
    const OriginalWebSocket = window.WebSocket;

    class MockWebSocket extends EventTarget {
        constructor(url, protocols) {
            super();
            console.log(`[OFFLINE PATCH] Intercepted WebSocket connection to: ${url}`);
            this.url = url;
            this.readyState = 0; // CONNECTING
            
            setTimeout(() => {
                console.log(`[OFFLINE PATCH] Simulating WebSocket Open for ${url}`);
                this.readyState = 1; // OPEN
                if (this.onopen) {
                    this.onopen({ type: 'open' });
                }
                this.dispatchEvent(new Event('open'));
            }, 100);
        }

        send(data) {
            if (data instanceof ArrayBuffer) {
                const view = new Uint8Array(data);
                console.log(`[OFFLINE PATCH] WebSocket.send received bytes:`, view);
                
                // FUZZING STRATEGY V3:
                // Error: "MagicNumber should be 0xF0 (240) or 0xF3 (243). Is: 1"
                // This means our previous attempt (starting with 1) failed the first check.
                // The client sent [243, 6, ...]. So it expects 243 back (or 240).
                // The previous error "unexpected msgType 6" means it DOESN'T want type 6 back.
                
                // Hypothesis: 
                // Byte 0: Magic Number (Keep 243 / 0xF3)
                // Byte 1: Message Type (Change 6 -> 1 for 'Connect Accept'?)
                
                setTimeout(() => {
                    const response = new Uint8Array(view); // Copy original payload
                    
                    response[0] = 243; // Magic Number (Fixes "MagicNumber should be 0xF0 or 0xF3")
                    response[1] = 1;   // Message Type (Fixes "unexpected msgType 6")
                    
                    // We keep the rest of the bytes (2..7) assuming they are session/version IDs
                    
                    console.log(`[OFFLINE PATCH] Sending response [${response[0]}, ${response[1]}, ...]:`, response);
                    
                    const event = new MessageEvent('message', {
                        data: response.buffer,
                        origin: this.url,
                        lastEventId: '',
                        source: null,
                        ports: []
                    });
                    
                    if (this.onmessage) {
                        this.onmessage(event);
                    }
                    this.dispatchEvent(event);
                }, 50);
            } else {
                 console.log(`[OFFLINE PATCH] WebSocket.send received non-binary:`, data);
            }
        }

        close() {
            console.log(`[OFFLINE PATCH] WebSocket.close called for ${this.url}`);
            this.readyState = 3; // CLOSED
            if (this.onclose) {
                this.onclose({ type: 'close', wasClean: true });
            }
            this.dispatchEvent(new Event('close'));
        }
    }

    window.WebSocket = MockWebSocket;
    
    Object.defineProperty(navigator, "onLine", {
        get: () => true
    });

    console.log("[OFFLINE PATCH] Network Shim Active (Echo Mode).");
})();"""

    with open(patch_file, "w") as f:
        f.write(patch_content)
    print("Created offline_patch.js")

    index_file = os.path.join(ORGANIZED_DIR, "index.html")
    if os.path.exists(index_file):
        print("Injecting offline_patch.js into index.html...")
        with open(index_file, "r") as f:
            html = f.read()
            
        if "offline_patch.js" not in html:
            # Inject before the first <script> or at end of <head>
            replacement = '<script src="offline_patch.js"></script>\n    <script>'
            if '<script>' in html:
                 html = html.replace('<script>', replacement, 1) # Only first occurrence
            else:
                 html = html.replace('</head>', '<script src="offline_patch.js"></script></head>')
            
            with open(index_file, "w") as f:
                f.write(html)
            print(" - Injection successful.")

    print("Run './start_server.sh' to test.")

if __name__ == "__main__":
    main()
