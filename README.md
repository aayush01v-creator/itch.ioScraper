# Unity WebGL Game Capture Tool

## Overview
This toolset provides a robust solution for capturing Unity WebGL games (specifically from Itch.io) for offline play. It handles common challenges like cross-origin `iframe` embedding, dynamic asset loading, and large binary file (WASM/Data) retrieval.

## Key Features
*   **Smart Capture (`better_capture.py`):**
    *   **Iframe Detection:** Automatically finds game iframes using both DOM structure and `data-iframe` attributes.
    *   **Direct Navigation:** Navigates the browser directly to the game frame to ensure strict asset capture.
    *   **Manual Binary Recovery:** Automatically detects and downloads critical Unity files (`.wasm`, `.data`) via `curl` if they are missed by the standard HAR recording (common with large files).
*   **Universal Extraction (`extract_har.py`):**
    *   Extracts all assets from the HAR recording.
*   **Intelligent Organization (`organize.py`):
    *   **Filename Fixing:** Automatically decodes URL-encoded filenames (e.g., `New%20folder.data` -> `New folder.data`) which causes 404 errors on local servers.
    *   **Merge & Build:** Consolidates extracted files and manually downloaded binaries into a clean, ready-to-run `organized_src/` directory.

## Quick Start

### 1. Setup
Install the necessary dependencies (Playwright):
```bash
./setup_capture.sh
```

### 2. Capture
Run the automated capture script. This will launch a headless browser, find the game, and capture the source.
```bash
python3 better_capture.py "https://studiohammergames.itch.io/rogue-sergeant-the-final-operation" final_op.har
```
*Note: This script will create a `manual_downloads` folder for any large binary files it fetches directly.*

### 3. Process
Extract the HAR file:
```bash
python3 extract_har.py final_op.har
```

### 4. Build
Run the organization script to fix filenames and merge manual downloads:
```bash
python3 organize.py
```

### 5. Play Offline
Start a local server to play the game:
```bash
./start_server.sh
```
Open [http://localhost:8081/index.html](http://localhost:8081/index.html).

## File Structure
*   `better_capture.py`: Main capture script. Handles browser automation and manual curl downloads.
*   `extract_har.py`: Extracts files from the HAR recording.
*   `organize.py`: Fixes filenames, merges `manual_downloads` into `organized_src`, and prepares the build.
*   `organized_src/`: The final, playable offline game.
    *   `offline_patch.js`: Network shim injected into `index.html`.
    *   `Build/`: Contains the Unity WASM, Data, and Framework files.
    *   `TemplateData/`: CSS and styling assets.
    *   `index.html`: The game entry point.

## Troubleshooting
*   **Game hangs on "Connecting":** The `offline_patch.js` handles most standard WebSocket connections. If it still fails, check the browser console to see if it's using a custom protocol or XHR polling.
*   **404 on `.data` or `.wasm` files:** These large files sometimes fail to capture in the HAR. `better_capture.py` attempts to download them manually to `manual_downloads`. Ensure `organize.py` is run to copy them into the build folder.
*   **"File not found" for files with spaces:** Unity often generates files like `New folder.data`. If your server sees `%20` in the request but the file has a space (or vice-versa), `organize.py` handles this renaming for you.
