#!/usr/bin/env python3
"""Test MCP chat function."""
import asyncio
import time
import traceback
from flock_mcp_server import call_tool

async def test():
    try:
        print("=" * 70)
        print("MCP CHAT TEST")
        print("=" * 70)

        print("\nTesting chat_with_documents...")
        start = time.time()

        result = await call_tool("chat_with_documents", {
            "question": "What are Majorana fermions in one sentence?",
            "context_chunks": 2
        })

        duration = time.time() - start

        print(f"\n📝 Response:")
        print(result[0].text)
        print(f"\n⏱️  Duration: {duration:.1f}s")

        if duration < 40:
            print("\n✅ PASS - Chat completed successfully!")
        else:
            print(f"\n⚠️  WARNING - Chat took {duration:.1f}s (expected <40s)")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
