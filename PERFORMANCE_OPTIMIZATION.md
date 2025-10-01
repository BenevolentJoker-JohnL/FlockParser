# 🚀 Performance Optimization Guide

## Overview

This guide helps you optimize FlockParse for maximum performance, covering retrieval quality, model management, and GPU utilization.

## Performance Issues & Solutions

### Issue 1: Slow Chat Responses

**Symptoms:**
- Chat taking 10-30+ seconds to respond
- High memory usage
- Multiple models loaded

**Root Causes:**
1. ❌ Multiple chat models loaded (llama3.1 + qwen2.5-coder = 8GB+)
2. ❌ Models running on CPU instead of GPU
3. ❌ Too many chunks retrieved for context

**Solutions:**

#### Unload Unused Models
```bash
⚡ Enter command: cleanup_models

🧹 Cleaning up non-priority models...
   Priority models: mxbai-embed-large, llama3.1:latest

📋 Found 1 non-priority models:
   - qwen2.5-coder:3b

⚠️  Unload these models? (yes/no): yes

✅ Cleanup complete!
```

**Result:** Frees 2.3GB RAM, reduces CPU contention

#### Move Embeddings to GPU
```bash
⚡ Enter command: force_gpu mxbai-embed-large

🚀 Forcing mxbai-embed-large to GPU on all nodes...
   ✅ http://10.9.66.124:11434: mxbai-embed-large now on GPU
```

**Result:** 5-10x faster embedding generation

#### Check Current Status
```bash
⚡ Enter command: vram_report

Node: http://localhost:11434
   llama3.1:latest: CPU (RAM) - 5.61GB
   mxbai-embed-large:latest: CPU (RAM) - 0.69GB

Node: http://10.9.66.124:11434
   mxbai-embed-large:latest: GPU (VRAM) - 0.69GB ✅
```

### Issue 2: Poor Retrieval Quality

**Symptoms:**
- Only 3 document chunks returned
- Missing relevant information
- Generic/incomplete responses

**Root Cause:**
- Default `top_k=3` was too low
- No similarity threshold filtering

**Solution:**

#### New Configuration (lines 61-65 in flockparsecli.py)
```python
# 📊 RAG CONFIGURATION
RETRIEVAL_TOP_K = 10          # Number of chunks to retrieve (default: 10)
RETRIEVAL_MIN_SIMILARITY = 0.3  # Minimum similarity score (0.0-1.0)
CHUNKS_TO_SHOW = 5            # Number of source chunks to display
```

**Adjust for your needs:**

| Use Case | top_k | min_similarity |
|----------|-------|----------------|
| **Quick answers** | 5 | 0.4 |
| **Balanced (default)** | 10 | 0.3 |
| **Comprehensive** | 20 | 0.2 |
| **Deep research** | 50 | 0.1 |

**Before (3 chunks):**
```
🔍 Searching knowledge base...
📚 Sources:
  1. vacuum_energy.pdf (relevance: 0.52)
  2. neutron_stars.pdf (relevance: 0.49)
  3. neutron_stars.pdf (relevance: 0.49)
```

**After (10 chunks):**
```
🔍 Searching knowledge base...
   Found 10 relevant chunks (similarity >= 0.30)
📚 Sources:
  1. vacuum_energy.pdf (relevance: 0.52)
  2. neutron_stars.pdf (relevance: 0.49)
  3. dark_matter.pdf (relevance: 0.48)
  4. cosmology.pdf (relevance: 0.45)
  5. quantum_fields.pdf (relevance: 0.42)
```

### Issue 3: Multiple Chat Models Loaded

**Symptoms:**
```bash
llama3.1:latest: CPU (RAM) - 5.61GB
qwen2.5-coder:3b: CPU (RAM) - 2.28GB  ← Unwanted
```

**Causes:**
- Testing different models
- Previous sessions didn't unload
- API loaded different model

**Solutions:**

#### Manual Unload
```bash
⚡ Enter command: unload_model qwen2.5-coder:3b

🗑️  Unloading qwen2.5-coder:3b from all nodes...
   ✅ http://localhost:11434: Unloaded qwen2.5-coder:3b
```

#### Automatic Cleanup
```bash
⚡ Enter command: cleanup_models
```

This keeps only `EMBEDDING_MODEL` and `CHAT_MODEL` loaded.

## Optimization Workflow

### 1. Initial Setup (One-Time)

```bash
# Configure GPU node (run on GPU server)
cd /path/to/FlockParser
./fix_gpu_node.sh

# Start FlockParse CLI
python3 flockparsecli.py

# Check cluster status
⚡ Enter command: gpu_status

# Move embeddings to GPU
⚡ Enter command: force_gpu mxbai-embed-large

# Clean up unused models
⚡ Enter command: cleanup_models
```

### 2. Before Chat Session (Quick Check)

```bash
# Check what's loaded
⚡ Enter command: vram_report

# If unwanted models loaded, clean up
⚡ Enter command: cleanup_models
```

### 3. Adjust Retrieval Quality

Edit `flockparsecli.py` lines 61-65:

**For faster responses (less context):**
```python
RETRIEVAL_TOP_K = 5
RETRIEVAL_MIN_SIMILARITY = 0.5
CHUNKS_TO_SHOW = 3
```

**For better quality (more context):**
```python
RETRIEVAL_TOP_K = 20
RETRIEVAL_MIN_SIMILARITY = 0.2
CHUNKS_TO_SHOW = 10
```

### 4. Monitor Performance

```bash
# View load balancer stats
⚡ Enter command: lb_stats

# Check GPU utilization
⚡ Enter command: gpu_status

# Verify routing decisions
⚡ Enter command: gpu_route llama3.1:latest
```

## Performance Benchmarks

### Embedding Generation

| Configuration | Speed | Use Case |
|--------------|-------|----------|
| **CPU (RAM)** | 100ms/chunk | Fallback |
| **GPU (VRAM) 1050Ti** | 10-20ms/chunk | 5-10x faster! ✅ |
| **GPU (VRAM) RTX 3080** | 5-10ms/chunk | 10-20x faster! ✅ |

### Chat Response Time

| Configuration | Time | Notes |
|--------------|------|-------|
| **1 model, CPU** | 5-10s | Baseline |
| **2 models, CPU** | 15-30s | ❌ High RAM contention |
| **1 model, GPU** | 2-5s | ✅ Ideal |

**Calculation for 7 documents:**
- 7 docs × 10 chunks each = 70 chunks
- CPU: 70 × 100ms = 7 seconds (just for embeddings!)
- GPU: 70 × 15ms = 1 second ✅

### Memory Usage

| Component | CPU | GPU (1050Ti) |
|-----------|-----|-------------|
| mxbai-embed-large | 690MB RAM | 690MB VRAM |
| llama3.1:latest | 5.6GB RAM | Too large (4.7GB > 3.2GB usable) |
| qwen2.5-coder:3b | 2.3GB RAM | 1.9GB VRAM (fits!) |

## Best Practices

### 1. Prioritize Embedding Model on GPU

**Why:** Used constantly for search queries
```bash
⚡ Enter command: force_gpu mxbai-embed-large
```

### 2. Keep Only Necessary Models Loaded

**Why:** Reduces memory pressure and CPU contention
```bash
⚡ Enter command: cleanup_models  # Run weekly
```

### 3. Use Appropriate Retrieval Settings

**Quick Q&A:**
```python
RETRIEVAL_TOP_K = 5
RETRIEVAL_MIN_SIMILARITY = 0.5
```

**Research:**
```python
RETRIEVAL_TOP_K = 20
RETRIEVAL_MIN_SIMILARITY = 0.2
```

### 4. Monitor GPU Utilization

**Check regularly:**
```bash
⚡ Enter command: gpu_status
⚡ Enter command: vram_report
```

### 5. Use Smaller Chat Models on GPU Nodes

**If node has limited VRAM (4GB):**
```python
CHAT_MODEL = "llama3.2:3b"  # 1.9GB - fits!
# Instead of:
# CHAT_MODEL = "llama3.1:latest"  # 4.7GB - too large
```

**Edit in flockparsecli.py:**
```python
# Line 54
CHAT_MODEL = "llama3.2:3b"
```

Then restart:
```bash
# Stop current session
⚡ Enter command: exit

# Restart
python3 flockparsecli.py
```

## Troubleshooting

### Chat Still Slow After Optimization

**Check what's actually loaded:**
```bash
curl http://localhost:11434/api/ps | jq
```

**Look for:**
1. Multiple chat models
2. `size_vram: 0` (means CPU, not GPU)
3. Large total memory usage

**Solutions:**
```bash
# Unload everything
⚡ Enter command: cleanup_models

# Force embeddings to GPU
⚡ Enter command: force_gpu mxbai-embed-large

# Verify
⚡ Enter command: vram_report
```

### GPU Not Being Used

**Symptoms:**
```
mxbai-embed-large:latest: CPU (RAM) - 0.69GB
```

**Should be:**
```
mxbai-embed-large:latest: GPU (VRAM) - 0.69GB
```

**Fix:**
```bash
# On GPU node, run:
./fix_gpu_node.sh

# Then from CLI:
⚡ Enter command: force_gpu mxbai-embed-large
```

### Retrieval Missing Documents

**Check number of chunks:**
```bash
⚡ Enter command: list_docs

📚 Processed Documents:
Document: vacuum_energy.pdf
   Chunks: 15  ← Should see chunk count
```

**Increase retrieval:**
```python
# In flockparsecli.py
RETRIEVAL_TOP_K = 20  # Increase from 10
RETRIEVAL_MIN_SIMILARITY = 0.2  # Lower threshold
```

### Models Not Unloading

**Check if process is stuck:**
```bash
curl http://localhost:11434/api/ps
```

**Force restart Ollama:**
```bash
sudo systemctl restart ollama
```

## Advanced Optimization

### Dedicated GPU Node Strategy

**If you have multiple nodes:**

1. **Embeddings → GPU node only**
   ```bash
   # Unload from CPU nodes
   curl http://localhost:11434/api/embed \
     -d '{"model": "mxbai-embed-large", "input": "x", "keep_alive": 0}'

   # Force on GPU node
   ⚡ Enter command: force_gpu mxbai-embed-large
   ```

2. **Chat → Distributed across all nodes**
   ```bash
   # Load balancer will distribute automatically
   ⚡ Enter command: lb_stats
   ```

### Intelligent Routing Automation

**Use GPU router daemon for automatic optimization:**

```bash
# Install daemon
./install_gpu_router.sh

# Configure priority
sudo nano /opt/gpu-router/gpu_router_config.yaml
```

```yaml
priority_models:
  - mxbai-embed-large  # Always on GPU
  - llama3.2:3b        # On GPU if fits
```

**Daemon will automatically:**
- Move embeddings to GPU
- Keep large models on CPU
- Recover from node restarts

## Performance Checklist

Before each session:

- [ ] Run `cleanup_models` to remove unused models
- [ ] Check `vram_report` for GPU utilization
- [ ] Verify embeddings on GPU (`force_gpu mxbai-embed-large`)
- [ ] Monitor `lb_stats` for load distribution

Weekly maintenance:

- [ ] Review loaded models (`vram_report`)
- [ ] Clean up old embeddings (`clear_cache`)
- [ ] Check GPU router daemon logs (if using)
- [ ] Test chat response times

## Configuration Reference

### Retrieval Settings (flockparsecli.py)

```python
# Lines 61-65

# 📊 RAG CONFIGURATION
RETRIEVAL_TOP_K = 10          # ← Adjust this (5-50)
RETRIEVAL_MIN_SIMILARITY = 0.3  # ← Adjust this (0.1-0.7)
CHUNKS_TO_SHOW = 5            # ← Adjust this (3-10)
```

### Model Settings (flockparsecli.py)

```python
# Lines 53-59

# 🔥 AI MODELS
EMBEDDING_MODEL = "mxbai-embed-large"  # ← 705MB
CHAT_MODEL = "llama3.1:latest"         # ← 4.7GB (or use llama3.2:3b for 1.9GB)

# 🚀 MODEL CACHING CONFIGURATION
EMBEDDING_KEEP_ALIVE = "1h"   # Keep in memory 1 hour
CHAT_KEEP_ALIVE = "15m"       # Keep in memory 15 minutes
```

### GPU Router Settings (gpu_router_config.yaml)

```yaml
nodes:
  - http://localhost:11434
  - http://10.9.66.124:11434  # GPU node

priority_models:
  - mxbai-embed-large  # Always optimize

check_interval: 300  # Check every 5 minutes
auto_optimize: true  # Automatically move to GPU
```

## Summary

**Quick Wins (Do These First):**

1. ✅ Run `cleanup_models` - Remove unused models
2. ✅ Run `force_gpu mxbai-embed-large` - 5-10x faster embeddings
3. ✅ Increase `RETRIEVAL_TOP_K = 10` - Better quality (already done!)

**Expected Results:**
- Chat response: 5-10s → 2-5s (50% faster)
- Embedding quality: 3 chunks → 10 chunks (better context)
- Memory usage: 8.6GB → 6.3GB (26% reduction)

**Ongoing:**
- Monitor with `vram_report` and `lb_stats`
- Clean up with `cleanup_models` weekly
- Adjust `RETRIEVAL_TOP_K` based on needs

---

**Created:** 2025-09-30
**Version:** 1.0
**Performance Impact:** 2-5x faster with GPU optimization