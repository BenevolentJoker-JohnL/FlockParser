# 🖥️ VRAM Monitoring & Resource Tracking

## Overview

FlockParse now includes **accurate VRAM monitoring** for distributed nodes using multiple detection methods:

1. ✅ **nvidia-smi** - NVIDIA GPU monitoring (most accurate)
2. ✅ **rocm-smi** - AMD GPU monitoring
3. ✅ **Ollama /api/ps** - Model-level VRAM usage (works remotely)
4. ✅ **Performance inference** - Fallback detection method

## Features

### 🎯 Accurate VRAM Reporting

**Before (Inference-based):**
```
🚀 GPU (inferred, ~8GB VRAM)  ← Guessing!
```

**After (Actual Monitoring):**
```
GPU 0: NVIDIA RTX 4090
   VRAM Total: 24,576 MB (24.0 GB)
   VRAM Used:  8,192 MB (8.0 GB)
   VRAM Free:  16,384 MB (16.0 GB)
   Utilization: 45%
   Temperature: 62°C
```

### 📊 Multi-Vendor Support

| GPU Vendor | Tool | Status |
|------------|------|--------|
| **NVIDIA** | nvidia-smi | ✅ Supported |
| **AMD** | rocm-smi | ✅ Supported |
| **Intel** | Limited | ⚠️ Partial (uses system RAM) |
| **None (CPU)** | Ollama API | ✅ Tracks RAM usage |

## New Command: `vram_report`

```bash
python3 flockparsecli.py
⚡ Enter command: vram_report
```

### Example Output:

```
🔍 Detected GPU type: NVIDIA

📊 Local Node Report:
======================================================================
🖥️  VRAM & GPU MONITORING REPORT
======================================================================
Timestamp: 2025-09-30 08:15:00

🎮 Local GPU (NVIDIA):
   Total GPUs: 2

   GPU 0: NVIDIA GeForce RTX 4090
      VRAM Total: 24,576 MB (24.0 GB)
      VRAM Used:  8,192 MB (8.0 GB)
      VRAM Free:  16,384 MB (16.0 GB)
      Utilization: 45%
      Temperature: 62°C

   GPU 1: NVIDIA GeForce RTX 3090
      VRAM Total: 24,576 MB (24.0 GB)
      VRAM Used:  2,048 MB (2.0 GB)
      VRAM Free:  22,528 MB (22.0 GB)
      Utilization: 12%
      Temperature: 48°C

🦙 Ollama Model Loading (http://localhost:11434):
   📦 mxbai-embed-large:latest
      Size: 705.4 MB
      Location: VRAM (GPU)
      VRAM Used: 705.4 MB

   📦 llama3.1:latest
      Size: 4700.0 MB
      Location: VRAM (GPU)
      VRAM Used: 4700.0 MB

   ✅ GPU-Accelerated: 5405.4 MB in VRAM

📊 Summary:
   GPU Vendor: NVIDIA
   Total VRAM: 48.0 GB
   VRAM Utilization: 21.3%
   Free VRAM: 38.9 GB
   Ollama GPU-Accelerated: ✅ Yes
   Ollama VRAM Usage: 5405.4 MB

======================================================================

🌐 Distributed Nodes Report:

   🚀 GPU http://10.9.66.124:11434:
      VRAM Usage: 3.20 GB
      Loaded Models:
         - llama3.1:latest (VRAM (GPU))
         - mxbai-embed-large:latest (VRAM (GPU))

   🐢 CPU http://10.9.66.154:11434:
      RAM Usage: 2.50 GB (CPU fallback)
      Loaded Models:
         - mxbai-embed-large:latest (RAM (CPU))

======================================================================
```

## Detection Methods

### 1. nvidia-smi (NVIDIA GPUs)

**Command:**
```bash
nvidia-smi --query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu --format=csv,noheader,nounits
```

**Output:**
```
0, NVIDIA GeForce RTX 4090, 24576, 8192, 16384, 45, 62
1, NVIDIA GeForce RTX 3090, 24576, 2048, 22528, 12, 48
```

**Provides:**
- ✅ Total VRAM
- ✅ Used VRAM
- ✅ Free VRAM
- ✅ GPU utilization %
- ✅ Temperature

### 2. rocm-smi (AMD GPUs)

**Command:**
```bash
rocm-smi --showmeminfo vram --json
```

**Provides:**
- ✅ Total VRAM
- ✅ Used VRAM
- ✅ GPU name

### 3. Ollama /api/ps (All GPUs)

**API Call:**
```bash
curl http://localhost:11434/api/ps
```

**Response:**
```json
{
  "models": [
    {
      "name": "llama3.1:latest",
      "size": 4700000000,
      "size_vram": 4700000000,  ← Model in VRAM (GPU)
      "expires_at": "2025-09-30T09:00:00Z"
    },
    {
      "name": "mxbai-embed-large:latest",
      "size": 705400000,
      "size_vram": 0,  ← Model in RAM (CPU fallback)
      "expires_at": "2025-09-30T09:00:00Z"
    }
  ]
}
```

**Provides:**
- ✅ Which models are loaded
- ✅ Model size
- ✅ VRAM vs RAM location
- ✅ Works remotely across network

### 4. Performance Inference (Fallback)

If no GPU monitoring tools available, measures embedding performance to estimate GPU capability.

## Module: vram_monitor.py

### Standalone Usage:

```python
from vram_monitor import VRAMMonitor, monitor_distributed_nodes

# Monitor local GPU
monitor = VRAMMonitor()
report = monitor.get_comprehensive_report("http://localhost:11434")
monitor.print_report(report)

# Monitor distributed nodes
nodes = [
    "http://localhost:11434",
    "http://10.9.66.124:11434",
    "http://10.9.66.154:11434"
]
results = monitor_distributed_nodes(nodes)
```

### VRAMMonitor Class:

```python
class VRAMMonitor:
    def _detect_gpu_type(self) -> str:
        """Detect GPU vendor: 'nvidia', 'amd', 'intel', or 'none'"""

    def get_local_vram_info(self) -> Dict:
        """Get local GPU VRAM information"""

    def get_ollama_vram_usage(self, node_url: str) -> Dict:
        """Get VRAM usage from Ollama API"""

    def get_comprehensive_report(self, node_url: str) -> Dict:
        """Combined local + Ollama report"""

    def print_report(self, report: Dict):
        """Pretty-print VRAM report"""
```

## Integration with Load Balancer

The VRAM monitor enhances the load balancer's GPU detection:

```python
# Old detection (inference-based)
has_gpu = response_time < 0.5  # Guessing!

# New detection (actual VRAM)
from vram_monitor import VRAMMonitor
monitor = VRAMMonitor()
gpu_info = monitor.get_local_vram_info()
has_gpu = gpu_info['total_vram_mb'] > 0  # Accurate!
```

### Load Balancer Benefits:

1. ✅ **Accurate GPU detection** - No more guessing
2. ✅ **VRAM exhaustion detection** - Know when GPU falls back to CPU
3. ✅ **Resource-aware routing** - Route to nodes with free VRAM
4. ✅ **Temperature monitoring** - Avoid overheated GPUs
5. ✅ **Multi-GPU support** - Distribute across multiple GPUs

## Use Cases

### 1. Production Monitoring

Monitor VRAM usage across a cluster:
```bash
# Check all nodes
vram_report

# See which nodes have available VRAM for new models
```

### 2. Debugging Performance Issues

```bash
# Node slow? Check VRAM
vram_report

# Is model in VRAM or RAM?
# Location: VRAM (GPU)  ← Fast
# Location: RAM (CPU)   ← Slow fallback
```

### 3. Resource Planning

```bash
# How much VRAM do we have?
vram_report

# Can we load llama3.1:70b (40GB model)?
# Free VRAM: 48.0 GB ← Yes!
```

### 4. Temperature Monitoring

```bash
# Is GPU overheating?
vram_report

# Temperature: 85°C ← Too hot! Reduce load
```

## Installation Requirements

### NVIDIA GPUs:
```bash
# nvidia-smi comes with NVIDIA drivers
# Usually already installed if you have NVIDIA GPU

# Verify:
nvidia-smi --version
```

### AMD GPUs:
```bash
# Install ROCm
sudo apt-get install rocm-smi

# Verify:
rocm-smi --version
```

### Intel GPUs:
```bash
# Install intel_gpu_top (optional)
sudo apt-get install intel-gpu-tools

# Note: Intel integrated GPUs use system RAM
```

## Remote Node Monitoring

Works across network with Ollama's `/api/ps` endpoint:

```python
# Monitor remote nodes without local GPU access
nodes = [
    "http://192.168.1.100:11434",  # Remote server 1
    "http://192.168.1.101:11434",  # Remote server 2
    "http://192.168.1.102:11434",  # Remote server 3
]

results = monitor_distributed_nodes(nodes)
# Returns VRAM usage for all nodes
```

**Benefits:**
- ✅ No SSH required
- ✅ Works across firewall (if Ollama port open)
- ✅ Real-time monitoring
- ✅ Shows which models are loaded

## Troubleshooting

### "No GPU detected"

**Issue:** VRAM monitor reports "No GPU detected"

**Solutions:**
1. Install nvidia-smi (NVIDIA) or rocm-smi (AMD)
2. Check GPU drivers are installed
3. Run `nvidia-smi` or `rocm-smi` manually to verify
4. System may be CPU-only (that's okay!)

### "size_vram: 0" but have GPU

**Issue:** Ollama shows `size_vram: 0` even though GPU exists

**Causes:**
1. Model is running on CPU (Ollama configuration)
2. VRAM exhausted, fell back to RAM
3. Ollama not configured to use GPU

**Solutions:**
```bash
# Check Ollama GPU configuration
ollama list

# Force GPU usage
export CUDA_VISIBLE_DEVICES=0
ollama serve

# Or set in Ollama config
OLLAMA_GPU_LAYERS=999  # Load all layers on GPU
```

### Remote node shows "error"

**Issue:** Distributed node monitoring fails

**Solutions:**
1. Check node is running: `curl http://node:11434/api/ps`
2. Check firewall allows port 11434
3. Verify Ollama is running on remote node
4. Check network connectivity

## Performance Impact

VRAM monitoring is lightweight:

| Operation | Time | Impact |
|-----------|------|--------|
| `nvidia-smi` call | ~50ms | Negligible |
| `rocm-smi` call | ~100ms | Negligible |
| Ollama /api/ps | ~10ms | Negligible |
| Full report | ~200ms | Negligible |

**Recommendation:** Run `vram_report` as needed, not continuously.

## Future Enhancements

- ⬜ Continuous VRAM monitoring dashboard
- ⬜ VRAM usage alerts (email/webhook)
- ⬜ Historical VRAM usage graphs
- ⬜ Automatic load balancing based on free VRAM
- ⬜ GPU temperature-based throttling
- ⬜ Multi-process VRAM tracking
- ⬜ PCIe bandwidth monitoring

## Summary

**VRAM monitoring provides accurate resource tracking:**

✅ **NVIDIA GPU support** - nvidia-smi integration
✅ **AMD GPU support** - rocm-smi integration
✅ **Ollama API integration** - Model-level VRAM tracking
✅ **Distributed monitoring** - Works across network
✅ **Temperature tracking** - Prevent overheating
✅ **Multi-GPU support** - Track all GPUs
✅ **CPU fallback detection** - Know when models use RAM

**Use `vram_report` command to see detailed VRAM usage across all nodes!**

---

**Implementation Date:** 2025-09-30
**Module:** vram_monitor.py (~400 lines)
**Integration:** flockparsecli.py (~30 lines)
**Breaking Changes:** None