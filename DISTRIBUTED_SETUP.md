# 🌐 Distributed Ollama Setup Guide

Complete guide to creating your own distributed Ollama cluster for FlockParser.

---

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start (Single Command)](#quick-start-single-command)
- [Step-by-Step Setup](#step-by-step-setup)
- [Node Discovery Methods](#node-discovery-methods)
- [Network Configuration](#network-configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Example Setups](#example-setups)

---

## Overview

**What is a distributed cluster?**

Instead of running Ollama on a single machine, you run it on multiple machines (nodes) and FlockParser intelligently distributes work across them based on:
- GPU availability
- VRAM capacity
- Network speed
- Current load

**Benefits:**
- 🚀 **60x+ speedups** - Real performance gains through parallelization
- 💰 **Use existing hardware** - Combine old GPUs with new ones
- 🔒 **Privacy maintained** - Everything stays on your local network
- ⚡ **Automatic failover** - If one node fails, others take over

---

## Prerequisites

### Hardware Requirements

**Minimum setup (2 nodes):**
- **Node 1:** Any computer with network access (can be CPU-only)
- **Node 2:** Any computer with network access (can be CPU-only)
- Both on the same local network (LAN)

**Recommended setup (3+ nodes):**
- **Node 1:** GPU-equipped machine (RTX 3060+, 8GB+ VRAM)
- **Node 2:** Another GPU or older GPU (GTX 1050Ti+, 4GB+ VRAM)
- **Node 3:** CPU-only machine or laptop (for fallback)

### Software Requirements

**On each node:**
- Linux, macOS, or Windows
- 4GB+ RAM (8GB+ recommended)
- Network connectivity (WiFi or Ethernet)
- Open port 11434 (Ollama default)

---

## Quick Start (Single Command)

### On Each Node Machine

**1. Install Ollama:**

```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh

# Windows
# Download installer from https://ollama.com/download
```

**2. Start Ollama to listen on network:**

```bash
# Linux/macOS - bind to all interfaces
OLLAMA_HOST=0.0.0.0:11434 ollama serve

# Or set permanently (recommended)
echo 'export OLLAMA_HOST=0.0.0.0:11434' >> ~/.bashrc
source ~/.bashrc
ollama serve
```

**3. Pull required models:**

```bash
# On each node, pull the models you want to use
ollama pull mxbai-embed-large    # Required for embeddings
ollama pull llama3.1:latest       # Required for chat
```

**4. Verify node is accessible:**

```bash
# From another machine on your network
curl http://NODE_IP:11434/api/tags

# Example:
curl http://192.168.1.90:11434/api/tags
```

That's it! FlockParser will auto-discover these nodes.

---

## Step-by-Step Setup

### Step 1: Identify Your Machines

**Find IP addresses of all machines you want to use:**

```bash
# Linux/macOS
ip addr show | grep "inet " | grep -v 127.0.0.1

# macOS (simpler)
ifconfig | grep "inet " | grep -v 127.0.0.1

# Windows
ipconfig | findstr IPv4
```

**Example output:**
```
Node 1: 192.168.1.90  (Desktop with RTX 4090)
Node 2: 192.168.1.91  (Laptop with GTX 1650)
Node 3: 192.168.1.92  (Old desktop, CPU-only)
```

**Write these down!** You'll need them later.

---

### Step 2: Install Ollama on Each Node

**On Node 1 (192.168.1.90):**

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Configure to listen on network
export OLLAMA_HOST=0.0.0.0:11434

# Start Ollama
ollama serve
```

**Repeat on Node 2 (192.168.1.91):**

```bash
curl -fsSL https://ollama.com/install.sh | sh
export OLLAMA_HOST=0.0.0.0:11434
ollama serve
```

**Repeat on Node 3 (192.168.1.92):**

```bash
curl -fsSL https://ollama.com/install.sh | sh
export OLLAMA_HOST=0.0.0.0:11434
ollama serve
```

---

### Step 3: Pull Models on Each Node

**Why pull on each node?**
- Faster first run (no network download during inference)
- Works offline after initial setup
- Better reliability

**On each node:**

```bash
# Essential models
ollama pull mxbai-embed-large    # Embeddings (705MB)
ollama pull llama3.1:latest       # Chat (4.7GB)

# Optional models
ollama pull llama3.2:3b           # Smaller chat (1.9GB)
ollama pull nomic-embed-text      # Alternative embeddings (274MB)
```

**Tip:** Pull smaller models on nodes with limited VRAM.

---

### Step 4: Test Each Node

**From your main machine (where FlockParser runs):**

```bash
# Test Node 1
curl http://192.168.1.90:11434/api/tags
# Should return JSON with model list

# Test Node 2
curl http://192.168.1.91:11434/api/tags

# Test Node 3
curl http://192.168.1.92:11434/api/tags
```

**If any fail:**
- Check firewall settings (see [Network Configuration](#network-configuration))
- Verify Ollama is running: `ps aux | grep ollama`
- Check IP addresses are correct

---

### Step 5: Configure FlockParser

**Method 1: Auto-Discovery (Easiest)**

FlockParser automatically scans your local network for Ollama nodes.

```bash
# Just run FlockParser
python flockparsecli.py

# It will find nodes automatically
# Check with:
> lb_stats
```

**Method 2: Manual Configuration**

If auto-discovery doesn't work, manually specify nodes:

```bash
# Edit flockparsecli.py (around line 150)
NODES = [
    {"url": "http://192.168.1.90:11434"},
    {"url": "http://192.168.1.91:11434"},
    {"url": "http://192.168.1.92:11434"},
]
```

**Method 3: GPU Router (Advanced)**

For automatic GPU optimization:

```bash
# Edit gpu_router_config.yaml
nodes:
  - http://192.168.1.90:11434
  - http://192.168.1.91:11434
  - http://192.168.1.92:11434

priority_models:
  - mxbai-embed-large
  - llama3.1:latest

auto_optimize: true
```

Then run the GPU router daemon:

```bash
python gpu_router_daemon.py
```

See [GPU_ROUTER_SETUP.md](GPU_ROUTER_SETUP.md) for details.

---

## Node Discovery Methods

FlockParser discovers nodes in 3 ways:

### 1. Local Network Scan (Default)

```python
# Scans your local network (e.g., 192.168.1.0/24)
# Checks common port 11434
# Returns nodes that respond
```

**Pros:** Fully automatic, no configuration
**Cons:** Slower (scans ~254 IPs), requires same subnet

### 2. Manual Node List

```python
NODES = [
    {"url": "http://192.168.1.90:11434"},
    {"url": "http://10.0.0.50:11434"},
]
```

**Pros:** Fast, works across subnets
**Cons:** Manual maintenance

### 3. DNS/Hostnames

```python
NODES = [
    {"url": "http://gpu-node-1.local:11434"},
    {"url": "http://gpu-node-2.local:11434"},
]
```

**Pros:** Survives IP changes (DHCP)
**Cons:** Requires DNS setup or /etc/hosts

---

## Network Configuration

### Firewall Configuration

**On each Ollama node, allow incoming port 11434:**

#### Linux (UFW)

```bash
sudo ufw allow 11434/tcp
sudo ufw reload
```

#### Linux (firewalld)

```bash
sudo firewall-cmd --permanent --add-port=11434/tcp
sudo firewall-cmd --reload
```

#### macOS

```bash
# macOS typically allows local network by default
# If blocked, add rule in System Preferences → Security & Privacy → Firewall → Options
```

#### Windows

```powershell
# Open Windows Firewall
# Add inbound rule for port 11434 TCP
New-NetFirewallRule -DisplayName "Ollama" -Direction Inbound -LocalPort 11434 -Protocol TCP -Action Allow
```

---

### Network Binding

**Make sure Ollama binds to all interfaces, not just localhost:**

#### Option 1: Environment Variable (Temporary)

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

#### Option 2: Shell Profile (Permanent)

```bash
# Linux/macOS
echo 'export OLLAMA_HOST=0.0.0.0:11434' >> ~/.bashrc
source ~/.bashrc

# Or for zsh
echo 'export OLLAMA_HOST=0.0.0.0:11434' >> ~/.zshrc
source ~/.zshrc
```

#### Option 3: Systemd Service (Linux)

```bash
# Create override
sudo systemctl edit ollama

# Add these lines:
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"

# Restart
sudo systemctl restart ollama
```

---

### Verify Network Access

**From main machine:**

```bash
# Test basic connectivity
ping 192.168.1.90

# Test Ollama API
curl http://192.168.1.90:11434/api/tags

# Test inference
curl http://192.168.1.90:11434/api/generate -d '{
  "model": "llama3.1:latest",
  "prompt": "Hello",
  "stream": false
}'
```

**Expected response:**
```json
{
  "model": "llama3.1:latest",
  "response": "Hello! How can I assist you today?",
  ...
}
```

---

## Verification

### Check Node Discovery

```bash
python flockparsecli.py

# In CLI
> lb_stats

# Expected output:
🎯 LOAD BALANCER STATUS
======================================================================
📊 Current Routing Strategy: ADAPTIVE

🖥️  Available Nodes: 3

✅ Node 1: http://192.168.1.90:11434
   Status: Healthy
   Health Score: 367
   Features: GPU (16384MB VRAM), Fast response (45ms)

✅ Node 2: http://192.168.1.91:11434
   Status: Healthy
   Health Score: 210
   Features: GPU (4096MB VRAM), Medium response (78ms)

✅ Node 3: http://192.168.1.92:11434
   Status: Healthy
   Health Score: 50
   Features: CPU-only, Slow response (120ms)
```

---

### Test Distributed Processing

```bash
# In FlockParser CLI
> open_pdf testpdfs/sample.pdf

# Watch timing:
# Single node: ~60 seconds
# 2 nodes: ~30 seconds
# 3 nodes with GPU: ~10 seconds
```

---

### Monitor Network Traffic

```bash
# On main machine, watch requests
sudo tcpdump -i any port 11434 -n

# You should see traffic to all nodes
```

---

## Troubleshooting

### Problem: "No nodes discovered"

**Symptoms:**
```
⚠️  Warning: No Ollama nodes discovered
Using localhost:11434 as fallback
```

**Solutions:**

1. **Check Ollama is running on nodes:**
   ```bash
   ssh user@192.168.1.90 "ps aux | grep ollama"
   ```

2. **Verify network binding:**
   ```bash
   ssh user@192.168.1.90 "netstat -tuln | grep 11434"
   # Should show: 0.0.0.0:11434 (not 127.0.0.1:11434)
   ```

3. **Test from main machine:**
   ```bash
   curl http://192.168.1.90:11434/api/tags
   ```

4. **Check firewall:**
   ```bash
   # Try disabling temporarily (for testing only!)
   sudo ufw disable  # Linux
   # Or add explicit rule
   sudo ufw allow from 192.168.1.0/24 to any port 11434
   ```

5. **Use manual node list:**
   Edit `flockparsecli.py` and add nodes manually.

---

### Problem: "Connection refused"

**Symptoms:**
```
ConnectionError: Failed to connect to http://192.168.1.90:11434
```

**Solutions:**

1. **Check Ollama is listening on 0.0.0.0:**
   ```bash
   # On the node
   sudo netstat -tuln | grep 11434
   # Should show: 0.0.0.0:11434
   # NOT: 127.0.0.1:11434
   ```

2. **Restart Ollama with correct binding:**
   ```bash
   pkill ollama
   OLLAMA_HOST=0.0.0.0:11434 ollama serve
   ```

---

### Problem: "Slow performance, not using GPU"

**Symptoms:**
- Processing takes same time with multiple nodes
- GPU nodes showing CPU usage

**Solutions:**

1. **Check GPU detection:**
   ```bash
   # In FlockParser CLI
   > lb_stats
   # Look for "GPU (XXXX MB VRAM)" on each node
   ```

2. **Verify VRAM monitoring:**
   ```bash
   # On GPU node
   curl http://192.168.1.90:11434/api/ps
   # Check "size_vram" field
   ```

3. **Use GPU router:**
   ```bash
   python gpu_router_daemon.py --report-only
   # Shows which models are on GPU
   ```

4. **Manually load model to GPU:**
   ```bash
   # On GPU node
   ollama run mxbai-embed-large "test"
   # This forces model to GPU
   ```

---

### Problem: "Nodes dropping offline"

**Symptoms:**
- Health score drops suddenly
- Requests timing out

**Solutions:**

1. **Check node health:**
   ```bash
   # On node machine
   top  # Check CPU/memory usage
   nvidia-smi  # Check GPU usage (if applicable)
   ```

2. **Check network latency:**
   ```bash
   ping 192.168.1.90
   # Should be <10ms on LAN
   ```

3. **Review Ollama logs:**
   ```bash
   # On node
   journalctl -u ollama -f  # If using systemd
   # Or check console output if running manually
   ```

4. **Restart node:**
   ```bash
   pkill ollama
   ollama serve
   ```

---

## Example Setups

### Example 1: Home Lab (Budget Build)

**Hardware:**
- Node 1: Old gaming PC (GTX 1060 6GB) - $200 used
- Node 2: Raspberry Pi 4 (8GB) - $75
- Node 3: Laptop (Intel i5, no GPU) - $300 used

**Result:** ~5-10x speedup over single node

```bash
# Node 1 (GTX 1060)
OLLAMA_HOST=0.0.0.0:11434 ollama serve
ollama pull mxbai-embed-large
ollama pull llama3.2:3b

# Node 2 (Raspberry Pi - CPU only)
OLLAMA_HOST=0.0.0.0:11434 ollama serve
ollama pull mxbai-embed-large  # Small model only

# Node 3 (Laptop)
OLLAMA_HOST=0.0.0.0:11434 ollama serve
ollama pull llama3.1:latest
```

---

### Example 2: Professional Setup (High Performance)

**Hardware:**
- Node 1: Workstation (RTX 4090 24GB) - $2500
- Node 2: Server (RTX A4000 16GB) - $1200
- Node 3: Server (RTX A4000 16GB) - $1200

**Result:** 60x+ speedup, 100+ concurrent users

```bash
# All nodes
OLLAMA_HOST=0.0.0.0:11434 ollama serve

# Pull all models on all nodes
ollama pull mxbai-embed-large
ollama pull llama3.1:latest
ollama pull llama3.2:70b  # Large model

# Use GPU router for optimization
python gpu_router_daemon.py
```

---

### Example 3: Mixed Cloud/Local

**Hardware:**
- Node 1: Local GPU workstation (RTX 3090)
- Node 2: Cloud VM with GPU (AWS g4dn.xlarge)
- Node 3: Local laptop (CPU fallback)

**Setup:**

```bash
# Node 1 (Local)
OLLAMA_HOST=0.0.0.0:11434 ollama serve

# Node 2 (Cloud - requires VPN or Tailscale)
# Install Tailscale for secure connection
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up
OLLAMA_HOST=0.0.0.0:11434 ollama serve

# Node 3 (Local)
OLLAMA_HOST=0.0.0.0:11434 ollama serve

# Configure with Tailscale IPs
NODES = [
    {"url": "http://192.168.1.90:11434"},    # Local
    {"url": "http://100.64.x.x:11434"},      # Tailscale IP
    {"url": "http://192.168.1.92:11434"},    # Local
]
```

---

## Next Steps

After setting up your distributed cluster:

1. **Monitor performance:**
   ```bash
   # In FlockParser CLI
   > lb_stats  # Check node health
   ```

2. **Optimize routing:**
   - Read [GPU_ROUTER_SETUP.md](GPU_ROUTER_SETUP.md)
   - Set up automatic GPU optimization
   - Configure priority models

3. **Scale up:**
   - Add more nodes as needed
   - Experiment with different hardware mixes
   - Test different workloads

4. **Production hardening:**
   - Set up monitoring (Prometheus/Grafana)
   - Configure systemd services for auto-start
   - Implement failover strategies

---

## Related Documentation

- [GPU_ROUTER_SETUP.md](GPU_ROUTER_SETUP.md) - GPU optimization and routing
- [VRAM_MONITORING.md](VRAM_MONITORING.md) - VRAM tracking
- [PERFORMANCE_OPTIMIZATION.md](PERFORMANCE_OPTIMIZATION.md) - Tuning tips
- [ERROR_HANDLING.md](ERROR_HANDLING.md) - Troubleshooting
- [docs/architecture.md](docs/architecture.md) - System design details

---

## Need Help?

- 🐛 [Report an issue](https://github.com/BenevolentJoker-JohnL/FlockParser/issues)
- 💬 [Discussions](https://github.com/BenevolentJoker-JohnL/FlockParser/discussions)
- 📖 [Full Documentation](README.md)
