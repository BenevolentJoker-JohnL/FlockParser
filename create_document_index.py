#!/usr/bin/env python3
"""
Create document_index.json for FlockParser knowledge base.

Scans the knowledge_base directory and generates an index of documents and their chunks.
"""
import json
import os
from pathlib import Path
import re

# Configuration
KNOWLEDGE_BASE_PATH = Path("/home/joker/FlockParser/knowledge_base")
OUTPUT_PATH = Path("/home/joker/FlockParser/document_index.json")
TESTPDFS_PATH = Path("/home/joker/FlockParser/testpdfs")


def get_document_chunks():
    """Scan knowledge_base and group chunks by document ID."""
    documents = {}

    # Find all chunk files
    chunk_pattern = re.compile(r"doc_(\d+)_chunk_(\d+)\.json")

    for chunk_file in KNOWLEDGE_BASE_PATH.glob("doc_*_chunk_*.json"):
        match = chunk_pattern.match(chunk_file.name)
        if match:
            doc_id = int(match.group(1))
            chunk_num = int(match.group(2))

            if doc_id not in documents:
                documents[doc_id] = []

            documents[doc_id].append({"chunk_num": chunk_num, "file": str(chunk_file.absolute())})

    # Sort chunks by chunk number
    for doc_id in documents:
        documents[doc_id].sort(key=lambda x: x["chunk_num"])

    return documents


def get_pdf_files():
    """Get list of PDF files from testpdfs directory."""
    pdfs = []
    if TESTPDFS_PATH.exists():
        pdfs = sorted([str(p) for p in TESTPDFS_PATH.glob("*.pdf")])
    return pdfs


def create_document_index():
    """Create the document index JSON file."""
    document_chunks = get_document_chunks()
    pdf_files = get_pdf_files()

    # Build index
    index = {"documents": [], "created": "2025-10-04", "version": "1.0"}

    for doc_id in sorted(document_chunks.keys()):
        chunks = document_chunks[doc_id]

        # Try to match with actual PDF, otherwise use placeholder
        if len(pdf_files) >= doc_id:
            original_pdf = pdf_files[doc_id - 1]
        else:
            original_pdf = f"/home/joker/FlockParser/testpdfs/document_{doc_id}.pdf"

        doc_entry = {
            "id": f"doc_{doc_id}",
            "original": original_pdf,
            "chunk_count": len(chunks),
            "chunks": [{"chunk_id": c["chunk_num"], "file": c["file"]} for c in chunks],
        }

        index["documents"].append(doc_entry)

    # Write index
    with open(OUTPUT_PATH, "w") as f:
        json.dump(index, f, indent=2)

    print(f"✅ Created document index at {OUTPUT_PATH}")
    print(f"   Documents: {len(index['documents'])}")
    for doc in index["documents"]:
        print(f"   - {doc['id']}: {doc['chunk_count']} chunks from {Path(doc['original']).name}")


if __name__ == "__main__":
    create_document_index()
