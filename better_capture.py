
import asyncio
import sys
import os
import time
from playwright.async_api import async_playwright

async def run(url, output_file="capture.har"):
    async with async_playwright() as p:
        # Launch Firefox
        print(f"Launching Firefox...")
        browser = await p.firefox.launch(headless=True)
        
        # Create a new context with HAR recording enabled
        # record_har_content='embed' ensures body content is saved
        context = await browser.new_context(
            record_har_path=output_file,
            record_har_content='embed', 
            ignore_https_errors=True,
            viewport={'width': 1920, 'height': 1080}
        )

        page = await context.new_page()

        # Disable cache to ensure we get fresh assets
        await page.route("**/*", lambda route: route.continue_())
        
        print(f"Navigating to {url}...")
        try:
            # Wait until network is idle (no connections for 500ms)
            await page.goto(url, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"Navigation warning (might be incomplete): {e}")

        # Unity specific wait and interaction as requested
        try:
            print("Attempting Unity interaction...")
            
            # 1. Handle "Run Game" button which is common on itch.io
            try:
                run_btn = page.locator("div.start_game_overlay, button:has-text('Run Game'), div:has-text('Run Game')").first
                if await run_btn.is_visible(timeout=5000):
                    print("Found 'Run Game' overlay/button. Clicking...")
                    await run_btn.click()
                    await page.wait_for_timeout(5000) # Wait for iframe to load/init
            except Exception as e:
                print(f"No 'Run Game' button processing needed or failed: {e}")

            # 2. Smart Capture Strategy: Find the game iframe and navigate directly to it
            print("Scanning for game iframe...")
            game_iframe_url = None
            
            # 2. Smart Capture Strategy: Find the game iframe and navigate directly to it
            print("Scanning for game iframe...")
            game_iframe_url = None
            
            # Strategy A: Check for data-iframe attribute (common in itch.io embeds)
            try:
                placeholder = await page.query_selector("div.iframe_placeholder")
                if placeholder:
                    data_iframe = await placeholder.get_attribute("data-iframe")
                    if data_iframe and "src=" in data_iframe:
                        import re
                        # Extract src="..."
                        match = re.search(r'src="([^"]+)"', data_iframe)
                        if match:
                            game_iframe_url = match.group(1).replace("&amp;", "&")
                            print(f" *** MATCH! Found game iframe src via data-iframe attribute: {game_iframe_url}")
            except Exception as e:
                print(f"Error checking data-iframe: {e}")

            # Strategy B: Fallback to DOM scan if not found
            if not game_iframe_url:
                # Wait loop for iframe URL via DOM element
                for i in range(5): 
                    await page.wait_for_timeout(2000)
                    print(f"[Debug] DOM scan for iframe (attempt {i+1}/5)...")
                    
                    iframe_element = await page.query_selector("iframe")
                    if iframe_element:
                        src = await iframe_element.get_attribute("src")
                        if src and ("itch.zone" in src or "hw-cdn" in src or "uploads.ungrounded.net" in src):
                            game_iframe_url = src
                            print(f" *** MATCH! Found game iframe src via DOM: {game_iframe_url}")
                            break
            
            if game_iframe_url:
                print(f"Navigating directly to game URL to ensure full capture: {game_iframe_url}")
                # We navigate the main page to the game URL. 
                # This ensures the HAR context captures all game assets as main-frame requests.
                await page.goto(game_iframe_url, wait_until="networkidle", timeout=60000)
                
                # Now we are on the game page directly
                print("Waiting for Unity canvas on direct page...")
                try:
                    canvas = await page.wait_for_selector('#unity-canvas, #unity-container, canvas[id*="unity"], canvas', timeout=45000)
                    print("Unity canvas found! Waiting for assets to load (WASM/Data)...")
                    await page.wait_for_timeout(10000) # Give it time to load huge WASM files
                    
                    print("Sending interaction 'W'...")
                    await canvas.click()
                    await page.keyboard.press('w')
                    await page.wait_for_timeout(2000)
                    print("Interaction done.")
                except Exception as e:
                    print(f"Direct interaction failed (game might still be loading): {e}")
            else:
                print("No game iframe found. Checking if game is already on main page...")
                if await page.query_selector('#unity-canvas, #unity-container, canvas[id*="unity"]'):
                     print("Game appears to be on main page.")
                     # Do interaction here if needed
                else:
                     print("Could not find game frame or canvas.")

        except Exception as e:
            print(f"Unity interaction note: {e}")

        print("Page loaded. Starting auto-scroll to trigger lazy loading...")
        
        # Auto-scroll function
        await page.evaluate("""
            async () => {
                await new Promise((resolve) => {
                    let totalHeight = 0;
                    let distance = 100;
                    let timer = setInterval(() => {
                        let scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;

                        if(totalHeight >= scrollHeight - window.innerHeight){
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
        """)
        
        # Wait a bit after scrolling for any final assets to load
        print("Scroll complete. Waiting for trailing network activity...")
        await page.wait_for_timeout(5000)

        # Close context to ensure HAR is saved
        await context.close()
        await browser.close()
        
        print(f"Capture complete! Saved to: {output_file}")
        
        # 4. Post-Capture: Manually fetch binary files (WASM/Data) if we know the URL
        # The HAR often misses strict binary streams or partial content
        if game_iframe_url:
            print("Attempting manual fetch of potential missing binaries (Data/Wasm)...")
            # Construct base URL from iframe URL
            # e.g. https://html-classic.itch.zone/html/14978833/index.html -> https://html-classic.itch.zone/html/14978833/Build/
            import urllib.parse
            base_url = game_iframe_url.rsplit('/', 1)[0]
            build_url = f"{base_url}/Build"
            
            # Common Unity filenames based on what we saw in the extract log or standard unity patterns
            # We urge the user to check 'New folder.data' specifically
            files_to_fetch = [
                "New%20folder.data", 
                "New%20folder.wasm", 
                "New%20folder.framework.js", 
                "New%20folder.loader.js"
            ]
            
            # Create a 'manual_download' folder
            manual_dir = "manual_downloads"
            if not os.path.exists(manual_dir):
                os.makedirs(manual_dir)
                
            for fname in files_to_fetch:
                file_url = f"{build_url}/{fname}"
                dest_path = os.path.join(manual_dir, urllib.parse.unquote(fname))
                print(f"Downloading {fname} from {file_url}...")
                
                # Use curl for reliability
                cmd = f"curl -L -o '{dest_path}' '{file_url}'"
                proc = await asyncio.create_subprocess_shell(cmd)
                await proc.communicate()
            
            print(f"Manual downloads complete in '{manual_dir}'. Move them to 'organized_src/Build' if needed.")

        print(f"You can now run: python3 extract_har.py {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 better_capture.py <url> [output_filename]")
        sys.exit(1)
        
    target_url = sys.argv[1]
    output_har = sys.argv[2] if len(sys.argv) > 2 else "capture.har"
    
    asyncio.run(run(target_url, output_har))
