#!/usr/bin/env python3
"""Fast routing test - manually creates load balancer with skip_init_checks."""

import sys
sys.path.insert(0, '/home/joker/FlockParser')

from flockparsecli import OllamaLoadBalancer, OLLAMA_INSTANCES
import json
from pathlib import Path

print("=" * 70)
print("ROUTING PRIORITY TEST (Fast)")
print("=" * 70)

# Create load balancer with skip_init_checks to avoid network delays
print("\n🔧 Creating load balancer (skip network checks)...")
lb = OllamaLoadBalancer(OLLAMA_INSTANCES, skip_init_checks=True)

# Manually set stats based on what we know
print("📝 Loading node stats from disk...")
nodes_file = Path.home() / '.local/share/flockparse/ollama_nodes.json'
if nodes_file.exists():
    with open(nodes_file) as f:
        nodes = json.load(f)
        for node in nodes:
            if isinstance(node, str):
                node_url = node
            else:
                node_url = node.get('url')

            if node_url not in lb.instances:
                lb.instances.append(node_url)
                lb.instance_stats[node_url] = {
                    "requests": 0,
                    "errors": 0,
                    "total_time": 0,
                    "latency": 50,
                    "concurrent_requests": 0,
                    "health_score": 100,
                    "last_check": None,
                    "has_gpu": None,
                    "gpu_memory_gb": 0,
                    "is_local": node_url.startswith("http://localhost"),
                    "force_cpu": False
                }

# Manually configure what we know about the nodes
lb.instance_stats["http://localhost:11434"]["has_gpu"] = False
lb.instance_stats["http://localhost:11434"]["gpu_memory_gb"] = 0
lb.instance_stats["http://localhost:11434"]["latency"] = 50

if "http://10.9.66.90:11434" in lb.instance_stats:
    lb.instance_stats["http://10.9.66.90:11434"]["has_gpu"] = True
    lb.instance_stats["http://10.9.66.90:11434"]["is_gpu_loaded"] = True
    lb.instance_stats["http://10.9.66.90:11434"]["gpu_memory_gb"] = 1.1
    lb.instance_stats["http://10.9.66.90:11434"]["latency"] = 40

if "http://10.9.66.159:11434" in lb.instance_stats:
    lb.instance_stats["http://10.9.66.159:11434"]["has_gpu"] = False
    lb.instance_stats["http://10.9.66.159:11434"]["gpu_memory_gb"] = 0
    lb.instance_stats["http://10.9.66.159:11434"]["latency"] = 15

print("\n📊 Node Health Scores:")
for inst in lb.instances:
    stats = lb.instance_stats[inst]
    score = lb._update_health_score(inst)
    has_gpu = stats.get("has_gpu")
    vram = stats.get("gpu_memory_gb", 0)

    gpu_icon = "🚀" if has_gpu else "🐢"
    gpu_text = f"GPU ({vram:.1f}GB)" if has_gpu else "CPU"

    print(f"   {gpu_icon} {inst}")
    print(f"      Type: {gpu_text}")
    print(f"      Health Score: {score:.1f}")
    print(f"      Latency: {stats.get('latency', 'N/A')}ms")
    print()

print("\n🎯 Testing get_best_instance():")
best = lb.get_best_instance()
best_stats = lb.instance_stats[best]
best_gpu = "GPU" if best_stats.get("has_gpu") else "CPU"
best_score = lb._update_health_score(best)

print(f"   Selected: {best} ({best_gpu}, score={best_score:.1f})")

if best_stats.get("has_gpu"):
    print("\n✅ PASS: GPU node correctly selected!")
else:
    print("\n❌ FAIL: CPU node selected instead of GPU!")
    print("   Routing is broken - GPU should be heavily prioritized")

print("\n" + "=" * 70)
