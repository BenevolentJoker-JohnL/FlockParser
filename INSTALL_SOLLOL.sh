#!/bin/bash
# Quick setup script for SOLLOL integration

echo "🚀 Installing SOLLOL for FlockParser..."
echo ""

# Check if SOLLOL exists
if [ ! -d "$HOME/SOLLOL" ]; then
    echo "❌ SOLLOL not found at ~/SOLLOL"
    echo "Please clone or install SOLLOL first"
    exit 1
fi

# Option 1: Add to PYTHONPATH (quick test)
echo "Option 1: Quick Test (PYTHONPATH)"
echo "  export PYTHONPATH=\"$HOME/SOLLOL/src:\$PYTHONPATH\""
echo "  python flockparsecli.py"
echo ""

# Option 2: Install editable
echo "Option 2: Install SOLLOL (editable mode)"
echo "  cd ~/SOLLOL && pip install --user -e ."
echo "  cd ~/FlockParser"
echo ""

# Option 3: Install from PyPI (future)
echo "Option 3: Install from PyPI (when published)"
echo "  pip install sollol>=0.7.0"
echo ""

echo "Choose your installation method and run the commands above."
echo ""
echo "✅ After installation, test with:"
echo "   python3 -c 'from sollol_adapter import OllamaLoadBalancer; print(\"✅ Works!\")'"
