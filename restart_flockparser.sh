#!/bin/bash
# Restart FlockParser with all fixes applied

echo "=============================================="
echo "  FlockParser Restart Script"
echo "=============================================="
echo ""

# Kill old process
echo "Step 1: Stopping old FlockParser process..."
pkill -f "python.*flockparsecli\.py"
sleep 2

# Confirm it's stopped
if pgrep -f "python.*flockparsecli\.py" > /dev/null; then
    echo "⚠️  Warning: FlockParser still running, trying SIGKILL..."
    pkill -9 -f "python.*flockparsecli\.py"
    sleep 1
fi

if pgrep -f "python.*flockparsecli\.py" > /dev/null; then
    echo "❌ Error: Could not stop FlockParser"
    exit 1
else
    echo "✅ FlockParser stopped"
fi

echo ""
echo "Step 2: Starting FlockParser with fixes..."
cd /home/joker/FlockParser

echo ""
echo "=============================================="
echo "  FlockParser is starting..."
echo "=============================================="
echo ""
echo "Expected to see:"
echo "  1. 🚀 FlockParser ready!"
echo "  2. ⚡ Enter command: (should be visible)"
echo ""
echo "If prompt is not visible, press Ctrl+C and run:"
echo "  python -u flockparsecli.py"
echo ""

# Start FlockParser
python flockparsecli.py
