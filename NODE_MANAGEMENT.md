# 📡 Node Management - Optional & Offline Handling

## Overview

FlockParse now intelligently handles nodes that are offline or temporarily unavailable. Nodes are **optional** - the system will automatically route around offline nodes.

## Key Features

### ✅ Automatic Offline Detection
- Nodes checked for availability before each request
- Offline nodes get health score of 0
- Only online nodes considered for routing

### ✅ Graceful Degradation
- System continues working even if nodes go down
- Automatic failover to available nodes
- No manual intervention needed

### ✅ Optional Node Addition
- Saved nodes loaded as "optional" at startup
- Can add nodes even if currently offline
- Will be used when they come online

## How It Works

### Startup Behavior

```
Loading saved nodes...
  http://10.9.66.90:11434  - ✅ ONLINE → Added
  http://10.9.66.124:11434 - ⚠️  OFFLINE → Added as optional
  http://10.9.66.154:11434 - ✅ ONLINE → Added
```

**Result:** All nodes added, offline nodes will be skipped until available

### Runtime Behavior

```
User requests embedding...
  1. Check which nodes are online (2s timeout)
  2. Calculate health scores for online nodes only
  3. Route to best available node
  4. If node fails, try next best node
```

**Result:** Seamless routing around offline nodes

## Commands

### Check Node Status

```bash
⚡ Enter command: list_nodes

🌐 Configured Ollama Nodes:
------------------------------------------------------------
1. http://localhost:11434 - 🟢 ONLINE - Active
   Requests: 150, Errors: 0 (0.0%)
   Avg Response Time: 0.45s

2. http://10.9.66.90:11434 - 🟢 ONLINE - Active
   Requests: 500, Errors: 2 (0.4%)
   Avg Response Time: 0.12s

3. http://10.9.66.124:11434 - 🔴 OFFLINE - Unused

4. http://10.9.66.154:11434 - 🟢 ONLINE - Unused
------------------------------------------------------------
```

### Add Optional Node

```bash
# Add node that might be offline
⚡ Enter command: add_node http://10.9.66.200:11434

# If online:
✅ Added node: http://10.9.66.200:11434

# If offline:
⚠️  Node http://10.9.66.200:11434 currently offline, adding as optional
```

**Node will be checked at runtime and used when available**

### View Load Balancer Stats

```bash
⚡ Enter command: lb_stats

📊 Load Balancer Statistics:
Current strategy: adaptive

Node Statistics:
================================================================================
🟢 http://10.9.66.90:11434 (31ms) 🚀 GPU (~8GB VRAM)
   Health Score: 380
   Requests: 500 | Errors: 2 (0.4%)
   Avg Response: 0.12s | Concurrent: 0

🟢 http://localhost:11434 (25ms) 🐢 CPU
   Health Score: 50
   Requests: 150 | Errors: 0 (0.0%)
   Avg Response: 0.45s | Concurrent: 0

🔴 http://10.9.66.124:11434 (OFFLINE)
   Health Score: 0
   Status: Skipped (offline)

🟢 http://10.9.66.154:11434 (25ms) 🐢 CPU
   Health Score: 50
   Requests: 0 | Errors: 0 (0.0%)
   Status: Unused
```

**Offline nodes shown with 🔴 and health score 0**

## Configuration

### Node Persistence

Nodes are saved to `ollama_nodes.json`:

```json
[
  "http://localhost:11434",
  "http://10.9.66.90:11434",
  "http://10.9.66.124:11434",
  "http://10.9.66.154:11434"
]
```

**At startup:** All saved nodes loaded as optional (offline ones added but skipped)

### Health Scoring

```python
# Online nodes
if node_online:
    score = 100 + GPU_bonus + VRAM_bonus - penalties
    # GPU node: ~380
    # CPU node: ~50

# Offline nodes
if node_offline:
    score = 0  # Never selected
```

**Result:** Offline nodes automatically excluded from routing

## Use Cases

### Case 1: Temporary Node Shutdown

**Scenario:** GPU node rebooting for updates

```
Before reboot:
  10.9.66.90: 🟢 ONLINE (handling 70% of traffic)

During reboot:
  10.9.66.90: 🔴 OFFLINE (automatically skipped)
  Traffic routes to: localhost + 10.9.66.154

After reboot:
  10.9.66.90: 🟢 ONLINE (automatically resumes handling 70%)
```

**No intervention needed!**

### Case 2: Network Issues

**Scenario:** Remote node unreachable due to network

```
Embedding request arrives...
  1. Check 10.9.66.90 → Timeout (2s)
  2. Mark as offline, score = 0
  3. Route to next best: localhost
  4. Request succeeds

Next request (5 min later):
  1. Check 10.9.66.90 → Online!
  2. Mark as online, score = 380
  3. Route to 10.9.66.90 (best node)
```

**Automatic recovery when network restored**

### Case 3: Optional Development Nodes

**Scenario:** You have extra nodes that aren't always on

```bash
# Add nodes that come/go
⚡ add_node http://10.9.66.200:11434
⚡ add_node http://10.9.66.201:11434

# Both currently offline
⚠️  Node http://10.9.66.200:11434 currently offline, adding as optional
⚠️  Node http://10.9.66.201:11434 currently offline, adding as optional

# Later, when they come online
# (automatic - no action needed)
# They'll be used in routing
```

**Nodes automatically incorporated when available**

## Troubleshooting

### Issue: All Nodes Showing Offline

**Check:**
```bash
⚡ list_nodes
```

**Possible causes:**
1. Network connectivity issues
2. Ollama not running on nodes
3. Firewall blocking port 11434

**Fix:**
```bash
# On each node, verify Ollama is running
sudo systemctl status ollama

# Test manually
curl http://10.9.66.90:11434/api/tags

# Check firewall
sudo ufw status
```

### Issue: Node Stuck as Offline

**Symptoms:** Node is up but showing as offline

**Cause:** Cached health score from previous check

**Fix:**
```bash
# Restart FlockParse CLI to re-check all nodes
⚡ exit
python3 flockparsecli.py
```

### Issue: Want to Force Check Node Status

**Solution:**
```bash
# list_nodes checks status in real-time
⚡ list_nodes

# Or lb_stats for detailed view
⚡ lb_stats
```

### Issue: Too Many Offline Checks Slowing Down

**Symptom:** Requests seem slow because checking many offline nodes

**Solution:** Remove permanently offline nodes:
```bash
⚡ remove_node http://10.9.66.124:11434
```

## Performance Impact

### Offline Detection Overhead

| Operation | Time | Frequency |
|-----------|------|-----------|
| **Online check** | ~10-50ms | Per routing decision |
| **Timeout (offline)** | 2000ms | Only for offline nodes |
| **Health score calculation** | <1ms | Per online node |

**Typical scenario:**
- 3 nodes, 1 offline
- Check time: 50ms + 50ms + 2000ms = ~2.1s **first time**
- After that: Only online nodes checked (~100ms total)

### Optimization Strategy

The system caches offline status:
```python
# First request
Check all 3 nodes: ~2.1s
Mark node 3 as offline (score = 0)

# Subsequent requests
Only check nodes 1-2: ~0.1s
Node 3 skipped (score = 0)
```

**Result:** Only first request after node goes offline is slow

## Best Practices

### 1. Add Stable Nodes First

```bash
# Add your always-on nodes first
⚡ add_node http://localhost:11434
⚡ add_node http://10.9.66.90:11434

# Add optional nodes later
⚡ add_node http://10.9.66.200:11434  # (optional dev machine)
```

### 2. Remove Permanently Dead Nodes

```bash
# Don't keep dead nodes around
⚡ remove_node http://old-server:11434
```

**Reason:** Reduces unnecessary timeout checks

### 3. Monitor with list_nodes

```bash
# Quick health check
⚡ list_nodes

# See what's online/offline
# Takes ~1-3 seconds depending on offline nodes
```

### 4. Use discover_nodes for Fresh Start

```bash
# Automatically find all online nodes on network
⚡ discover_nodes

# Replaces any offline saved nodes
```

## Advanced Configuration

### Timeout Adjustment

Edit `flockparsecli.py`:

```python
# Line 612
def _is_node_available(self, node_url, timeout=2):
    """Quick check if node is online and responding."""
    # Reduce timeout for faster checks (but more false negatives)
    # timeout=1  # Aggressive (1s timeout)
    # timeout=2  # Balanced (default)
    # timeout=5  # Conservative (slow but catches slow nodes)
```

### Skip Offline Checks (Performance Mode)

If you know all nodes are always online:

```python
# Disable availability checking (NOT RECOMMENDED)
def get_available_instances(self):
    """Get list of currently available instances."""
    return self.instances  # Skip checking, assume all online
```

**Warning:** Will cause errors if nodes are actually offline

## Summary

**FlockParse now handles optional nodes automatically:**

✅ **Nodes can be offline** - System continues working
✅ **Automatic detection** - Checks before each routing decision
✅ **Graceful recovery** - Offline nodes resume when available
✅ **No intervention** - Just let it handle things
✅ **Status visibility** - `list_nodes` shows real-time status

**Just add your nodes and let the system handle availability!**

---

**Created:** 2025-09-30
**Status:** Production-ready
**Breaking Changes:** None (fully backward compatible)