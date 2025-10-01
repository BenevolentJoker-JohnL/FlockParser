#!/usr/bin/env python3
"""
Simple MCP Server validation - tests imports and basic structure
"""

print("=" * 70)
print("FLOCKPARSER MCP SERVER VALIDATION")
print("=" * 70)

# Test 1: Import MCP server
print("\n[1/5] Testing MCP server import...")
try:
    from flock_mcp_server import app
    print("✅ MCP server imports successfully")
except Exception as e:
    print(f"❌ Failed to import MCP server: {e}")
    exit(1)

# Test 2: Check server name
print("\n[2/5] Checking server configuration...")
try:
    assert app.name == "flockparse", f"Expected server name 'flockparse', got '{app.name}'"
    print(f"✅ Server name: {app.name}")
except Exception as e:
    print(f"❌ Server configuration error: {e}")
    exit(1)

# Test 3: List tools (synchronous check)
print("\n[3/5] Checking available tools...")
try:
    # Access the registered handler
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Import the handler function directly
    from flock_mcp_server import list_tools as tools_func
    tools = loop.run_until_complete(tools_func())

    loop.close()

    print(f"✅ Found {len(tools)} tools:")
    for i, tool in enumerate(tools, 1):
        print(f"   {i}. {tool.name}")
except Exception as e:
    print(f"❌ Failed to list tools: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 4: Check tool schemas
print("\n[4/5] Validating tool schemas...")
try:
    required_tools = {
        "process_pdf": ["file_path"],
        "query_documents": ["query"],
        "chat_with_documents": ["question"],
        "list_documents": [],
        "get_load_balancer_stats": [],
        "discover_ollama_nodes": [],
        "add_ollama_node": ["node_url"],
        "remove_ollama_node": ["node_url"]
    }

    tool_map = {t.name: t for t in tools}

    for tool_name, required_params in required_tools.items():
        if tool_name not in tool_map:
            print(f"   ❌ Missing tool: {tool_name}")
            exit(1)

        tool = tool_map[tool_name]
        schema_params = tool.inputSchema.get("properties", {}).keys()
        schema_required = set(tool.inputSchema.get("required", []))

        for param in required_params:
            if param not in schema_required:
                print(f"   ❌ {tool_name}: missing required param '{param}'")
                exit(1)

    print("✅ All tool schemas valid")

except Exception as e:
    print(f"❌ Schema validation failed: {e}")
    exit(1)

# Test 5: Check FlockParser integration
print("\n[5/5] Checking FlockParser integration...")
try:
    from flockparsecli import load_balancer, load_document_index

    # Check load balancer
    assert load_balancer is not None, "Load balancer not initialized"
    print(f"   ✅ Load balancer: {len(load_balancer.instances)} nodes")

    # Check document index
    index = load_document_index()
    doc_count = len(index.get("documents", []))
    print(f"   ✅ Document index: {doc_count} documents")

except Exception as e:
    print(f"❌ FlockParser integration error: {e}")
    exit(1)

# Summary
print("\n" + "=" * 70)
print("✅ ALL VALIDATION CHECKS PASSED")
print("=" * 70)
print("\nMCP server is properly configured and ready to use!")
print("\nTo start the MCP server:")
print("  python3 flock_mcp_server.py")
print("\nTo use with Claude Desktop, add to your MCP config:")
print("""
{
  "mcpServers": {
    "flockparse": {
      "command": "python3",
      "args": ["/home/joker/FlockParser/flock_mcp_server.py"]
    }
  }
}
""")
print("=" * 70)
