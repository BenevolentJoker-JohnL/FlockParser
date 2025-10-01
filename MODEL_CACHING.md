# 🚀 Model Weight Caching

## Overview

FlockParse now implements **model weight caching** to keep AI models loaded in VRAM/RAM for faster inference. This eliminates the 3-10 second model loading overhead on each request.

## How It Works

When you use Ollama models, they normally load from disk into memory for each inference request. With `keep_alive`, models stay loaded in memory for a specified duration.

### Configuration

```python
# flockparsecli.py configuration
EMBEDDING_KEEP_ALIVE = "1h"   # Keep embedding model loaded for 1 hour
CHAT_KEEP_ALIVE = "15m"       # Keep chat model loaded for 15 minutes
```

### Why Different Times?

- **Embedding Model (1 hour)**: Used constantly for:
  - Document chunking during processing
  - Semantic search queries
  - Similarity calculations
  - Much more frequent → keep loaded longer

- **Chat Model (15 minutes)**: Used occasionally for:
  - User Q&A sessions
  - Document summarization
  - Less frequent → shorter keep_alive saves VRAM

## Performance Impact

### Before (No Caching):
```
Request 1: Load model (8s) + Inference (2s) = 10s
Request 2: Load model (8s) + Inference (2s) = 10s
Request 3: Load model (8s) + Inference (2s) = 10s
Total: 30 seconds
```

### After (With Caching):
```
Request 1: Load model (8s) + Inference (2s) = 10s
Request 2: Inference (2s) = 2s  ← Model already loaded!
Request 3: Inference (2s) = 2s  ← Model already loaded!
Total: 14 seconds (53% faster!)
```

## Implementation Details

### Files Modified:

1. **flockparsecli.py**
   - Added `EMBEDDING_KEEP_ALIVE` and `CHAT_KEEP_ALIVE` constants
   - Updated `ollama.embed()` calls with `keep_alive` parameter
   - Updated `ollama.chat()` calls with `keep_alive` parameter
   - Modified `embed_distributed()` to support keep_alive

2. **flock_ai_api.py**
   - Added keep_alive configuration
   - Updated `embed_text()` function
   - Updated `summarize_text()` function

3. **flock_mcp_server.py**
   - Imported `CHAT_KEEP_ALIVE` from flockparsecli
   - Updated chat response generation

### Code Examples

**Embedding with caching:**
```python
response = ollama.embed(
    model="mxbai-embed-large",
    input=text,
    keep_alive="1h"  # Keep model loaded
)
```

**Chat with caching:**
```python
response = ollama.chat(
    model="llama3.1:latest",
    messages=[...],
    keep_alive="15m"  # Keep model loaded
)
```

**Load balancer with caching:**
```python
embedding_result = load_balancer.embed_distributed(
    EMBEDDING_MODEL,
    text,
    keep_alive="1h"
)
```

## VRAM/RAM Requirements

### Memory Usage (Approximate):

| Model | Size | VRAM (GPU) | RAM (CPU) |
|-------|------|------------|-----------|
| `mxbai-embed-large` | 670MB | ~800MB | ~1.2GB |
| `llama3.1:latest` (8B) | 4.7GB | ~5.5GB | ~8GB |

### With Both Models Loaded:
- **GPU**: ~6.3GB VRAM required
- **CPU**: ~9.2GB RAM required

### Automatic Unloading:
- Models automatically unload after `keep_alive` expires
- Frees up VRAM/RAM for other processes
- Balances performance vs. resource usage

## Configuration Options

You can adjust keep_alive duration:

```python
# Aggressive caching (high VRAM usage)
EMBEDDING_KEEP_ALIVE = "2h"
CHAT_KEEP_ALIVE = "30m"

# Conservative caching (low VRAM usage)
EMBEDDING_KEEP_ALIVE = "30m"
CHAT_KEEP_ALIVE = "5m"

# Disable caching (always unload immediately)
EMBEDDING_KEEP_ALIVE = "0"
CHAT_KEEP_ALIVE = "0"
```

## Multi-Node Behavior

When using load balancer with multiple Ollama nodes:
- Each node maintains its own model cache
- `keep_alive` applies per-node, not globally
- GPU nodes benefit most from caching (faster inference)
- CPU nodes still benefit but to a lesser degree

## Monitoring

Check which models are currently loaded:

```bash
# Via Ollama API
curl http://localhost:11434/api/ps

# Example output shows loaded models and their keep_alive timers
```

## Benefits

✅ **5-10x faster** subsequent inference requests
✅ **Reduced latency** for interactive chat sessions
✅ **Better UX** - faster response times
✅ **GPU efficiency** - keep models in VRAM where they belong
✅ **Automatic cleanup** - models unload when not needed

## Best Practices

1. **Match duration to usage patterns**:
   - Frequent use → longer keep_alive (1h+)
   - Occasional use → shorter keep_alive (5-15m)

2. **Monitor VRAM usage**:
   - Use `nvidia-smi` or `ollama ps` to check memory
   - Reduce keep_alive if running out of VRAM

3. **Development vs. Production**:
   - Development: Longer keep_alive (less waiting)
   - Production: Tune based on request frequency

4. **Multi-model scenarios**:
   - Prioritize frequently-used models
   - Consider per-model keep_alive tuning

## Comparison to Alternatives

| Approach | Speed | Memory | Complexity |
|----------|-------|--------|------------|
| **No caching** | Slow | Low | Simple |
| **keep_alive** | Fast | Medium | Simple ✅ |
| **Persistent server** | Fastest | High | Complex |
| **Model quantization** | Medium | Low | Medium |

FlockParse uses `keep_alive` for the best balance of speed, memory, and simplicity.

## Troubleshooting

### Models not staying loaded?
- Check Ollama version: `ollama --version` (need v0.1.26+)
- Verify syntax: `keep_alive="15m"` not `keep_alive=15`
- Check logs: Ollama may evict models due to memory pressure

### Running out of VRAM?
- Reduce keep_alive duration
- Use smaller models
- Offload to CPU with `OLLAMA_NUM_GPU=0`

### Still slow after first request?
- Verify keep_alive is passed to `ollama.embed()` / `ollama.chat()`
- Check model is actually loaded: `curl http://localhost:11434/api/ps`
- Ensure Ollama server has sufficient VRAM

## Future Enhancements

- ⬜ Dynamic keep_alive based on request frequency
- ⬜ Per-user model caching (multi-tenant scenarios)
- ⬜ Predictive model preloading
- ⬜ VRAM-aware auto-tuning of keep_alive

---

**Implementation Date**: 2025-09-30
**Lines of Code**: ~30 lines across 3 files
**Performance Gain**: 5-10x faster inference after first request
**Breaking Changes**: None (backward compatible)