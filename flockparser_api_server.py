#!/usr/bin/env python3
"""
FlockParser HTTP API Server

Provides REST API access to FlockParser document index for remote SynapticLlamas instances.
Compatible with the existing JSON-based document storage structure.
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    """Request model for document query."""

    query: str
    query_embedding: List[float]
    top_k: int = 15
    min_similarity: float = 0.5


class ChunkResult(BaseModel):
    """Result model for a single chunk."""

    text: str
    doc_name: str
    similarity: float
    doc_id: str


class QueryResponse(BaseModel):
    """Response model for document query."""

    chunks: List[ChunkResult]
    total_found: int


class StatsResponse(BaseModel):
    """Response model for statistics."""

    available: bool
    documents: int
    chunks: int
    document_names: List[str]


class FlockParserAPIServer:
    """HTTP API server for FlockParser document index."""

    def __init__(self, flockparser_path: str = "/home/joker/FlockParser", host: str = "0.0.0.0", port: int = 8765):
        """
        Initialize FlockParser API server.

        Args:
            flockparser_path: Path to FlockParser installation
            host: Host to bind to
            port: Port to listen on
        """
        self.flockparser_path = Path(flockparser_path)
        self.knowledge_base_path = self.flockparser_path / "knowledge_base"
        self.document_index_path = self.flockparser_path / "document_index.json"
        self.host = host
        self.port = port

        # Initialize FastAPI
        self.app = FastAPI(
            title="FlockParser API", description="Remote access to FlockParser document knowledge base", version="1.0.0"
        )

        # Enable CORS for remote access
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Register routes
        self._register_routes()

        # Check availability
        self.available = self.document_index_path.exists()
        if self.available:
            doc_count = self._count_documents()
            logger.info(f"✅ FlockParser API initialized ({doc_count} documents)")
        else:
            logger.warning(f"⚠️  Document index not found at {self.document_index_path}")

    def _register_routes(self):
        """Register API routes."""

        @self.app.get("/")
        async def root():
            """API status endpoint."""
            return {"service": "FlockParser API", "version": "1.0.0", "status": "running", "available": self.available}

        @self.app.get("/health")
        async def health():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "available": self.available,
                "document_index_exists": self.document_index_path.exists(),
            }

        @self.app.get("/stats", response_model=StatsResponse)
        async def get_stats():
            """Get statistics about document knowledge base."""
            if not self.available:
                return StatsResponse(available=False, documents=0, chunks=0, document_names=[])

            try:
                with open(self.document_index_path, "r") as f:
                    index_data = json.load(f)

                documents = index_data.get("documents", [])
                total_chunks = sum(len(doc.get("chunks", [])) for doc in documents)
                doc_names = [Path(doc["original"]).name for doc in documents]

                return StatsResponse(
                    available=True, documents=len(documents), chunks=total_chunks, document_names=doc_names
                )
            except Exception as e:
                logger.error(f"Error getting statistics: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/documents")
        async def get_document_index():
            """Get complete document index."""
            if not self.available:
                raise HTTPException(status_code=503, detail="Document index not available")

            try:
                with open(self.document_index_path, "r") as f:
                    index_data = json.load(f)
                return index_data
            except Exception as e:
                logger.error(f"Error reading document index: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/chunk/{chunk_id}")
        async def get_chunk(chunk_id: str):
            """Get specific chunk data by ID."""
            if not self.available:
                raise HTTPException(status_code=503, detail="Document index not available")

            try:
                # Find chunk file
                chunk_path = self.knowledge_base_path / f"{chunk_id}.json"
                if not chunk_path.exists():
                    raise HTTPException(status_code=404, detail=f"Chunk {chunk_id} not found")

                with open(chunk_path, "r") as f:
                    chunk_data = json.load(f)
                return chunk_data
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error reading chunk {chunk_id}: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/query", response_model=QueryResponse)
        async def query_documents(request: QueryRequest):
            """
            Query documents with pre-computed embedding.

            Client is responsible for generating the query embedding.
            This endpoint computes cosine similarity and returns matching chunks.
            """
            if not self.available:
                raise HTTPException(status_code=503, detail="Document index not available")

            try:
                query_embedding = np.array(request.query_embedding)

                # Load document index
                with open(self.document_index_path, "r") as f:
                    index_data = json.load(f)

                documents = index_data.get("documents", [])
                if not documents:
                    return QueryResponse(chunks=[], total_found=0)

                # Collect all chunks with similarities
                chunks_with_similarity = []

                for doc in documents:
                    for chunk_ref in doc.get("chunks", []):
                        try:
                            chunk_file = Path(chunk_ref["file"])
                            if chunk_file.exists():
                                with open(chunk_file, "r") as f:
                                    chunk_data = json.load(f)

                                chunk_embedding = chunk_data.get("embedding", [])
                                if chunk_embedding:
                                    similarity = self._cosine_similarity(query_embedding, np.array(chunk_embedding))

                                    if similarity >= request.min_similarity:
                                        chunks_with_similarity.append(
                                            {
                                                "text": chunk_data["text"],
                                                "doc_name": Path(doc["original"]).name,
                                                "similarity": float(similarity),
                                                "doc_id": doc["id"],
                                            }
                                        )
                        except Exception as e:
                            logger.debug(f"Error processing chunk: {e}")

                # Sort by similarity and return top k
                chunks_with_similarity.sort(key=lambda x: x["similarity"], reverse=True)
                results = chunks_with_similarity[: request.top_k]

                logger.info(
                    f"Query: '{request.query[:60]}...' -> "
                    f"Found {len(results)} chunks (from {len(chunks_with_similarity)} total matches)"
                )

                return QueryResponse(
                    chunks=[ChunkResult(**chunk) for chunk in results], total_found=len(chunks_with_similarity)
                )

            except Exception as e:
                logger.error(f"Error querying documents: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def _count_documents(self) -> int:
        """Count documents in FlockParser knowledge base."""
        try:
            with open(self.document_index_path, "r") as f:
                index = json.load(f)
            return len(index.get("documents", []))
        except Exception as e:
            logger.debug(f"Could not count documents: {e}")
            return 0

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0

    def run(self):
        """Start the API server."""
        logger.info(f"🚀 Starting FlockParser API server on {self.host}:{self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")


def main():
    """Entry point for console script."""
    import argparse

    parser = argparse.ArgumentParser(description="FlockParser HTTP API Server")
    parser.add_argument(
        "--path",
        type=str,
        default="/home/joker/FlockParser",
        help="Path to FlockParser installation (default: /home/joker/FlockParser)",
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8765, help="Port to listen on (default: 8765)")

    args = parser.parse_args()

    server = FlockParserAPIServer(flockparser_path=args.path, host=args.host, port=args.port)
    server.run()


if __name__ == "__main__":
    main()
