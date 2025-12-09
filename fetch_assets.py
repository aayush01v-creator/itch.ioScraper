import os
import re
import requests
from urllib.parse import urlparse

# Base directory for organized assets
BASE_DIR = "organized_src"
HTML_FILE = os.path.join(BASE_DIR, "index.html")

def download_asset(url, local_path):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb') as f:
                f.write(response.content)
            print(f"Downloaded: {url} -> {local_path}")
            return True
        else:
            print(f"Failed (Status {response.status_code}): {url}")
            return False
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def fix_assets():
    if not os.path.exists(HTML_FILE):
        print("index.html not found!")
        return

    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Regex to find assets on udemycdn.com
    # Searching for https://[subdomain].udemycdn.com/[path]
    # We want to capture the full URL and map it to a local path
    
    # Pattern for link hrefs and script srcs
    # Group 1: Quote (or empty)
    # Group 2: URL
    pattern = re.compile(r'(href|src)=["\'](https://[^"\']*udemycdn\.com[^"\']*)["\']')
    
    new_content = content
    seen_urls = set()

    matches = pattern.findall(content)
    print(f"Found {len(matches)} potential asset links.")

    for attr, url in matches:
        if url in seen_urls:
            continue
        seen_urls.add(url)

        parsed = urlparse(url)
        # We will map:
        # https://frontends.udemycdn.com/frontends-homepage/... -> organized_src/frontends-homepage/...
        # https://img-c.udemycdn.com/... -> organized_src/images/...
        # https://s.udemycdn.com/... -> organized_src/s/... (maybe?)

        domain = parsed.netloc
        path = parsed.path.lstrip('/')
        
        local_rel_path = ""
        
        if "frontends.udemycdn.com" in domain:
            # e.g. frontends-homepage/_next/...
            # We want to keep the path structure exactly as is relative to root
            # But wait, the URL path starts with /frontends-homepage/ usually?
            # Let's just mirror the path locally.
            local_rel_path = path # e.g. frontends-homepage/_next/static/css/...
        elif "img-" in domain or "cms-images" in domain:
            local_rel_path = os.path.join("images", os.path.basename(path))
            # Note: flattening images might break duplicates, but good enough for now
        elif "s.udemycdn.com" in domain:
             local_rel_path = os.path.join("s_assets", path)
        else:
            # Fallback
            local_rel_path = os.path.join("misc", domain, path)

        full_local_path = os.path.join(BASE_DIR, local_rel_path)
        
        # Download the file
        if download_asset(url, full_local_path):
            # Update HTML content
            # We need to replace the absolute URL with the relative path
            # relative path from index.html (which is in organized_src root) is just local_rel_path
            new_content = new_content.replace(url, local_rel_path)

    with open(HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Updated index.html with local links.")

if __name__ == "__main__":
    fix_assets()
