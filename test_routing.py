#!/usr/bin/env python3
"""Test that routing correctly prioritizes GPU nodes."""

from flockparsecli import load_balancer

print("=" * 70)
print("ROUTING PRIORITY TEST")
print("=" * 70)

print("\n📊 Node Health Scores:")
for inst in load_balancer.instances:
    stats = load_balancer.instance_stats[inst]
    score = load_balancer._update_health_score(inst)
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
best = load_balancer.get_best_instance()
best_stats = load_balancer.instance_stats[best]
best_gpu = "GPU" if best_stats.get("has_gpu") else "CPU"

print(f"   Selected: {best} ({best_gpu})")

if best_stats.get("has_gpu"):
    print("\n✅ PASS: GPU node correctly selected")
else:
    print("\n❌ FAIL: CPU node selected instead of GPU!")
    print("   This means routing is broken.")

print("\n" + "=" * 70)
