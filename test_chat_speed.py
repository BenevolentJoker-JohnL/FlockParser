#!/usr/bin/env python3
"""Quick test to verify chat uses GPU node and is fast."""

import time
from flockparsecli import load_balancer, CHAT_MODEL

print("=" * 70)
print("CHAT ROUTING TEST")
print("=" * 70)

# Show current node stats
print("\n📊 Current Node Configuration:")
for inst in load_balancer.instances:
    stats = load_balancer.instance_stats[inst]
    has_gpu = "🚀 GPU" if stats.get("has_gpu") else "🐢 CPU"
    print(f"   {inst}: {has_gpu}")

# Test chat routing
print("\n🤖 Testing chat generation with load balancer...")
print(f"   Model: {CHAT_MODEL}")

messages = [
    {"role": "system", "content": "You are a helpful assistant. Be brief."},
    {"role": "user", "content": "What is 2+2? Answer in one word."}
]

start = time.time()
try:
    response = load_balancer.chat_distributed(CHAT_MODEL, messages)
    duration = time.time() - start

    answer = response['message']['content']

    print(f"\n✅ Chat Response: {answer}")
    print(f"⏱️  Duration: {duration:.2f}s")

    if duration < 30:
        print("✅ PASS: Chat is fast (using GPU node)")
    else:
        print("⚠️  WARNING: Chat is slow (may not be using GPU)")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Show which node handled it
print("\n📊 Updated Node Stats:")
for inst in load_balancer.instances:
    stats = load_balancer.instance_stats[inst]
    requests = stats.get("requests", 0)
    if requests > 0:
        print(f"   {inst}: {requests} requests")

print("\n" + "=" * 70)
