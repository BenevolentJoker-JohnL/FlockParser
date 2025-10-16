#!/usr/bin/env python3
"""
Verify FlockParser file access from SOLLOL directory.
Tests that the documented paths in FLOCKPARSER_REMOTE_ACCESS.md are correct.
"""

import json
from pathlib import Path

def verify_local_access():
    """Verify FlockParser files are accessible locally."""

    print("🔍 Verifying FlockParser file access...")
    print()

    # Check FlockParser directory
    flockparser_path = Path("/home/joker/FlockParser")
    if not flockparser_path.exists():
        print(f"❌ FlockParser directory not found: {flockparser_path}")
        return False
    print(f"✅ FlockParser directory exists: {flockparser_path}")

    # Check knowledge base
    kb_path = flockparser_path / "knowledge_base"
    if not kb_path.exists():
        print(f"❌ Knowledge base directory not found: {kb_path}")
        return False

    chunk_files = list(kb_path.glob("*.json"))
    print(f"✅ Knowledge base exists with {len(chunk_files)} chunk files")

    # Check document index
    doc_index_path = flockparser_path / "document_index.json"
    if not doc_index_path.exists():
        print(f"❌ Document index not found: {doc_index_path}")
        return False

    with open(doc_index_path, 'r') as f:
        index_data = json.load(f)

    num_docs = len(index_data.get('documents', []))
    num_chunks = sum(len(doc.get('chunks', [])) for doc in index_data.get('documents', []))

    print(f"✅ Document index exists")
    print(f"   📚 Documents: {num_docs}")
    print(f"   📄 Chunks: {num_chunks}")

    # Verify chunk file format
    if chunk_files:
        sample_chunk = chunk_files[0]
        with open(sample_chunk, 'r') as f:
            chunk_data = json.load(f)

        has_text = 'text' in chunk_data
        has_embedding = 'embedding' in chunk_data
        embedding_dim = len(chunk_data.get('embedding', []))

        print(f"\n📋 Sample chunk format ({sample_chunk.name}):")
        print(f"   {'✅' if has_text else '❌'} Has 'text' field")
        print(f"   {'✅' if has_embedding else '❌'} Has 'embedding' field")
        print(f"   📊 Embedding dimension: {embedding_dim}")

        if has_text:
            text_preview = chunk_data['text'][:100] + "..." if len(chunk_data['text']) > 100 else chunk_data['text']
            print(f"   📝 Text preview: {text_preview}")

    print()
    print("✅ All FlockParser files are accessible locally")
    print()
    print("📍 File locations verified:")
    print(f"   • FlockParser root: {flockparser_path}")
    print(f"   • Knowledge base: {kb_path}")
    print(f"   • Document index: {doc_index_path}")
    print()
    print("🌐 Remote access methods documented in:")
    print("   /home/joker/SOLLOL/FLOCKPARSER_REMOTE_ACCESS.md")
    print()
    print("   Methods available:")
    print("   1. NFS (Network File System) - Transparent file access")
    print("   2. HTTP REST API - Custom API endpoint")
    print("   3. SSHFS - SSH-based mounting")
    print("   4. Rsync - Periodic synchronization")

    return True

if __name__ == "__main__":
    verify_local_access()
