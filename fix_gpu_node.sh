#!/bin/bash
# Fix GPU Node to Force GPU Usage
# Run this script ON the GPU node (10.9.66.124)

echo "🔧 Fixing Ollama GPU Configuration"
echo "=================================="

# Method 1: Set environment variables
echo ""
echo "Method 1: Setting environment variables..."
cat << 'EOF' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_NUM_GPU=999"
Environment="OLLAMA_GPU_LAYERS=-1"
Environment="CUDA_VISIBLE_DEVICES=0"
Environment="OLLAMA_KEEP_ALIVE=1h"
EOF

# Method 2: Stop Ollama, clear cache, restart
echo ""
echo "Method 2: Restarting Ollama with GPU enabled..."
sudo systemctl daemon-reload
sudo systemctl stop ollama
sleep 2

# Clear any cached models
rm -rf ~/.ollama/models/manifests/*
rm -rf ~/.ollama/models/blobs/*

# Restart Ollama
sudo systemctl start ollama
sleep 3

# Verify GPU is detected
echo ""
echo "Checking GPU detection..."
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "nvidia-smi not found (install NVIDIA drivers)"

# Pull embedding model with GPU
echo ""
echo "Re-pulling embedding model to force GPU..."
ollama pull mxbai-embed-large

# Test GPU usage
echo ""
echo "Testing GPU usage..."
echo "test" | ollama embed mxbai-embed-large

# Check if model is in VRAM
echo ""
echo "Checking model location..."
curl -s http://localhost:11434/api/ps | python3 -c "
import sys, json
data = json.load(sys.stdin)
for model in data.get('models', []):
    name = model.get('name')
    size_vram = model.get('size_vram', 0)
    location = 'GPU (VRAM)' if size_vram > 0 else 'CPU (RAM)'
    print(f'{name}: {location}')
"

echo ""
echo "✅ Done! Check output above to verify GPU usage"
echo "If still on CPU, check:"
echo "  1. NVIDIA drivers installed: nvidia-smi"
echo "  2. CUDA installed: nvcc --version"
echo "  3. Ollama service logs: sudo journalctl -u ollama -n 50"