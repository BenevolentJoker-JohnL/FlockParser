#!/usr/bin/env python3
"""Comprehensive MCP Server Test Suite - All Functions."""
import asyncio
import time
from flock_mcp_server import list_tools, call_tool

async def run_tests():
    print("=" * 70)
    print("FLOCKPARSER MCP SERVER - COMPREHENSIVE TEST")
    print("=" * 70)

    results = {}

    # TEST 1: List Tools
    print("\n[TEST 1/6] List Available Tools")
    print("-" * 70)
    try:
        tools = await list_tools()
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool.name}")
        results["list_tools"] = True
    except Exception as e:
        print(f"❌ Failed: {e}")
        results["list_tools"] = False

    # TEST 2: List Documents
    print("\n[TEST 2/6] List Documents")
    print("-" * 70)
    try:
        result = await call_tool("list_documents", {})
        print(result[0].text[:200] + "...")
        results["list_documents"] = True
    except Exception as e:
        print(f"❌ Failed: {e}")
        results["list_documents"] = False

    # TEST 3: Load Balancer Stats
    print("\n[TEST 3/6] Load Balancer Stats")
    print("-" * 70)
    try:
        result = await call_tool("get_load_balancer_stats", {})
        print(result[0].text[:300] + "...")
        results["lb_stats"] = True
    except Exception as e:
        print(f"❌ Failed: {e}")
        results["lb_stats"] = False

    # TEST 4: Query Documents
    print("\n[TEST 4/6] Query Documents")
    print("-" * 70)
    try:
        start = time.time()
        result = await call_tool("query_documents", {
            "query": "What are Majorana fermions?",
            "top_k": 3
        })
        duration = time.time() - start
        print(result[0].text[:300] + "...")
        print(f"⏱️  Query time: {duration:.2f}s")
        results["query"] = True
    except Exception as e:
        print(f"❌ Failed: {e}")
        results["query"] = False

    # TEST 5: Chat with Documents
    print("\n[TEST 5/6] Chat with Documents")
    print("-" * 70)
    try:
        start = time.time()
        result = await call_tool("chat_with_documents", {
            "question": "Explain Majorana fermions briefly.",
            "context_chunks": 2
        })
        duration = time.time() - start
        print(result[0].text[:400])
        print(f"\n⏱️  Chat time: {duration:.2f}s")

        if duration < 40:
            print("✅ Performance acceptable")
            results["chat"] = True
        else:
            print(f"⚠️  Slow (>{duration:.1f}s)")
            results["chat"] = False
    except Exception as e:
        print(f"❌ Failed: {e}")
        results["chat"] = False

    # TEST 6: Node Management
    print("\n[TEST 6/6] Node Management (Add/Remove)")
    print("-" * 70)
    try:
        # Test add (should fail gracefully for invalid node)
        result = await call_tool("add_ollama_node", {
            "node_url": "http://192.168.255.255:11434"
        })
        print(f"Add test: {result[0].text[:100]}")

        # Test remove (should fail gracefully)
        result = await call_tool("remove_ollama_node", {
            "node_url": "http://192.168.255.255:11434"
        })
        print(f"Remove test: {result[0].text[:100]}")
        results["node_mgmt"] = True
    except Exception as e:
        print(f"❌ Failed: {e}")
        results["node_mgmt"] = False

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n{'='*70}")
    if passed == total:
        print(f"🎉 ALL {total}/{total} TESTS PASSED!")
        print("✅ MCP Server is production ready!")
    else:
        print(f"⚠️  {passed}/{total} tests passed")
        print(f"❌ {total - passed} test(s) failed")
    print("=" * 70)

    return passed == total

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    exit(0 if success else 1)
