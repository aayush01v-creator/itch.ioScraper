#!/bin/bash
set -e

echo "=== Setting up Better Capture Tool ==="

# 1. Install Python dependencies
echo "Installing playwright..."
pip install playwright

# 2. Install Playwright browsers (specifically Firefox as requested)
echo "Installing Firefox binary for Playwright..."
playwright install firefox

echo ""
echo "Setup complete!"
echo "Usage: python3 better_capture.py <URL>"
