import os
import json
import numpy as np
import pdfplumber
import pytesseract
import chromadb
import uvicorn
from fastapi import FastAPI, UploadFile, File, HTTPException
from pypdf import PdfReader
from PIL import Image
import ollama

# Initialize FastAPI app
app = FastAPI()

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
    response = ollama.embeddings(model="mxbai-embed-large", prompt=text)
    return np.array(response["embedding"])

# Store document in ChromaDB
def store_document(file_name, content):
    embedding = embed_text(content)
    collection.add(
        documents=[content],
        metadatas=[{"file_name": file_name}],
        ids=[file_name]
    )

# Summarization using LLM
def summarize_text(text):
    response = ollama.chat(model="llama3.1:latest", messages=[{"role": "user", "content": f"Summarize this document:\n{text}"}])
    return response["message"]["content"]

# Search documents
def search_documents(query):
    query_embedding = embed_text(query)
    results = collection.query(query_embeddings=[query_embedding.tolist()], n_results=3)
    return results

# FastAPI Routes
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
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
async def get_summary(file_name: str):
    try:
        doc = collection.get(where={"file_name": file_name})
        if not doc["documents"]:
            raise HTTPException(status_code=404, detail="Document not found.")
        summary = summarize_text(doc["documents"][0])
        return {"file_name": file_name, "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search/")
async def search(query: str):
    try:
        results = search_documents(query)
        return {"query": query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    os.makedirs("./uploads", exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=8000)

