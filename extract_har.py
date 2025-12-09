import json
import os
import sys
import base64
from urllib.parse import urlparse

# Binary file extensions that should always be written in binary mode
BINARY_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico', '.bmp', '.svg',
    '.glb', '.gltf', '.bin', '.obj', '.fbx',
    '.woff', '.woff2', '.ttf', '.otf', '.eot',
    '.mp3', '.wav', '.ogg', '.m4a', '.aac',
    '.mp4', '.webm', '.avi', '.mov',
    '.zip', '.gz', '.tar', '.rar',
    '.pdf', '.wasm'
}

# MIME types that indicate binary content
BINARY_MIME_PREFIXES = [
    'image/', 'audio/', 'video/', 'application/octet-stream',
    'application/pdf', 'application/zip', 'application/wasm',
    'font/', 'model/'
]

def is_binary_content(path, mime_type):
    """Determine if content should be treated as binary based on extension or MIME type."""
    ext = os.path.splitext(path)[1].lower()
    if ext in BINARY_EXTENSIONS:
        return True
    if mime_type:
        for prefix in BINARY_MIME_PREFIXES:
            if mime_type.startswith(prefix):
                return True
    return False

def extract_har(har_path, output_dir="src"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(har_path, 'r', encoding='utf-8') as f:
        try:
            har_data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error reading HAR file: {e}")
            return

    entries = har_data.get('log', {}).get('entries', [])
    print(f"Found {len(entries)} entries in HAR.")

    for entry in entries:
        request = entry.get('request', {})
        response = entry.get('response', {})
        url = request.get('url')
        
        if not url or not response:
            continue

        parsed_url = urlparse(url)
        path = parsed_url.path
        query = parsed_url.query

        if query:
            # Use a simple FNV-1a hash for easy JS implementation
            def fnv1a_hash(string):
                hash_val = 0x811c9dc5
                for char in string:
                    hash_val ^= ord(char)
                    hash_val *= 0x01000193
                    hash_val &= 0xffffffff
                return hex(hash_val)[2:]

            query_hash = fnv1a_hash(query)
            
            # Append hash to the path to ensure uniqueness
            if path.endswith('/'):
                 path = path.rstrip('/') + "_" + query_hash
            else:
                root, ext = os.path.splitext(path)
                # Keep extension at the end if it exists and looks like a real file extension (short)
                if ext and len(ext) < 10: 
                    path = f"{root}_{query_hash}{ext}"
                else:
                    path = f"{path}_{query_hash}"

        if path == "/" or path == "":
            path = "/index.html"
        
        # Split path into components and sanitize each one
        # Some URLs have extremely long segments that violate filesystem limits (usually 255 bytes)
        parts = path.strip('/').split('/')
        safe_parts = []
        for part in parts:
            if len(part) > 150:  # Safety margin below 255
                # Create a safe simplified name: first 100 chars + hash of full name
                import hashlib
                part_hash = hashlib.md5(part.encode('utf-8')).hexdigest()[:8]
                safe_part = f"{part[:100]}_{part_hash}"
                safe_parts.append(safe_part)
            else:
                safe_parts.append(part)
        
        local_path = os.path.join(*safe_parts) if safe_parts else "index.html"
        
        # Construct full output path
        domain = parsed_url.netloc
        full_output_path = os.path.join(output_dir, domain, local_path)

        # Handle directory creation with conflict resolution
        directory = os.path.dirname(full_output_path)
        
        # Check if any part of the directory structure exists as a file
        current_check = output_dir
        parts_to_check = full_output_path.replace(output_dir, '').strip(os.sep).split(os.sep)
        
        # Iterate through the parts to find conflicts
        for i in range(len(parts_to_check) - 1): # Check all directories in the path
            current_check = os.path.join(current_check, parts_to_check[i])
            if os.path.isfile(current_check):
                # Conflict: We need this to be a directory, but it's a file.
                # Rename the existing file to allow directory creation
                print(f"Conflict detected: {current_check} is a file, but needs to be a directory. Renaming file.")
                try:
                    os.rename(current_check, current_check + "_file")
                except OSError as e:
                     print(f"Failed to rename conflicting file {current_check}: {e}")

        # Now attempting to create directories
        try:
            if not os.path.exists(directory):
                os.makedirs(directory)
        except OSError as e:
            if os.path.isfile(directory):
                 # Double check if it became a file in a race condition or missed above
                 print(f"Conflict: Directory {directory} exists as file. Renaming.")
                 os.rename(directory, directory + "_file")
                 os.makedirs(directory)
            else:
                print(f"Error creating directory {directory}: {e}")
                continue
        
        # Check if the target file itself is a directory (e.g. /foo/bar/ created, now writing /foo/bar)
        if os.path.isdir(full_output_path):
             print(f"Conflict: Target {full_output_path} is a directory. Appending /index.html")
             full_output_path = os.path.join(full_output_path, "index.html")


        content = response.get('content', {})
        content_text = content.get('text')
        encoding = content.get('encoding')
        mime_type = content.get('mimeType', '')

        if content_text:
            try:
                # Check if content is base64 encoded
                if encoding == 'base64':
                    content_bytes = base64.b64decode(content_text)
                    with open(full_output_path, 'wb') as out_file:
                        out_file.write(content_bytes)
                # Check if this is binary content that was UTF-8 encoded in HAR
                elif is_binary_content(local_path, mime_type):
                    # Recover binary data by encoding text as latin-1
                    # This reverses the UTF-8 decoding that happened during HAR creation
                    try:
                        content_bytes = content_text.encode('latin-1')
                    except UnicodeEncodeError:
                        # Fallback: encode as UTF-8 if latin-1 fails
                        content_bytes = content_text.encode('utf-8')
                    with open(full_output_path, 'wb') as out_file:
                        out_file.write(content_bytes)
                else:
                    # Text content - write as text
                    with open(full_output_path, 'w', encoding='utf-8') as out_file:
                        out_file.write(content_text)
                
                print(f"Extracted: {full_output_path}")
            except Exception as e:
                print(f"Failed to save {full_output_path}: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 extract_har.py <path_to_har_file>")
        sys.exit(1)
    
    har_file = sys.argv[1]
    extract_har(har_file)
