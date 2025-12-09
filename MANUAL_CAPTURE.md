# Manual Dynamic Site Capture

This guide explains how to use the "Manual Capture" mode to grab complex, dynamic websites (like Udemy, YouTube, etc.) using your own local browser (Firefox/Chrome).

## Prerequisites

1.  **Mitmproxy**: Must be installed in your environment.
    ```bash
    pip install mitmproxy
    ```

## Step 1: Start the Capture Proxy

Run the manual capture script in your terminal:

```bash
cd "/home/codespace/Downloads/src grabber"
./manual_capture.sh
```

This will start a proxy server on port **8080** and wait for you to browse.

## Step 2: Connect Your Browser

Since the proxy is running in a remote Codespace (or container), you need to tunnel the traffic from your local machine to it.

### A. SSH Tunnel (Recommended)
Open a terminal **on your local computer** (not the codespace terminal) and run:

```bash
# Replace <codespace-host> with your specific connection string
# Check 'Ports' tab in VS Code to see forwarded ports or just rely on port 8080 being forwarded.
# If using VS Code Desktop, port 8080 is often automatically forwarded to localhost:8080.
```

If you are using VS Code Port Forwarding, simply ensure Port **8080** is "Private" (or Public) and forwarded to your local machine.

### B. Configure Browser Proxy
In your local Firefox (or Chrome):
1.  Go to **Settings** > **Network Settings**.
2.  Select **Manual proxy configuration**.
3.  HTTP Proxy: `127.0.0.1`
4.  Port: `8080`
5.  Check "Use this proxy provider for HTTPS".

## Step 3: Install Certificate (HTTPS Support)
To decrypt and capture HTTPS traffic (which is 99% of the web), you need to trust the mitmproxy certificate.

1.  With the proxy configured, visit [http://mitm.it](http://mitm.it) in your browser.
2.  Click the matching icon (Apple/Windows/Other) to download the certificate.
3.  **Install/Trust it**:
    *   **Firefox**: Settings > Privacy > Certificates > View Certificates > Authorities > Import... (Select the file, check "Trust for websites").
    *   **Chrome/System**: Double click and add to "Trusted Root Certification Authorities".

## Step 4: Browse and Capture
1.  Navigate to the target site (e.g., `https://www.udemy.com`).
2.  **Interact** with the page:
    *   Scroll down to load lazy images.
    *   Click buttons to open modals.
    *   Play videos briefly (if you want to capture media requests).
3.  Everything you see is being recorded.

## Step 5: Save and Extract
1.  Go back to your terminal running `./manual_capture.sh`.
2.  Press **ENTER**.
3.  The script will:
    *   Stop the proxy.
    *   Save the recording to `manual_captures/capture_....har`.
    *   Automatically run `extract_har.py` to save files into the `src/` directory.

## Step 6: View Offline Site
Your downloaded files are in `src/`. Open `src/www.udemy.com/index.html` (or similar) to view.
