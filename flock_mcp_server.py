#!/usr/bin/env python3
"""
FlockParse MCP Server
Provides document processing and querying capabilities via Model Context Protocol
"""

import asyncio
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Import FlockParse functionality
sys.path.append(str(Path(__file__).parent))

from flockparsecli import (  # noqa: E402
    process_pdf,
    load_document_index,
    get_similar_chunks,
    load_balancer,
    CHAT_MODEL,
    CHAT_KEEP_ALIVE,
)

# Initialize MCP server
app = Server("flockparse")

# Create a dedicated thread pool with more threads to prevent blocking
# Default is min(32, cpu_count + 4), we'll use 50 threads
executor = ThreadPoolExecutor(max_workers=50, thread_name_prefix="flockparse")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools for FlockParse."""
    return [
        Tool(
            name="process_pd",
            description=(
                "Process a PDF file and add it to the knowledge base. "
                "Extracts text, creates embeddings, and converts to multiple formats (TXT, MD, DOCX)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the PDF file to process",
                    }
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="query_documents",
            description=(
                "Query the document knowledge base using semantic search. "
                "Returns relevant text chunks from processed documents."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query or question to search for in the documents",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of relevant chunks to return (default: 3)",
                        "default": 3,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="chat_with_documents",
            description=(
                "Ask questions about your processed documents using AI. "
                "The system will find relevant context and generate an answer."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The question to ask about your documents"},
                    "context_chunks": {
                        "type": "integer",
                        "description": "Number of context chunks to use (default: 3)",
                        "default": 3,
                    },
                },
                "required": ["question"],
            },
        ),
        Tool(
            name="list_documents",
            description="List all documents currently in the knowledge base with their metadata.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_load_balancer_stats",
            description="Get statistics about the Ollama load balancer including node performance metrics.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="discover_ollama_nodes",
            description="Auto-discover Ollama nodes on the local network and add them to the load balancer.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="add_ollama_node",
            description="Manually add an Ollama node to the load balancer pool.",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_url": {
                        "type": "string",
                        "description": "URL of the Ollama node (e.g., http://192.168.1.100:11434)",
                    }
                },
                "required": ["node_url"],
            },
        ),
        Tool(
            name="remove_ollama_node",
            description="Remove an Ollama node from the load balancer pool.",
            inputSchema={
                "type": "object",
                "properties": {"node_url": {"type": "string", "description": "URL of the Ollama node to remove"}},
                "required": ["node_url"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    import sys

    print(f"[MCP] Tool called: {name}", file=sys.stderr)
    print(f"[MCP] Arguments: {arguments}", file=sys.stderr)

    if name == "process_pd":
        file_path = arguments["file_path"]
        try:
            import sys

            print(f"[MCP] Starting process_pdf for: {file_path}", file=sys.stderr)
            # Run synchronously in thread pool with timeout
            loop = asyncio.get_event_loop()
            print("[MCP] Got event loop, calling run_in_executor", file=sys.stderr)
            await asyncio.wait_for(
                loop.run_in_executor(executor, process_pdf, file_path), timeout=300.0  # 5 minute timeout
            )
            print("[MCP] process_pdf completed successfully", file=sys.stderr)
            return [
                TextContent(
                    type="text",
                    text=f"✅ Successfully processed PDF: {file_path}\nDocument has been added to the knowledge base.",
                )
            ]
        except asyncio.TimeoutError:
            return [TextContent(type="text", text="❌ Timeout processing PDF: Operation took longer than 5 minutes")]
        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            return [TextContent(type="text", text=f"❌ Error processing PDF: {str(e)}\n\nDetails:\n{error_details}")]

    elif name == "query_documents":
        query = arguments["query"]
        top_k = arguments.get("top_k", 3)
        try:
            import sys

            print(f"[MCP] Starting query_documents for: {query[:50]}...", file=sys.stderr)
            loop = asyncio.get_event_loop()
            print("[MCP] Calling get_similar_chunks", file=sys.stderr)
            chunks = await asyncio.wait_for(
                loop.run_in_executor(executor, get_similar_chunks, query, top_k), timeout=60.0  # 1 minute timeout
            )
            print(f"[MCP] get_similar_chunks completed, found {len(chunks)} chunks", file=sys.stderr)

            if not chunks:
                return [TextContent(type="text", text="No relevant documents found in the knowledge base.")]

            result = f"📚 Found {len(chunks)} relevant chunks:\n\n"
            for i, chunk in enumerate(chunks, 1):
                result += f"**{i}. From: {chunk['doc_name']}** (Similarity: {chunk['similarity']:.2f})\n"
                result += f"{chunk['text'][:500]}...\n\n"

            return [TextContent(type="text", text=result)]
        except asyncio.TimeoutError:
            return [TextContent(type="text", text="❌ Timeout querying documents: Operation took longer than 1 minute")]
        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            return [
                TextContent(type="text", text=f"❌ Error querying documents: {str(e)}\n\nDetails:\n{error_details}")
            ]

    elif name == "chat_with_documents":
        question = arguments["question"]
        context_chunks = arguments.get("context_chunks", 3)

        try:
            import sys

            print(f"[MCP] Starting chat_with_documents for: {question[:50]}...", file=sys.stderr)
            loop = asyncio.get_event_loop()

            # Get relevant chunks with timeout
            print("[MCP] Getting relevant chunks", file=sys.stderr)
            chunks = await asyncio.wait_for(
                loop.run_in_executor(executor, get_similar_chunks, question, context_chunks),
                timeout=60.0,  # 1 minute timeout
            )
            print(f"[MCP] Got {len(chunks)} chunks", file=sys.stderr)

            if not chunks:
                return [TextContent(type="text", text="No relevant documents found to answer this question.")]

            # Build context with intelligent fitting
            MAX_CONTEXT_TOKENS = 1500

            def estimate_tokens(text):
                """Conservative token estimation: 1 token ≈ 3.5 chars."""
                return int(len(text) / 3.5)

            context_parts = []
            current_tokens = 0

            for chunk in chunks:
                chunk_text = f"[Doc: {chunk['doc_name']}, Relevance: {chunk['similarity']:.2f}]\n{chunk['text']}"
                chunk_tokens = estimate_tokens(chunk_text)

                if current_tokens + chunk_tokens > MAX_CONTEXT_TOKENS:
                    break

                context_parts.append(chunk_text)
                current_tokens += chunk_tokens

            context = "\n\n".join(context_parts)

            # Generate answer using load-balanced routing with timeout
            system_prompt = (
                "You are FlockParser AI, a helpful assistant that answers questions "
                "based on the provided document context. Only use information from the context. "
                "If you don't know or the answer isn't in the context, say so."
            )

            def generate_response():
                print("[MCP] Calling load_balancer.chat_distributed", file=sys.stderr)
                response = load_balancer.chat_distributed(
                    model=CHAT_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"CONTEXT: {context}\n\nQUESTION: {question}"},
                    ],
                    keep_alive=CHAT_KEEP_ALIVE,
                )
                print("[MCP] Got response from LLM", file=sys.stderr)
                return response["message"]["content"]

            print("[MCP] Starting LLM generation", file=sys.stderr)
            answer = await asyncio.wait_for(
                loop.run_in_executor(executor, generate_response), timeout=120.0  # 2 minute timeout for chat
            )
            print("[MCP] LLM generation completed", file=sys.stderr)

            # Format response with sources
            result = f"**Answer:**\n{answer}\n\n**Sources:**\n"
            for i, chunk in enumerate(chunks, 1):
                result += f"{i}. {chunk['doc_name']} (relevance: {chunk['similarity']:.2f})\n"

            return [TextContent(type="text", text=result)]
        except asyncio.TimeoutError:
            return [TextContent(type="text", text="❌ Timeout generating answer: Operation took too long")]
        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            return [TextContent(type="text", text=f"❌ Error generating answer: {str(e)}\n\nDetails:\n{error_details}")]

    elif name == "list_documents":
        try:
            index_data = load_document_index()
            if not index_data["documents"]:
                return [TextContent(type="text", text="📚 No documents have been processed yet.")]

            result = f"📚 Knowledge Base: {len(index_data['documents'])} documents\n\n"
            for i, doc in enumerate(index_data["documents"], 1):
                doc_name = Path(doc["original"]).name
                result += f"{i}. **{doc_name}**\n"
                result += f"   ID: {doc['id']} | Processed: {doc['processed_date'][:10]}\n"
                result += f"   Chunks: {len(doc['chunks'])}\n\n"

            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error listing documents: {str(e)}")]

    elif name == "get_load_balancer_stats":
        try:
            stats_text = "📊 Ollama Load Balancer Statistics:\n\n"

            for inst, stats in load_balancer.instance_stats.items():
                if stats["requests"] > 0:
                    error_rate = (stats["errors"] / stats["requests"]) * 100
                    avg_time = stats["total_time"] / stats["requests"]
                    stats_text += f"🖥️  **{inst}**\n"
                    stats_text += f"   Requests: {stats['requests']}, Errors: {stats['errors']} ({error_rate:.1f}%)\n"
                    stats_text += f"   Avg Response Time: {avg_time:.2f}s\n\n"
                else:
                    stats_text += f"🖥️  **{inst}** - No requests yet\n\n"

            return [TextContent(type="text", text=stats_text)]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error getting stats: {str(e)}")]

    elif name == "discover_ollama_nodes":
        try:
            loop = asyncio.get_event_loop()
            discovered = await loop.run_in_executor(executor, load_balancer.discover_nodes)

            if discovered:
                result = f"✅ Discovered and added {len(discovered)} Ollama nodes:\n\n"
                for node in discovered:
                    result += f"- {node}\n"
            else:
                result = "⚠️ No Ollama nodes found on the network."

            return [TextContent(type="text", text=result)]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error discovering nodes: {str(e)}")]

    elif name == "add_ollama_node":
        node_url = arguments["node_url"]
        try:
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(executor, load_balancer.add_node, node_url)

            if success:
                return [TextContent(type="text", text=f"✅ Successfully added node: {node_url}")]
            else:
                return [
                    TextContent(
                        type="text", text=f"⚠️ Node {node_url} could not be added (already exists or unreachable)"
                    )
                ]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error adding node: {str(e)}")]

    elif name == "remove_ollama_node":
        node_url = arguments["node_url"]
        try:
            loop = asyncio.get_event_loop()
            success = await loop.run_in_executor(executor, load_balancer.remove_node, node_url)

            if success:
                return [TextContent(type="text", text=f"✅ Successfully removed node: {node_url}")]
            else:
                return [TextContent(type="text", text=f"⚠️ Node {node_url} could not be removed")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error removing node: {str(e)}")]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
