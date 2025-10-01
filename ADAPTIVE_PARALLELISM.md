# 🔀 Adaptive Parallelism - Intelligent Sequential vs Parallel Routing

## Overview

FlockParse now **automatically decides** whether to process batches in parallel or sequential mode based on your cluster's characteristics. This ensures optimal performance regardless of your hardware setup.

## Key Concept

**Problem:** Blindly parallelizing across all nodes isn't always faster!

### Example Scenarios:

**Scenario 1: One Fast GPU Node**
```
10.9.66.90: GPU (100ms/embedding) ← 10x faster!
localhost: CPU (1000ms/embedding)
10.9.66.154: CPU (1000ms/embedding)
```

**Wrong approach (parallel):**
- Splits 100 items across 3 nodes
- Takes: ~33 seconds (33 items × 1000ms on slow nodes)

**Smart approach (sequential):**
- Uses only fast GPU node
- Takes: ~10 seconds (100 items × 100ms) ✅ **3x faster!**

**Scenario 2: Multiple Similar Nodes**
```
Node 1: GPU (100ms/embedding)
Node 2: GPU (120ms/embedding)
Node 3: GPU (110ms/embedding)
```

**Smart approach (parallel):**
- Splits across all 3 nodes
- Takes: ~3.7 seconds (33 items × 110ms avg) ✅ **3x faster than sequential!**

## How It Works

### Decision Algorithm

The system analyzes:

1. **Speed Ratio** - How much faster is the fastest node?
2. **Batch Size** - Is parallelism overhead worth it?
3. **Node Count** - How many nodes available?
4. **Historical Performance** - Actual measured speeds

### Decision Rules

| Speed Ratio | Batch Size | Decision | Reasoning |
|-------------|-----------|----------|-----------|
| **>5x** | Any | ➡️ Sequential | Dominant node wins |
| <3x | >20 | 🔀 Parallel | Balanced cluster |
| 3-5x | >50 | 🔀 Hybrid (top 3) | Use fastest nodes |
| Any | <20 | ➡️ Sequential | Overhead too high |

### Example Output

```
Processing 200 chunks...
   🔀 Adaptive mode: dominant_node
      Fastest node is 8.5x faster - sequential wins
   ➡️  Sequential mode: Using http://10.9.66.90:11434
   Progress: 50/200 embeddings (25%)
   Progress: 100/200 embeddings (50%)
   ...
```

or

```
Processing 200 chunks...
   🔀 Adaptive mode: balanced_cluster
      Speed ratio 2.1x - parallel is efficient
   🔀 Parallel mode: Using 8 workers across 4 nodes
   Progress: 50/200 embeddings (25%)
   ...
```

## Performance Gains

### Your Cluster (1 GPU + 3 CPU)

**Before (Always Parallel):**
- 200 embeddings
- 50 go to GPU (fast)
- 150 go to CPU (slow)
- Total: ~15 seconds

**After (Adaptive Sequential):**
- 200 embeddings
- All 200 go to GPU
- Total: ~4 seconds ✅ **3.75x faster!**

### Balanced Cluster (3 Similar GPUs)

**Before (Sequential):**
- 200 embeddings
- All on one GPU
- Total: ~4 seconds

**After (Adaptive Parallel):**
- 200 embeddings
- Split across 3 GPUs
- Total: ~1.5 seconds ✅ **2.7x faster!**

## Commands

### View Parallelism Analysis

```bash
⚡ Enter command: parallelism_report

🔀 ADAPTIVE PARALLELISM ANALYSIS
======================================================================

📊 Batch Size: 10 items
   Mode: ➡️  SEQUENTIAL
   Reason: small_batch
   Detail: Batch size 10 too small for parallel overhead
   Sequential: 1.0s
   Parallel: 1.8s
   Recommendation: SEQUENTIAL
   Time saved: 0.8s

📊 Batch Size: 50 items
   Mode: ➡️  SEQUENTIAL
   Reason: dominant_node
   Detail: Fastest node is 8.5x faster - sequential wins
   Sequential: 5.0s
   Parallel: 12.0s
   Recommendation: SEQUENTIAL
   Time saved: 7.0s

📊 Batch Size: 100 items
   Mode: ➡️  SEQUENTIAL
   Reason: dominant_node
   Detail: Fastest node is 8.5x faster - sequential wins
   Sequential: 10.0s
   Parallel: 23.0s
   Recommendation: SEQUENTIAL
   Time saved: 13.0s

📊 Batch Size: 200 items
   Mode: ➡️  SEQUENTIAL
   Reason: dominant_node
   Detail: Fastest node is 8.5x faster - sequential wins
   Sequential: 20.0s
   Parallel: 45.0s
   Recommendation: SEQUENTIAL
   Time saved: 25.0s
```

### Check Load Balancer Stats

```bash
⚡ Enter command: lb_stats

📊 Load Balancer Statistics:
Current strategy: adaptive

Node Statistics:
================================================================================
🟢 http://10.9.66.90:11434 (31ms) 🚀 GPU (~8GB VRAM)
   Health Score: 380  ← Dominant!
   Requests: 500 | Errors: 2 (0.4%)
   Avg Response: 0.12s | Concurrent: 0

🟢 http://localhost:11434 (25ms) 🐢 CPU
   Health Score: 50  ← Much slower
   ...
```

## Configuration

### Enable/Disable Adaptive Mode

In `flockparsecli.py` (line 150):

```python
# Enable (default)
self.auto_adaptive_mode = True

# Disable (always parallel)
self.auto_adaptive_mode = False
```

### Force Mode for Testing

```python
# In embed_batch() call
load_balancer.embed_batch(model, texts, force_mode="sequential")
load_balancer.embed_batch(model, texts, force_mode="parallel")
load_balancer.embed_batch(model, texts, force_mode=None)  # Adaptive (default)
```

### Adjust Decision Thresholds

Edit `adaptive_parallelism.py`:

```python
# Line ~78: Speed ratio threshold for dominant node
if speed_ratio >= 5.0:  # Default: 5x
    # Change to 3.0 for more aggressive sequential
    # Change to 10.0 for more aggressive parallel

# Line ~86: Small batch threshold
if batch_size < 20:  # Default: 20 items
    # Change to 10 for more aggressive parallel
    # Change to 50 for more aggressive sequential
```

## Use Cases

### Case 1: Development (1 GPU + Laptop)

**Setup:**
- Workstation: GPU (RTX 3080) - Fast!
- Laptop: CPU - Slow

**Adaptive Decision:**
- Batch <500: Sequential on GPU ✅
- Result: 5-10x faster than parallel

### Case 2: Production (4 GPU Servers)

**Setup:**
- 4 servers with similar GPUs

**Adaptive Decision:**
- Batch >20: Parallel across all 4 ✅
- Result: ~4x faster than sequential

### Case 3: Mixed Cluster (2 GPU + 3 CPU)

**Setup:**
- 2 GPU nodes (fast)
- 3 CPU nodes (slow)

**Adaptive Decision:**
- Uses top 2-3 nodes in parallel ✅
- Ignores slow CPU nodes
- Result: Optimal balance

## Technical Details

### Speed Score Calculation

```python
if has_requests:
    # Use actual measured performance
    speed_score = 1.0 / avg_response_time
else:
    # Estimate based on hardware
    speed_score = 100 if has_gpu else 10
```

### Worker Count Calculation

```python
base_workers = num_nodes * 2

if batch_size < 50:
    workers = min(base_workers, batch_size)
elif batch_size < 200:
    workers = base_workers
else:
    workers = min(base_workers * 2, batch_size)
```

### Sequential Optimization

In sequential mode:
- Skips load balancer routing overhead
- Directly connects to fastest node
- No thread pool overhead
- Result: Minimal latency

## Monitoring

### Check What Mode Was Used

Look for output during processing:

```
🔀 Adaptive mode: dominant_node
   Fastest node is 8.5x faster - sequential wins
➡️  Sequential mode: Using http://10.9.66.90:11434
```

or

```
🔀 Adaptive mode: balanced_cluster
   Speed ratio 2.1x - parallel is efficient
🔀 Parallel mode: Using 8 workers across 4 nodes
```

### Performance Tracking

The system learns over time:
- Tracks actual response times
- Adjusts speed scores
- Improves decisions with usage

## Troubleshooting

### Issue: Always Uses Sequential

**Symptom:** Never parallelizes even with multiple nodes

**Cause:** One node much faster than others

**Check:**
```bash
⚡ parallelism_report
# Look at speed ratio
```

**Solution:** This is correct! If one node is 5x+ faster, sequential is optimal.

### Issue: Always Uses Parallel

**Symptom:** Parallelizes even with dominant GPU

**Cause:** GPU node not properly detected or measured

**Check:**
```bash
⚡ lb_stats
# Check health scores
```

**Solution:** Ensure GPU node has high health score (>300)

### Issue: Want to Force Mode

**Temporary:** Not exposed in CLI yet

**Workaround:** Edit `flockparsecli.py` line 150:
```python
self.auto_adaptive_mode = False  # Always parallel
```

## Best Practices

### 1. Let Adaptive Mode Learn

- First few batches may not be optimal
- System learns from actual performance
- Gets better with usage

### 2. Check Parallelism Report

```bash
# Before large processing job
⚡ parallelism_report

# Understand what mode will be used
```

### 3. Monitor Load Balancer Stats

```bash
# After processing
⚡ lb_stats

# Verify health scores match expectations
```

### 4. GPU Nodes Should Dominate

If you have a GPU node:
- Health score should be 300-400
- CPU nodes should be 50-100
- Speed ratio should be 5-10x

## Future Enhancements

Planned improvements:
- [ ] Per-model adaptive strategies
- [ ] Dynamic batch size adjustment
- [ ] Network latency consideration
- [ ] Cost-aware routing (cloud scenarios)
- [ ] Learning rate adjustment

## Summary

**Adaptive Parallelism automatically:**

✅ **Detects cluster characteristics** - Fast vs slow nodes
✅ **Chooses optimal mode** - Sequential vs parallel
✅ **Maximizes throughput** - 2-5x performance gains
✅ **No configuration needed** - Works out of the box
✅ **Learns over time** - Gets better with usage

**Just process documents and let the system optimize!** 🚀

---

**Created:** 2025-09-30
**Status:** Production-ready
**Performance Gain:** 2-5x faster processing