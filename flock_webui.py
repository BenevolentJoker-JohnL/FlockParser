#!/usr/bin/env python3
"""
FlockParse Web UI
Beautiful Streamlit interface for document processing
"""

import streamlit as st
import sys
from pathlib import Path
import time

# Import FlockParse functionality
sys.path.append(str(Path(__file__).parent))
from flockparsecli import process_pdf, load_document_index, get_similar_chunks, load_balancer  # noqa: E402

# Page configuration
st.set_page_config(
    page_title="FlockParse - Document Intelligence", page_icon="📚", layout="wide", initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown(
    """
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #667eea;
    }
    .stButton>button {
        width: 100%;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "processed_files" not in st.session_state:
    st.session_state.processed_files = []

# Header
st.markdown('<h1 class="main-header">📚 FlockParse Document Intelligence</h1>', unsafe_allow_html=True)
st.markdown("**GPU-aware distributed document processing with AI-powered search**")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("⚙️ Navigation")
    page = st.radio(
        "Choose a page:",
        [
            "📤 Upload & Process",
            "💬 Chat with Documents",
            "📊 Load Balancer",
            "🔍 Search Documents",
            "🌐 Node Management",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.header("📊 Quick Stats")

    # Load document stats
    try:
        index_data = load_document_index()
        doc_count = len(index_data.get("documents", []))
        total_chunks = sum(len(doc.get("chunks", [])) for doc in index_data.get("documents", []))
    except Exception:
        doc_count = 0
        total_chunks = 0

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Documents", doc_count)
    with col2:
        st.metric("Chunks", total_chunks)

    st.metric("Active Nodes", len(load_balancer.instances))

    st.markdown("---")
    st.caption("🔒 Privacy: This web UI runs locally")
    st.caption("Version 1.0.0")

# Main content area
if page == "📤 Upload & Process":
    st.header("📤 Upload & Process PDFs")
    st.write("Upload PDF files to extract text, create embeddings, and enable semantic search.")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_files = st.file_uploader(
            "Choose PDF files", type=["pd"], accept_multiple_files=True, help="Select one or more PDF files to process"
        )

    with col2:
        st.info("**Features:**\n- Text extraction\n- 4 format outputs\n- GPU-aware processing\n- Automatic caching")

    if uploaded_files:
        # Validate files before processing
        MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
        validation_errors = []
        total_size = 0

        for uploaded_file in uploaded_files:
            file_size = len(uploaded_file.getbuffer())
            total_size += file_size

            if file_size > MAX_FILE_SIZE:
                validation_errors.append(
                    f"❌ {uploaded_file.name}: File too large ({file_size / 1024 / 1024:.1f} MB > 100 MB)"
                )
            elif file_size == 0:
                validation_errors.append(f"❌ {uploaded_file.name}: Empty file")

        # Show validation errors
        if validation_errors:
            st.error("**Validation Errors:**")
            for error in validation_errors:
                st.write(error)
            st.info("💡 **Tip:** For files >100MB, split them or use the CLI interface for better performance.")

        # Show file summary
        st.info(
            f"📊 **Ready to process:** {len(uploaded_files)} file(s), total size: {total_size / 1024 / 1024:.1f} MB"
        )

        if st.button("🚀 Process Files", type="primary", disabled=len(validation_errors) > 0):
            progress_bar = st.progress(0)
            status_container = st.empty()

            start_time = time.time()
            success_count = 0
            error_count = 0

            for idx, uploaded_file in enumerate(uploaded_files):
                file_start = time.time()

                # Update status with detailed progress
                with status_container.container():
                    st.write(f"**Processing file {idx + 1}/{len(uploaded_files)}:** {uploaded_file.name}")
                    file_size_mb = len(uploaded_file.getbuffer()) / 1024 / 1024
                    st.caption(f"Size: {file_size_mb:.1f} MB | Extracting text, creating embeddings...")

                # Save uploaded file temporarily
                temp_path = Path("/tmp") / uploaded_file.name
                try:
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # Process the PDF with detailed error handling
                    process_pdf(str(temp_path))

                    processing_time = time.time() - file_start
                    st.session_state.processed_files.append(uploaded_file.name)
                    st.success(f"✅ {uploaded_file.name} ({processing_time:.1f}s)")
                    success_count += 1

                except FileNotFoundError as e:
                    st.error(f"❌ {uploaded_file.name}: File not found - {e}")
                    error_count += 1
                except PermissionError as e:
                    st.error(f"❌ {uploaded_file.name}: Permission denied - {e}")
                    error_count += 1
                except ValueError as e:
                    st.error(f"❌ {uploaded_file.name}: Invalid PDF format - {e}")
                    st.info("💡 Try opening in Adobe Reader and re-saving, or use `qpdf --decrypt` for encrypted PDFs")
                    error_count += 1
                except ConnectionError as e:
                    st.error(f"❌ {uploaded_file.name}: Cannot connect to Ollama - {e}")
                    st.info("💡 Ensure Ollama is running: `ollama serve`")
                    error_count += 1
                except MemoryError:
                    st.error(f"❌ {uploaded_file.name}: Out of memory - file too large")
                    st.info("💡 Try splitting the PDF or processing on a machine with more RAM")
                    error_count += 1
                except Exception as e:
                    st.error(f"❌ {uploaded_file.name}: Unexpected error")
                    with st.expander("📋 Error Details"):
                        st.code(f"{type(e).__name__}: {str(e)}")
                        st.caption("If this persists, please report at:")
                        st.caption("https://github.com/BenevolentJoker-JohnL/FlockParser/issues")
                    error_count += 1
                finally:
                    # Clean up temp file
                    if temp_path.exists():
                        temp_path.unlink()

                # Update progress
                progress = (idx + 1) / len(uploaded_files)
                progress_bar.progress(progress)

                # Estimate time remaining
                elapsed = time.time() - start_time
                if idx > 0:
                    avg_time_per_file = elapsed / (idx + 1)
                    remaining_files = len(uploaded_files) - (idx + 1)
                    eta = avg_time_per_file * remaining_files
                    status_container.caption(f"⏱️ Estimated time remaining: {eta:.0f}s")

            # Final summary
            total_time = time.time() - start_time
            status_container.empty()

            if success_count == len(uploaded_files):
                st.success(f"✅ **All {success_count} files processed successfully!** ({total_time:.1f}s total)")
                st.balloons()
            elif success_count > 0:
                st.warning(
                    f"⚠️ **Completed with errors:** {success_count} succeeded, "
                    f"{error_count} failed ({total_time:.1f}s total)"
                )
            else:
                st.error("❌ **All files failed to process.** Check error messages above.")

            progress_bar.empty()

    # Show recently processed files
    if st.session_state.processed_files:
        st.markdown("---")
        st.subheader("✅ Recently Processed")
        for filename in st.session_state.processed_files[-5:]:
            st.write(f"• {filename}")

elif page == "💬 Chat with Documents":
    st.header("💬 Chat with Your Documents")
    st.write("Ask questions about your processed documents using AI-powered semantic search.")

    # Chat interface
    chat_container = st.container()

    # Display chat history
    with chat_container:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    # Chat input
    user_question = st.chat_input("Ask a question about your documents...")

    if user_question:
        # Add user message to history
        st.session_state.chat_history.append({"role": "user", "content": user_question})

        # Display user message
        with st.chat_message("user"):
            st.write(user_question)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Searching documents and generating response..."):
                try:
                    # Get similar chunks
                    chunks = get_similar_chunks(user_question, top_k=5)

                    if not chunks:
                        response = (
                            "❓ **No documents found.**\n\n"
                            "I don't have any documents to search. "
                            "Please upload and process some PDFs first using the '📤 Upload & Process' tab."
                        )
                    else:
                        # Build context from chunks
                        context = "\n\n".join([f"From {chunk['doc_name']}:\n{chunk['text']}" for chunk in chunks[:3]])

                        # Simple response (could use chat_with_documents for more sophisticated responses)
                        response = f"Based on your documents:\n\n{context}\n\n---\n**Sources:** " + ", ".join(
                            set(c["doc_name"] for c in chunks[:3])
                        )

                    st.write(response)

                    # Add assistant response to history
                    st.session_state.chat_history.append({"role": "assistant", "content": response})

                except ConnectionError:
                    error_msg = (
                        "🔌 **Connection Error:** Cannot connect to Ollama service.\n\n"
                        "💡 **Fix:** Ensure Ollama is running with `ollama serve`"
                    )
                    st.error(error_msg)
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                except FileNotFoundError:
                    error_msg = (
                        "📂 **Database Error:** ChromaDB database not found.\n\n"
                        "💡 **Fix:** Process at least one document first to create the database."
                    )
                    st.error(error_msg)
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
                except Exception as e:
                    error_msg = f"❌ **Unexpected Error:** {type(e).__name__}"
                    st.error(error_msg)
                    with st.expander("📋 Error Details"):
                        st.code(str(e))
                        st.caption("Report at: https://github.com/BenevolentJoker-JohnL/FlockParser/issues")
                    st.session_state.chat_history.append({"role": "assistant", "content": error_msg})

    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()

elif page == "📊 Load Balancer":
    st.header("📊 Load Balancer Statistics")
    st.write("Monitor GPU-aware distributed processing across Ollama nodes.")

    # Refresh button
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("🔄 Refresh"):
            st.rerun()
    with col2:
        auto_refresh = st.checkbox("Auto-refresh", value=False)

    if auto_refresh:
        st.info("Auto-refreshing every 5 seconds...")
        time.sleep(5)
        st.rerun()

    # Display routing strategy
    st.subheader(f"🎯 Routing Strategy: {load_balancer.routing_strategy.upper()}")

    # Display node statistics
    for node in load_balancer.instances:
        stats = load_balancer.instance_stats[node]

        # Update health score
        health_score = load_balancer._update_health_score(node)

        # Determine status color
        if health_score > 80:
            status_color = "🟢"
        elif health_score > 50:
            status_color = "🟡"
        else:
            status_color = "🔴"

        # GPU indicator
        has_gpu = stats.get("has_gpu")
        is_gpu_loaded = stats.get("is_gpu_loaded", False)
        vram_gb = stats.get("gpu_memory_gb", 0)

        if has_gpu and is_gpu_loaded:
            gpu_indicator = f"🚀 GPU (~{vram_gb}GB VRAM)"
        elif has_gpu and not is_gpu_loaded:
            gpu_indicator = "⚠️ GPU (VRAM limited)"
        elif has_gpu is False:
            gpu_indicator = "🐢 CPU"
        else:
            gpu_indicator = "❓ Unknown"

        # Create expandable node card
        with st.expander(f"{status_color} {node} {gpu_indicator}", expanded=True):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Health Score", f"{health_score:.1f}/100")
            with col2:
                latency = stats.get("latency", 0)
                st.metric("Latency", f"{latency:.0f}ms")
            with col3:
                st.metric("Requests", stats.get("requests", 0))
            with col4:
                error_rate = 0
                if stats.get("requests", 0) > 0:
                    error_rate = (stats.get("errors", 0) / stats["requests"]) * 100
                st.metric("Error Rate", f"{error_rate:.1f}%")

            # Additional info
            st.caption(f"Concurrent requests: {stats.get('concurrent_requests', 0)}")
            if stats.get("requests", 0) > 0:
                avg_time = stats.get("total_time", 0) / stats["requests"]
                st.caption(f"Avg response time: {avg_time:.2f}s")

elif page == "🔍 Search Documents":
    st.header("🔍 Semantic Search")
    st.write("Search across all your documents using AI-powered semantic understanding.")

    col1, col2 = st.columns([3, 1])

    with col1:
        search_query = st.text_input(
            "Enter your search query:", placeholder="e.g., quantum mechanics, black holes, neural networks..."
        )

    with col2:
        top_k = st.slider("Results", min_value=1, max_value=20, value=5)

    if st.button("🔍 Search", type="primary") and search_query:
        search_start = time.time()
        with st.spinner("Searching documents..."):
            try:
                chunks = get_similar_chunks(search_query, top_k=top_k)
                search_time = time.time() - search_start

                if not chunks:
                    st.warning(
                        "⚠️ **No results found.**\n\n"
                        "Please upload and process some documents first using the '📤 Upload & Process' tab."
                    )
                else:
                    st.success(f"✅ Found {len(chunks)} relevant chunks in {search_time:.2f}s")

                    for idx, chunk in enumerate(chunks, 1):
                        with st.expander(f"Result {idx}: {chunk['doc_name']} (Similarity: {chunk['similarity']:.3f})"):
                            st.write(chunk["text"])
                            st.caption(f"Document: {chunk['doc_name']}")

            except ConnectionError:
                st.error("🔌 **Connection Error:** Cannot connect to Ollama service.")
                st.info("💡 **Fix:** Ensure Ollama is running with `ollama serve`")
            except FileNotFoundError:
                st.error("📂 **Database Error:** ChromaDB database not found.")
                st.info("💡 **Fix:** Process at least one document first to create the database.")
            except Exception as e:
                st.error(f"❌ **Search Error:** {type(e).__name__}")
                with st.expander("📋 Error Details"):
                    st.code(str(e))
                    st.caption("Report at: https://github.com/BenevolentJoker-JohnL/FlockParser/issues")

    # Show indexed documents
    st.markdown("---")
    st.subheader("📚 Indexed Documents")

    try:
        index_data = load_document_index()
        documents = index_data.get("documents", [])

        if documents:
            for doc in documents:
                with st.expander(f"📄 {Path(doc['original']).name}"):
                    st.write(f"**Document ID:** {doc['id']}")
                    st.write(f"**Processed:** {doc['processed_date']}")
                    st.write(f"**Chunks:** {len(doc['chunks'])}")
                    st.write(f"**Path:** {doc['text_path']}")
        else:
            st.info("No documents indexed yet. Upload and process some PDFs!")
    except Exception as e:
        st.error(f"Error loading documents: {e}")

elif page == "🌐 Node Management":
    st.header("🌐 Ollama Node Management")
    st.write("Manage distributed Ollama instances for GPU-aware load balancing.")

    # Current nodes
    st.subheader("📋 Active Nodes")

    if load_balancer.instances:
        for node in load_balancer.instances:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text(node)
            with col2:
                if st.button("❌ Remove", key=f"remove_{node}"):
                    if load_balancer.remove_node(node):
                        st.success(f"Removed: {node}")
                        st.rerun()
                    else:
                        st.error("Failed to remove node")
    else:
        st.info("No active nodes. Add an Ollama instance below.")

    st.markdown("---")

    # Add node
    st.subheader("➕ Add Ollama Node")

    col1, col2 = st.columns([3, 1])

    with col1:
        new_node_url = st.text_input(
            "Node URL:", placeholder="http://192.168.1.100:11434", help="Enter the full URL of an Ollama instance"
        )

    with col2:
        st.write("")
        st.write("")
        if st.button("➕ Add Node", type="primary"):
            if new_node_url:
                with st.spinner(f"Adding node {new_node_url}..."):
                    if load_balancer.add_node(new_node_url):
                        st.success(f"✅ Added: {new_node_url}")
                        st.rerun()
                    else:
                        st.error("❌ Failed to add node. Check URL and model availability.")
            else:
                st.warning("Please enter a node URL")

    st.markdown("---")

    # Auto-discovery
    st.subheader("🔍 Auto-Discovery")
    st.write("Automatically scan your local network for Ollama instances.")

    if st.button("🔍 Discover Nodes", type="secondary"):
        with st.spinner("Scanning network... This may take 30-60 seconds"):
            try:
                initial_count = len(load_balancer.instances)
                load_balancer.discover_nodes()
                final_count = len(load_balancer.instances)
                discovered = final_count - initial_count

                if discovered > 0:
                    st.success(f"✅ Discovered {discovered} new node(s)!")
                    st.rerun()
                else:
                    st.info("No new nodes found on the network.")
            except Exception as e:
                st.error(f"Discovery error: {e}")

    st.markdown("---")

    # Routing strategy
    st.subheader("🎯 Routing Strategy")

    current_strategy = load_balancer.routing_strategy
    strategies = ["adaptive", "round_robin", "least_loaded", "lowest_latency"]

    new_strategy = st.selectbox(
        "Select routing strategy:",
        strategies,
        index=strategies.index(current_strategy),
        help=(
            "Adaptive: GPU-aware intelligent routing (recommended)\n"
            "Round Robin: Cycle through nodes\n"
            "Least Loaded: Choose node with fewest active requests\n"
            "Lowest Latency: Choose fastest responding node"
        ),
    )

    if new_strategy != current_strategy:
        if st.button("✅ Apply Strategy"):
            load_balancer.set_routing_strategy(new_strategy)
            st.success(f"Routing strategy changed to: {new_strategy}")
            st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        <p>🚀 FlockParse - GPU-Aware Document Intelligence Platform</p>
        <p>100% Local • Privacy-First • High Performance</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def main():
    """Entry point for console script - runs Streamlit app."""
    import sys
    import subprocess

    # Get the path to this file
    script_path = __file__

    # Run streamlit with this script
    subprocess.run([sys.executable, "-m", "streamlit", "run", script_path, "--server.address=0.0.0.0"])


if __name__ == "__main__":
    # When run directly with python, streamlit has already loaded this file
    # So we don't need to do anything here - streamlit handles execution
    pass
