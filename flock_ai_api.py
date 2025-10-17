import os
import numpy as np
import pdfplumber
import pytesseract
import chromadb
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Security, Depends, Body
from fastapi.security.api_key import APIKeyHeader
from pydantic import BaseModel
from PIL import Image
from pathlib import Path
from typing import Optional, List
import ollama
import json

# Pydantic Models for Request Bodies
class QueryRequest(BaseModel):
    query: str
    embedding: Optional[List[float]] = None
    n_results: int = 3


# API Key Configuration
API_KEY = os.getenv("FLOCKPARSE_API_KEY", "your-secret-api-key-change-this")
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Model caching configuration for faster inference
EMBEDDING_KEEP_ALIVE = "1h"  # Embedding model used frequently
CHAT_KEEP_ALIVE = "15m"  # Chat model used less frequently


async def verify_api_key(api_key: str = Security(api_key_header)):
    """Verify API key from request header."""
    if api_key != API_KEY:
        raise HTTPException(
            status_code=403, detail="Invalid or missing API Key. Include X-API-Key header with your request."
        )
    return api_key


# Initialize FastAPI app
app = FastAPI(title="FlockParse API", description="GPU-aware document processing with authentication", version="1.0.4")

# ChromaDB setup - Use CLI's database for shared access
chroma_client = chromadb.PersistentClient(path="./chroma_db_cli")
collection = chroma_client.get_or_create_collection(name="documents", metadata={"hnsw:space": "cosine"})

# Knowledge base paths (shared with CLI)
KB_DIR = Path("./knowledge_base")
KB_DIR.mkdir(exist_ok=True)
INDEX_FILE = KB_DIR / "document_index.json"

# Text Extraction from PDF (including OCR for images)


def extract_text_from_pdf(file_path):
    text = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                text.append(extracted_text)
            else:
                # OCR for scanned images
                image = page.to_image().original
                ocr_text = pytesseract.image_to_string(Image.open(image))
                text.append(ocr_text)
    return "\n".join(text)


# Convert text to embeddings using Ollama


def embed_text(text):
    response = ollama.embed(model="mxbai-embed-large", input=text, keep_alive=EMBEDDING_KEEP_ALIVE)
    # Response has 'embeddings' (list of lists) not 'embedding'
    embeddings = response.embeddings if hasattr(response, "embeddings") else []
    embedding = embeddings[0] if embeddings else []
    return np.array(embedding)


# Store document in ChromaDB


def store_document(file_name, content):
    _ = embed_text(content)
    collection.add(documents=[content], metadatas=[{"file_name": file_name}], ids=[file_name])


# Summarization using LLM


def summarize_text(text):
    response = ollama.chat(
        model="llama3.1:latest",
        messages=[{"role": "user", "content": f"Summarize this document:\n{text}"}],
        keep_alive=CHAT_KEEP_ALIVE,
    )
    return response["message"]["content"]


# Search documents


def search_documents(query):
    query_embedding = embed_text(query)
    results = collection.query(query_embeddings=[query_embedding.tolist()], n_results=3)
    return results


# FastAPI Routes


@app.get("/")
async def root():
    """Public endpoint - API status"""
    return {
        "service": "FlockParse API",
        "version": "1.0.4",
        "status": "running",
        "authentication": "Required (X-API-Key header for most endpoints)",
        "public_endpoints": ["/", "/health", "/stats", "/query"],
        "authenticated_endpoints": ["/upload", "/search", "/summarize", "/documents", "/process-local", "/process-directory"],
    }


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    """Upload and process a PDF file (requires authentication)"""
    try:
        file_path = f"./uploads/{file.filename}"
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        text_content = extract_text_from_pdf(file_path)
        store_document(file.filename, text_content)

        return {"message": "File uploaded and processed.", "file_name": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/summarize/{file_name}")
async def get_summary(file_name: str, api_key: str = Depends(verify_api_key)):
    """Get AI-generated summary of a document (requires authentication)"""
    try:
        doc = collection.get(where={"file_name": file_name})
        if not doc["documents"]:
            raise HTTPException(status_code=404, detail="Document not found.")
        summary = summarize_text(doc["documents"][0])
        return {"file_name": file_name, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search/")
async def search(query: str, api_key: str = Depends(verify_api_key)):
    """Search across documents (requires authentication)"""
    try:
        results = search_documents(query)
        return {"query": query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/")
async def list_documents(api_key: str = Depends(verify_api_key)):
    """List all documents in the knowledge base (requires authentication)"""
    try:
        if not INDEX_FILE.exists():
            return {"documents": [], "total": 0}

        with open(INDEX_FILE, "r") as f:
            index_data = json.load(f)

        documents = []
        for doc in index_data.get("documents", []):
            documents.append({
                "id": doc["id"],
                "filename": Path(doc["original"]).name,
                "original_path": doc["original"],
                "processed_date": doc["processed_date"],
                "chunks": len(doc.get("chunks", []))
            })

        return {"documents": documents, "total": len(documents)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/documents/{doc_id}")
async def get_document(doc_id: str, api_key: str = Depends(verify_api_key)):
    """Get details for a specific document (requires authentication)"""
    try:
        if not INDEX_FILE.exists():
            raise HTTPException(status_code=404, detail="No documents found")

        with open(INDEX_FILE, "r") as f:
            index_data = json.load(f)

        for doc in index_data.get("documents", []):
            if doc["id"] == doc_id:
                # Read the text file
                text_content = ""
                if Path(doc["text_path"]).exists():
                    with open(doc["text_path"], "r") as tf:
                        text_content = tf.read()

                return {
                    "id": doc["id"],
                    "filename": Path(doc["original"]).name,
                    "original_path": doc["original"],
                    "text_path": doc["text_path"],
                    "processed_date": doc["processed_date"],
                    "chunks": len(doc.get("chunks", [])),
                    "content": text_content
                }

        raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-local/")
async def process_local_pdf(
    file_path: str,
    api_key: str = Depends(verify_api_key)
):
    """Process a PDF file from the local filesystem (requires authentication)"""
    try:
        pdf_path = Path(file_path).expanduser().resolve()

        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

        if not pdf_path.suffix.lower() == ".pdf":
            raise HTTPException(status_code=400, detail="File must be a PDF")

        # Import processing function from CLI
        # Note: This requires flockparsecli to be importable
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from flockparsecli import process_pdf

            # Process the PDF (this will add it to the knowledge base)
            process_pdf(pdf_path)

            return {
                "message": "PDF processed successfully",
                "file_path": str(pdf_path),
                "filename": pdf_path.name
            }
        except ImportError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Cannot import flockparsecli: {str(e)}. Make sure FlockParser CLI is available."
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-directory/")
async def process_local_directory(
    directory_path: str,
    api_key: str = Depends(verify_api_key)
):
    """Process all PDFs in a directory from the local filesystem (requires authentication)"""
    try:
        dir_path = Path(directory_path).expanduser().resolve()

        if not dir_path.exists() or not dir_path.is_dir():
            raise HTTPException(status_code=404, detail=f"Directory not found: {directory_path}")

        pdf_files = list(dir_path.glob("*.pdf"))
        if not pdf_files:
            return {"message": "No PDF files found in directory", "processed": 0}

        # Import processing function from CLI
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from flockparsecli import process_pdf

            processed_files = []
            for pdf_path in pdf_files:
                try:
                    process_pdf(pdf_path)
                    processed_files.append(pdf_path.name)
                except Exception as e:
                    # Continue processing other files even if one fails
                    pass

            return {
                "message": f"Processed {len(processed_files)} PDFs",
                "directory": str(dir_path),
                "processed": len(processed_files),
                "files": processed_files
            }
        except ImportError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Cannot import flockparsecli: {str(e)}. Make sure FlockParser CLI is available."
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# SynapticLlamas Compatibility Endpoints


@app.get("/health")
async def health_check():
    """Health check endpoint for SynapticLlamas compatibility (public)"""
    try:
        doc_index_exists = INDEX_FILE.exists()
        chroma_healthy = collection is not None

        # Count documents if index exists
        doc_count = 0
        if doc_index_exists:
            try:
                with open(INDEX_FILE, "r") as f:
                    index_data = json.load(f)
                    doc_count = len(index_data.get("documents", []))
            except Exception:
                pass

        return {
            "status": "healthy",
            "available": True,
            "document_index_exists": doc_index_exists,
            "chroma_healthy": chroma_healthy,
            "document_count": doc_count
        }
    except Exception as e:
        return {
            "status": "error",
            "available": False,
            "error": str(e)
        }


@app.get("/stats")
async def get_stats():
    """Get statistics about knowledge base (SynapticLlamas compatibility - public)"""
    try:
        if not INDEX_FILE.exists():
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "knowledge_base_size": 0,
                "available": True
            }

        with open(INDEX_FILE, "r") as f:
            index_data = json.load(f)

        documents = index_data.get("documents", [])
        total_docs = len(documents)
        total_chunks = sum(len(doc.get("chunks", [])) for doc in documents)

        # Calculate total KB size
        kb_size = 0
        for doc in documents:
            text_path = Path(doc.get("text_path", ""))
            if text_path.exists():
                kb_size += text_path.stat().st_size

        return {
            "total_documents": total_docs,
            "total_chunks": total_chunks,
            "knowledge_base_size": kb_size,
            "available": True,
            "documents": [
                {
                    "id": doc["id"],
                    "filename": Path(doc["original"]).name,
                    "chunks": len(doc.get("chunks", [])),
                    "processed_date": doc.get("processed_date", "")
                }
                for doc in documents
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query")
async def query_with_embedding(request: QueryRequest):
    """Query with pre-computed embedding (SynapticLlamas compatibility - public)

    SynapticLlamas generates embeddings on its side, then sends them here for retrieval.
    This allows load balancing of embedding generation while centralizing document storage.
    """
    try:
        # If embedding provided, use it directly (SynapticLlamas mode)
        if request.embedding:
            query_embedding = request.embedding
        else:
            # Otherwise generate embedding locally (fallback mode)
            query_embedding = embed_text(request.query).tolist()

        # Query ChromaDB with the embedding
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=request.n_results
        )

        # Format results for SynapticLlamas
        formatted_results = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                formatted_results.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                    "id": results["ids"][0][i] if results.get("ids") else None
                })

        return {
            "query": request.query,
            "results": formatted_results,
            "total_results": len(formatted_results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Entry point for console script."""
    os.makedirs("./uploads", exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
