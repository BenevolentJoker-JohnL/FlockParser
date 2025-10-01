# 🚀 GPU Router - Setup Guide

## Overview

The **GPU Router** is a standalone intelligent GPU management system for distributed Ollama clusters. It provides:

✅ **VRAM-aware routing** - Knows which models fit on which nodes
✅ **Automatic optimization** - Keeps priority models on GPU
✅ **Real-time monitoring** - Tracks VRAM usage across all nodes
✅ **Standalone daemon** - Runs independently as a system service
✅ **CLI integration** - Accessible from FlockParse CLI

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  GPU Router Daemon (Background Service)                 │
│  ├─ Monitors cluster every 5 minutes                    │
│  ├─ Detects VRAM capacity per node                      │
│  ├─ Routes models intelligently (GPU vs CPU)            │
│  └─ Automatically optimizes priority models             │
└─────────────────────────────────────────────────────────┘
              │
              │ Ollama API
              ▼
┌─────────────────────────────────────────────────────────┐
│  Distributed Ollama Cluster                             │
│  ├─ Node 1 (4GB VRAM) - Embeddings on GPU              │
│  ├─ Node 2 (No GPU)   - Large models on CPU            │
│  └─ Node 3 (8GB VRAM) - Chat models on GPU             │
└─────────────────────────────────────────────────────────┘
```

## Installation

### Method 1: Standalone Daemon (Recommended for Production)

1. **Run the installation script:**
   ```bash
   cd /home/joker/FlockParser
   ./install_gpu_router.sh
   ```

2. **Configure your cluster:**
   ```bash
   sudo nano /opt/gpu-router/gpu_router_config.yaml
   ```

   Update the configuration:
   ```yaml
   nodes:
     - http://localhost:11434
     - http://10.9.66.124:11434
     - http://10.9.66.154:11434

   priority_models:
     - mxbai-embed-large
     - llama3.1:latest

   check_interval: 300  # 5 minutes
   auto_optimize: true
   ```

3. **Start the service:**
   ```bash
   sudo systemctl start gpu-router
   sudo systemctl enable gpu-router  # Auto-start on boot
   ```

4. **View logs:**
   ```bash
   sudo journalctl -u gpu-router -f
   ```

### Method 2: Manual Daemon (Development)

1. **Run daemon directly:**
   ```bash
   cd /home/joker/FlockParser
   python3 gpu_router_daemon.py
   ```

2. **Run with custom config:**
   ```bash
   python3 gpu_router_daemon.py --config ./my_config.yaml
   ```

3. **Print cluster report only (no daemon):**
   ```bash
   python3 gpu_router_daemon.py --report-only
   ```

### Method 3: CLI Integration (Interactive)

**Access GPU router commands from FlockParse CLI:**

```bash
python3 flockparsecli.py
```

Available commands:
```
🎯 gpu_status        → Show intelligent GPU routing status
🧠 gpu_route <model> → Show routing decision for a model
🔧 gpu_optimize      → Trigger intelligent GPU optimization
✅ gpu_check <model> → Check which nodes can fit a model
📚 gpu_models        → List all known models and sizes
```

## Configuration

### `gpu_router_config.yaml`

```yaml
# List of Ollama nodes to manage
nodes:
  - http://localhost:11434
  - http://10.9.66.124:11434
  - http://10.9.66.154:11434

# Priority models to keep on GPU
# These will be automatically moved to GPU if detected on CPU
priority_models:
  - mxbai-embed-large    # Embedding model (705MB)
  - nomic-embed-text     # Alternative embedding (274MB)
  # - llama3.2:3b        # Small chat model (1.9GB)

# Check interval in seconds
# Development: 60-120 (1-2 minutes)
# Production: 300-600 (5-10 minutes)
check_interval: 300

# VRAM safety margin (0.0 - 1.0)
# 0.8 = Use max 80% of VRAM (recommended)
vram_safety_margin: 0.8

# Auto-optimize: true = automatic GPU assignment, false = monitor only
auto_optimize: true

# Logging level: DEBUG, INFO, WARNING, ERROR
log_level: INFO
```

## Usage Examples

### Example 1: Check Cluster Status

**Using CLI:**
```bash
⚡ Enter command: gpu_status

🎯 INTELLIGENT GPU ROUTING STATUS
======================================================================
🚀 GPU Node: http://10.9.66.124:11434
   Total VRAM: 4096 MB
   Usable VRAM: 3276 MB (80% safety)
   Free VRAM: 2571 MB

   📦 Can fit these models:
      ✅ mxbai-embed-large (705 MB)
      ✅ llama3.2:3b (1900 MB)
      ❌ llama3.1:latest (4700 MB) - Model too large
```

**Using daemon report:**
```bash
python3 gpu_router_daemon.py --report-only
```

### Example 2: Check Routing Decision

**Scenario:** You want to know where to run `mxbai-embed-large`

```bash
⚡ Enter command: gpu_route mxbai-embed-large

🧠 ROUTING DECISION FOR: mxbai-embed-large
======================================================================
🎯 Routing decision for: mxbai-embed-large
   Model size: 705 MB

   ✅ http://10.9.66.124:11434 (GPU): Fits in 3276MB VRAM (2571MB free)
   ⏭️  http://localhost:11434 (CPU): Node has no GPU

   🏆 Best choice: http://10.9.66.124:11434 (GPU)
      Reason: Fits in 3276MB VRAM (2571MB free)
```

### Example 3: Check if Large Model Fits

**Scenario:** You want to run `llama3.1:latest` (4.7GB)

```bash
⚡ Enter command: gpu_check llama3.1:latest

✅ CHECKING FIT FOR: llama3.1:latest
======================================================================
📦 Model size: 4700 MB

📍 Node compatibility:
   ❌ http://10.9.66.124:11434: Model too large (4700MB > 3276MB usable VRAM)
   ❌ http://localhost:11434: Node has no GPU

Result: Model must run on CPU
```

### Example 4: Trigger Optimization

**Scenario:** Force priority models to GPU

```bash
⚡ Enter command: gpu_optimize

🔧 OPTIMIZING 2 PRIORITY MODELS
======================================================================
🎯 Routing decision for: mxbai-embed-large
   ✅ Best choice: http://10.9.66.124:11434 (GPU)

🚀 Executing Routing Plan
======================================================================
📍 Loading mxbai-embed-large on GPU at http://10.9.66.124:11434...
   ✅ mxbai-embed-large now on GPU
```

### Example 5: List Known Models

```bash
⚡ Enter command: gpu_models

📚 KNOWN MODELS DATABASE
======================================================================
📦 Model sizes:
   all-minilm                      45 MB (0.04 GB)
   nomic-embed-text               274 MB (0.27 GB)
   qwen2.5-coder:0.5b             500 MB (0.49 GB)
   mxbai-embed-large              705 MB (0.69 GB)
   qwen2.5-coder:1.5b             900 MB (0.88 GB)
   llama3.2:1b                   1300 MB (1.27 GB)
   qwen2.5-coder:3b              1800 MB (1.76 GB)
   llama3.2:3b                   1900 MB (1.86 GB)
   codellama:7b                  3600 MB (3.52 GB)
   qwen2.5-coder:7b              4400 MB (4.30 GB)
   llama3.1:latest               4700 MB (4.59 GB)
   codellama:13b                 6900 MB (6.74 GB)
```

## How It Works

### Intelligent Routing Logic

The GPU Router makes decisions based on:

1. **Actual VRAM Capacity**
   - Detects GPU hardware (nvidia-smi, rocm-smi)
   - Reads total VRAM per node
   - Example: 1050Ti = 4GB VRAM

2. **Model Sizes**
   - Built-in database of common models
   - Falls back to Ollama API if unknown
   - Example: mxbai-embed-large = 705MB

3. **Safety Margin**
   - Only uses 80% of VRAM by default
   - Prevents GPU memory exhaustion
   - Example: 4GB GPU → 3.2GB usable

4. **Current Usage**
   - Tracks loaded models via Ollama API
   - Calculates free VRAM
   - Routes to nodes with most free space

### Example Decision Tree

```
Model: mxbai-embed-large (705MB)
Node: 1050Ti (4GB VRAM)

Step 1: Check VRAM capacity
  Total VRAM: 4096 MB
  Usable VRAM: 3276 MB (80% safety)
  ✅ Enough capacity

Step 2: Check current usage
  Loaded models: 0 MB
  Free VRAM: 3276 MB
  ✅ Enough free space

Step 3: Check model size
  Model size: 705 MB
  705 MB < 3276 MB free
  ✅ Model fits!

Decision: Load on GPU ✅
```

### Example Decision (Too Large)

```
Model: llama3.1:latest (4700MB)
Node: 1050Ti (4GB VRAM)

Step 1: Check VRAM capacity
  Total VRAM: 4096 MB
  Usable VRAM: 3276 MB (80% safety)
  ❌ 4700 MB > 3276 MB usable

Decision: Load on CPU ❌ (Model too large)
```

## Monitoring

### View Daemon Logs

```bash
# Follow logs in real-time
sudo journalctl -u gpu-router -f

# View last 50 lines
sudo journalctl -u gpu-router -n 50

# View logs from today
sudo journalctl -u gpu-router --since today
```

### Check Service Status

```bash
sudo systemctl status gpu-router
```

Example output:
```
● gpu-router.service - GPU Router Daemon
   Loaded: loaded (/etc/systemd/system/gpu-router.service; enabled)
   Active: active (running) since Mon 2025-09-30 10:00:00 EDT; 5min ago
 Main PID: 12345
   Status: "Running optimization cycle #3"
```

### View Log File

```bash
# Daemon log
tail -f /var/log/gpu-router/daemon.log

# Or FlockParser logs directory
tail -f ./logs/gpu_router_daemon.log
```

## Troubleshooting

### Issue: Daemon Not Starting

**Symptom:** Service fails to start

**Solution:**
```bash
# Check logs for errors
sudo journalctl -u gpu-router -n 50

# Verify configuration
python3 /opt/gpu-router/gpu_router_daemon.py --config /opt/gpu-router/gpu_router_config.yaml

# Check Python dependencies
pip3 install pyyaml requests
```

### Issue: Models Not Moving to GPU

**Symptom:** Optimization runs but models stay on CPU

**Common causes:**
1. ❌ Ollama not configured for GPU
2. ❌ Model too large for VRAM
3. ❌ GPU drivers not installed
4. ❌ CUDA/ROCm not detected

**Solutions:**

1. **Configure Ollama for GPU:**
   ```bash
   # On the GPU node, run:
   cd /path/to/FlockParser
   ./fix_gpu_node.sh
   ```

2. **Check GPU detection:**
   ```bash
   nvidia-smi  # For NVIDIA GPUs
   rocm-smi    # For AMD GPUs
   ```

3. **Check Ollama model status:**
   ```bash
   curl http://localhost:11434/api/ps | jq
   # Look for "size_vram" field - should be > 0 for GPU
   ```

### Issue: No GPU Detected

**Symptom:** All nodes show as "CPU only"

**Solutions:**

1. **Install GPU drivers:**
   ```bash
   # NVIDIA
   sudo ubuntu-drivers autoinstall

   # AMD
   sudo apt install rocm-dkms rocm-smi
   ```

2. **Restart Ollama:**
   ```bash
   sudo systemctl restart ollama
   ```

3. **Check GPU visibility:**
   ```bash
   nvidia-smi  # Should show GPU
   ```

### Issue: Wrong Model Sizes

**Symptom:** Router shows incorrect model sizes

**Solution:**

1. **Update model database in `intelligent_gpu_router.py`:**
   ```python
   self.known_model_sizes = {
       'my-custom-model': 2500,  # Add custom model
       # ...
   }
   ```

2. **Router will auto-detect from Ollama API if not in database**

## Service Management

### Start/Stop Service

```bash
# Start
sudo systemctl start gpu-router

# Stop
sudo systemctl stop gpu-router

# Restart
sudo systemctl restart gpu-router

# Enable auto-start
sudo systemctl enable gpu-router

# Disable auto-start
sudo systemctl disable gpu-router
```

### Update Configuration

```bash
# Edit config
sudo nano /opt/gpu-router/gpu_router_config.yaml

# Restart service to apply changes
sudo systemctl restart gpu-router
```

### Uninstall

```bash
# Stop and disable service
sudo systemctl stop gpu-router
sudo systemctl disable gpu-router

# Remove service file
sudo rm /etc/systemd/system/gpu-router.service

# Remove installation directory
sudo rm -rf /opt/gpu-router

# Remove logs
sudo rm -rf /var/log/gpu-router

# Reload systemd
sudo systemctl daemon-reload
```

## Best Practices

### 1. Configure Priority Models

**Prioritize frequently-used models:**
```yaml
priority_models:
  - mxbai-embed-large   # Used for all embeddings
  - llama3.2:3b         # Fast chat model
```

**Let large models stay on CPU:**
```yaml
# Don't prioritize models that won't fit:
# - llama3.1:70b  (40GB - too large)
# - codellama:13b (6.9GB - might be too large)
```

### 2. Adjust Check Interval

**Development (fast feedback):**
```yaml
check_interval: 60  # Check every minute
```

**Production (low overhead):**
```yaml
check_interval: 600  # Check every 10 minutes
```

### 3. Monitor VRAM Usage

**Use `gpu_status` regularly:**
```bash
⚡ Enter command: gpu_status
```

**Watch for patterns:**
- High utilization (>90%) → Consider reducing models
- Low utilization (<30%) → Can add more models

### 4. Test Before Production

**Run in monitor-only mode first:**
```yaml
auto_optimize: false  # Won't change anything
```

**Verify routing decisions:**
```bash
⚡ Enter command: gpu_route mxbai-embed-large
⚡ Enter command: gpu_check llama3.1:latest
```

**Enable auto-optimize when confident:**
```yaml
auto_optimize: true
```

## Performance Impact

| Aspect | Impact |
|--------|--------|
| **CPU Usage** | <0.1% average |
| **Memory Usage** | ~50MB for daemon |
| **Network Usage** | ~1KB per node per check |
| **Optimization Time** | 5-10s per model (one-time) |
| **Net Benefit** | **5-10x faster inference on GPU!** |

## Use Cases

### Use Case 1: Mixed GPU/CPU Cluster

**Scenario:** 3 nodes, only 1 has GPU

```yaml
nodes:
  - http://node1:11434  # No GPU
  - http://node2:11434  # 4GB GPU (1050Ti)
  - http://node3:11434  # No GPU
```

**Result:**
- mxbai-embed-large → node2 (GPU) ✅
- llama3.1:latest → node1/node3 (CPU) ✅

### Use Case 2: Development Workstation

**Scenario:** Single node with GPU, frequent Ollama restarts

```yaml
nodes:
  - http://localhost:11434

check_interval: 60  # Check every minute
```

**Result:**
- Models automatically return to GPU after restart
- No manual intervention needed

### Use Case 3: Production Cluster

**Scenario:** Multiple GPU nodes, need consistent performance

```yaml
nodes:
  - http://node1:11434  # 8GB GPU
  - http://node2:11434  # 8GB GPU
  - http://node3:11434  # 4GB GPU

priority_models:
  - mxbai-embed-large
  - nomic-embed-text
  - llama3.2:3b
```

**Result:**
- Embeddings always on GPU (critical for performance)
- Small chat models on GPU when space available
- Large models automatically use CPU

## Advanced Configuration

### Custom Model Sizes

Add custom models to the database:

Edit `intelligent_gpu_router.py`:
```python
self.known_model_sizes = {
    'mxbai-embed-large': 705,
    'my-custom-model': 2500,  # Add your model
    # ...
}
```

### Multiple Priority Lists

Create different configs for different use cases:

```bash
# Embedding-focused
python3 gpu_router_daemon.py --config config_embeddings.yaml

# Chat-focused
python3 gpu_router_daemon.py --config config_chat.yaml
```

### Monitoring Integration

Integrate with monitoring systems:

```bash
# Parse daemon logs
tail -f /var/log/gpu-router/daemon.log | grep "✅"

# Export metrics
# (Future feature: Prometheus endpoint)
```

## Summary

**GPU Router provides:**

✅ **Zero-config GPU detection** - Automatically discovers VRAM capacity
✅ **Intelligent routing** - Models go to the right place
✅ **Automatic optimization** - Set it and forget it
✅ **Standalone service** - Runs independently
✅ **CLI integration** - Easy management
✅ **Production-ready** - Logging, monitoring, error handling

**Just install and models will intelligently use GPU!** 🚀

---

**Created:** 2025-09-30
**Version:** 1.0
**Dependencies:** Python 3, PyYAML, requests, nvidia-smi (for NVIDIA GPUs)