import json
import os
import base64
from mitmproxy import http

# Path to save HAR file
HAR_PATH = os.environ.get("HAR_CAPTURE_PATH", "capture.har")

class HARRecorder:
    def __init__(self):
        self.entries = []

    def response(self, flow: http.HTTPFlow):
        # We only care about successful responses to save
        entry = {
            "startedDateTime": flow.request.timestamp_start,
            "request": {
                "method": flow.request.method,
                "url": flow.request.url,
                "headers": [{"name": k, "value": v} for k, v in flow.request.headers.items()],
            },
            "response": {
                "status": flow.response.status_code,
                "statusText": flow.response.reason,
                "headers": [{"name": k, "value": v} for k, v in flow.response.headers.items()],
                "content": {
                    "mimeType": flow.response.headers.get("Content-Type", ""),
                    "text": "",
                    "encoding": ""
                }
            }
        }

        # Handle content
        if flow.response.content:
            try:
                entry["response"]["content"]["text"] = flow.response.content.decode("utf-8")
            except UnicodeDecodeError:
                # Fallback to base64 for binary
                entry["response"]["content"]["text"] = base64.b64encode(flow.response.content).decode("ascii")
                entry["response"]["content"]["encoding"] = "base64"

        self.entries.append(entry)

    def done(self):
        har_data = {
            "log": {
                "version": "1.2",
                "creator": {"name": "mitmproxy_addon", "version": "1.0"},
                "entries": self.entries
            }
        }
        
        with open(HAR_PATH, "w", encoding="utf-8") as f:
            json.dump(har_data, f, indent=2)
        print(f"Saved HAR to {HAR_PATH}")

addons = [HARRecorder()]
