#!/bin/bash
# Start FlockParser in unbuffered mode (aggressive fix for prompt visibility)

echo "=============================================="
echo "  Starting FlockParser (Unbuffered Mode)"
echo "=============================================="
echo ""

# Kill old process
echo "Stopping any running FlockParser..."
pkill -9 -f "python.*flockparsecli\.py" 2>/dev/null
sleep 1

cd /home/joker/FlockParser

echo "Starting FlockParser with -u (unbuffered I/O)..."
echo ""

# Run with -u flag for unbuffered stdout/stderr
python -u flockparsecli.py
