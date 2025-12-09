#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

CURRENT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CAPTURE_DIR="$CURRENT_DIR/manual_captures"
mkdir -p "$CAPTURE_DIR"
CAPTURE_FILE="$CAPTURE_DIR/capture_$(date +%Y%m%d_%H%M%S).har"
MITM_SCRIPT="capture_har_addon.py"

if ! command -v mitmdump &> /dev/null; then
    echo -e "${RED}mitmproxy is not installed. Please run: pip install mitmproxy${NC}"
    exit 1
fi

echo -e "${GREEN}=== Manual Site Grabber ===${NC}"
echo -e "${YELLOW}NOTE: For best results (lazy loading, consistent headers), use 'better_capture.py' instead.${NC}"
echo -e "${YELLOW}Starting proxy server on port 8080...${NC}"

# Export env var for the addon
export HAR_CAPTURE_PATH="$CAPTURE_FILE"

# Start mitmdump background
mitmdump \
    -p 8080 \
    -s "$CURRENT_DIR/$MITM_SCRIPT" \
    --set confdir="$HOME/.mitmproxy" \
    > mitmproxy_manual.log 2>&1 &

MITM_PID=$!

sleep 3

if ! kill -0 $MITM_PID 2>/dev/null; then
    echo -e "${RED}Proxy failed to start. Check mitmproxy_manual.log${NC}"
    exit 1
fi

echo -e "${GREEN}Proxy running (PID $MITM_PID).${NC}"
echo ""
echo -e "${YELLOW}SETUP INSTRUCTIONS:${NC}"
echo "1. Connect your local machine to this codespace via SSH tunnel if needed:"
echo "   ssh -L 8080:localhost:8080 <your-codespace-host>"
echo "   (Or if running locally, just use 127.0.0.1:8080)"
echo ""
echo "2. Configure your browser proxy:"
echo "   - IP: 127.0.0.1"
echo "   - Port: 8080"
echo "   - Type: HTTP/HTTPS"
echo ""
echo "3. Install Certificate (First Time Only):"
echo "   - Visit http://mitm.it"
echo "   - Download/Install the certificate for your OS/Browser."
echo ""
echo "4. BROWSE! Go to the site you want to grab (e.g., Udemy)."
echo "   - Navigate around to trigger asset loading."
echo ""
echo -e "${GREEN}Press ENTER when finished capturing...${NC}"
read -r

echo -e "${YELLOW}Stopping proxy...${NC}"
kill $MITM_PID
wait $MITM_PID || true

echo -e "${GREEN}Capture saved to: $CAPTURE_FILE${NC}"
echo -e "${GREEN}Extracting assets...${NC}"

# Run extraction
python3 "$CURRENT_DIR/extract_har.py" "$CAPTURE_FILE"

echo -e "${GREEN}Assets extracted to 'src/'. Organizing now...${NC}"
python3 "$CURRENT_DIR/organize.py"

echo -e "${GREEN}Done! Site is ready in 'organized_src/'.${NC}"
