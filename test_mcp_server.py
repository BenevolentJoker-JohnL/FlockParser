#!/usr/bin/env python3
"""
Test script for FlockParser MCP Server
Tests all available tools and functionality
"""

import asyncio
import json
import sys
from pathlib import Path

# MCP client simulation
class MCPTestClient:
    """Simple MCP test client to validate server functionality."""

    def __init__(self):
        self.results = []

    async def test_list_tools(self):
        """Test that all expected tools are available."""
        print("\n" + "="*70)
        print("TEST 1: List Available Tools")
        print("="*70)

        from flock_mcp_server import list_tools
        tools = await list_tools()

        expected_tools = [
            "process_pdf",
            "query_documents",
            "chat_with_documents",
            "list_documents",
            "get_load_balancer_stats",
            "discover_ollama_nodes",
            "add_ollama_node",
            "remove_ollama_node"
        ]

        tool_names = [tool.name for tool in tools]

        print(f"Found {len(tools)} tools:")
        for tool in tools:
            status = "✅" if tool.name in expected_tools else "❌"
            print(f"  {status} {tool.name}: {tool.description[:60]}...")

        missing = set(expected_tools) - set(tool_names)
        if missing:
            print(f"\n❌ Missing tools: {missing}")
            return False

        print(f"\n✅ All {len(expected_tools)} expected tools are available")
        return True

    async def test_list_documents(self):
        """Test listing documents in knowledge base."""
        print("\n" + "="*70)
        print("TEST 2: List Documents")
        print("="*70)

        from flock_mcp_server import call_tool

        try:
            result = await call_tool("list_documents", {})
            print(result[0].text)
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_load_balancer_stats(self):
        """Test getting load balancer stats."""
        print("\n" + "="*70)
        print("TEST 3: Load Balancer Stats")
        print("="*70)

        from flock_mcp_server import call_tool

        try:
            result = await call_tool("get_load_balancer_stats", {})
            print(result[0].text)
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_query_documents(self):
        """Test querying documents (if any exist)."""
        print("\n" + "="*70)
        print("TEST 4: Query Documents")
        print("="*70)

        from flock_mcp_server import call_tool

        try:
            # Test query
            query = "What are Majorana fermions?"
            print(f"Query: '{query}'")
            print()

            result = await call_tool("query_documents", {
                "query": query,
                "top_k": 3
            })

            response_text = result[0].text
            print(response_text)

            if "No relevant documents" in response_text:
                print("\n⚠️  No documents in knowledge base - add PDFs first")
                return True
            elif "Found" in response_text:
                print("\n✅ Query successful")
                return True
            else:
                print("\n❌ Unexpected response")
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_chat_with_documents(self):
        """Test chat functionality (if documents exist)."""
        print("\n" + "="*70)
        print("TEST 5: Chat with Documents")
        print("="*70)

        from flock_mcp_server import call_tool

        try:
            question = "What are the main concepts discussed?"
            print(f"Question: '{question}'")
            print()

            result = await call_tool("chat_with_documents", {
                "question": question,
                "context_chunks": 3
            })

            response_text = result[0].text
            print(response_text)

            if "No relevant documents" in response_text:
                print("\n⚠️  No documents in knowledge base - add PDFs first")
                return True
            elif "Answer:" in response_text:
                print("\n✅ Chat successful")
                return True
            else:
                print("\n❌ Unexpected response")
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def test_node_management(self):
        """Test node add/remove operations."""
        print("\n" + "="*70)
        print("TEST 6: Node Management (Add/Remove)")
        print("="*70)

        from flock_mcp_server import call_tool

        try:
            # Test adding a dummy node (should fail gracefully)
            print("Testing add_ollama_node with unreachable URL...")
            result = await call_tool("add_ollama_node", {
                "node_url": "http://192.168.255.255:11434"
            })
            print(result[0].text)

            # Test removing a non-existent node
            print("\nTesting remove_ollama_node with non-existent URL...")
            result = await call_tool("remove_ollama_node", {
                "node_url": "http://192.168.255.255:11434"
            })
            print(result[0].text)

            print("\n✅ Node management tools work (graceful handling)")
            return True

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def run_all_tests(self):
        """Run all tests and report results."""
        print("\n" + "="*70)
        print("FLOCKPARSER MCP SERVER TEST SUITE")
        print("="*70)

        tests = [
            ("List Tools", self.test_list_tools),
            ("List Documents", self.test_list_documents),
            ("Load Balancer Stats", self.test_load_balancer_stats),
            ("Query Documents", self.test_query_documents),
            ("Chat with Documents", self.test_chat_with_documents),
            ("Node Management", self.test_node_management),
        ]

        results = {}
        for test_name, test_func in tests:
            try:
                results[test_name] = await test_func()
            except Exception as e:
                print(f"\n❌ Test '{test_name}' crashed: {e}")
                results[test_name] = False

        # Summary
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)

        passed = sum(1 for r in results.values() if r)
        total = len(results)

        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {test_name}")

        print(f"\n{'='*70}")
        print(f"Results: {passed}/{total} tests passed")
        print(f"{'='*70}\n")

        return passed == total

async def main():
    """Main test runner."""
    client = MCPTestClient()
    success = await client.run_all_tests()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
