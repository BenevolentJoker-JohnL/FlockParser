import os
import numpy as np
import pdfplumber
import pytesseract
import chromadb
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from PIL import Image
import ollama

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
app = FastAPI(title="FlockParse API", description="GPU-aware document processing with authentication", version="1.0.0")

# ChromaDB setup
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="documents")

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
        "version": "1.0.0",
        "status": "running",
        "authentication": "Required (X-API-Key header)",
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


def main():
    """Entry point for console script."""
    os.makedirs("./uploads", exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
