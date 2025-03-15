Hi guys! 

I have actually decided to develop this application out further and will be licensing features. This is the free version! Ill be posting updates of the enhanced features with demonstrations when theyre complete. Until then, enjoy! 

# **FlockParse - AI-Powered Document Intelligence Platform**

## **Overview**  
`FlockParse` is a **fully local** AI-powered document intelligence platform that:  
✅ Extracts **text from PDFs** with multiple methods (PyPDF2 and pdftotext)  
✅ Converts PDFs to **multiple formats** (TXT, Markdown, DOCX)  
✅ Uses **Ollama embeddings** (`mxbai-embed-large`) for **semantic search**  
✅ Enables **AI-powered chat** with your document knowledge base using `llama3.1`  
✅ Works entirely offline with no data sent to external servers  
✅ Preserves original document names in all converted files

The project offers two main interfaces:
1. **flockparsecli.py** - A command-line interface for personal document processing
2. **flock_ai_api.py** - A web server API for multi-user or application integration

## **🔧 Installation**  

### **1. Clone the Repository**  
```bash
git clone https://github.com/yourusername/flockparse.git
cd flockparse
```

### **2. Install Python Dependencies**  
```bash
pip install -r requirements.txt
```

Required dependencies:
- fastapi
- uvicorn
- pdfplumber
- pytesseract
- PyPDF2
- pypdf
- chromadb
- python-docx
- ollama
- numpy
- Pillow
- markdown

### **3. Install External Dependencies**  

#### For Better PDF Text Extraction:
- **Linux**: `sudo apt-get install poppler-utils`
- **macOS**: `brew install poppler`
- **Windows**: Download from [Poppler for Windows](http://blog.alivate.com.au/poppler-windows/)

#### For OCR Support:
- **Linux**: `sudo apt-get install tesseract-ocr`
- **macOS**: `brew install tesseract`
- **Windows**: Install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)

### **4. Install and Configure Ollama**  

1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Start the Ollama service:
   ```bash
   ollama serve
   ```
3. Pull the required models:
   ```bash
   ollama pull mxbai-embed-large
   ollama pull llama3.1:latest
   ```

## **📜 Usage**

### **CLI Interface (flockparsecli.py)**

Run the script:
```bash
python flockparsecli.py
```

Available commands:
```
📖 open_pdf <file>   → Process a single PDF file
📂 open_dir <dir>    → Process all PDFs in a directory
💬 chat              → Chat with processed PDFs
📊 list_docs         → List all processed documents
🔍 check_deps        → Check for required dependencies
❌ exit              → Quit the program
```

### **Web Server API (flock_ai_api.py)**

Start the API server:
```bash
python flock_ai_api.py
```

The server will run on `http://0.0.0.0:8000` by default with the following endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload/` | POST | Upload and process a PDF file |
| `/summarize/{file_name}` | GET | Get an AI-generated summary of a document |
| `/search/?query=your_query` | GET | Search for relevant documents |

#### Example API Usage:

**Upload a document:**
```bash
curl -X POST -F "file=@your_document.pdf" http://localhost:8000/upload/
```

**Get a document summary:**
```bash
curl http://localhost:8000/summarize/your_document.pdf
```

**Search across documents:**
```bash
curl http://localhost:8000/search/?query=your%20search%20query
```

## **💡 Practical Use Cases**

### **Knowledge Management**
- Create searchable archives of research papers, legal documents, and technical manuals
- Generate summaries of lengthy documents for quick review
- Chat with your document collection to find specific information without manual searching

### **Legal & Compliance**
- Process contract repositories for semantic search capabilities
- Extract key terms and clauses from legal documents
- Analyze regulatory documents for compliance requirements

### **Research & Academia**
- Process and convert academic papers for easier reference
- Create a personal research assistant that can reference your document library
- Generate summaries of complex research for presentations or reviews

### **Business Intelligence**
- Convert business reports into searchable formats
- Extract insights from PDF-based market research
- Make proprietary documents more accessible throughout an organization

## **🔄 Example Workflows**

### **CLI Workflow: Research Paper Processing**

1. **Check Dependencies**:
   ```
   ⚡ Enter command: check_deps
   ```

2. **Process a Directory of Research Papers**:
   ```
   ⚡ Enter command: open_dir ~/research_papers
   ```

3. **Chat with Your Research Collection**:
   ```
   ⚡ Enter command: chat
   🙋 You: What are the key methods used in the Smith 2023 paper?
   ```

### **API Workflow: Document Processing Service**

1. **Start the API Server**:
   ```bash
   python flock_ai_api.py
   ```

2. **Upload Documents via API**:
   ```bash
   curl -X POST -F "file=@quarterly_report.pdf" http://localhost:8000/upload/
   ```

3. **Generate a Summary**:
   ```bash
   curl http://localhost:8000/summarize/quarterly_report.pdf
   ```

4. **Search Across Documents**:
   ```bash
   curl http://localhost:8000/search/?query=revenue%20growth%20Q3
   ```

## **🔧 Troubleshooting Guide**

### **Ollama Connection Issues**

**Problem**: Error messages about Ollama not being available or connection failures.

**Solution**:
1. Verify Ollama is running: `ps aux | grep ollama`
2. Restart the Ollama service: 
   ```bash
   killall ollama
   ollama serve
   ```
3. Check that you've pulled the required models:
   ```bash
   ollama list
   ```
4. If models are missing:
   ```bash
   ollama pull mxbai-embed-large
   ollama pull llama3.1:latest
   ```

### **PDF Text Extraction Failures**

**Problem**: No text extracted from certain PDFs.

**Solution**:
1. Check if the PDF is scanned/image-based:
   - Install OCR tools: `sudo apt-get install tesseract-ocr` (Linux)
   - For better scanned PDF handling: `pip install ocrmypdf`
   - Process with OCR: `ocrmypdf input.pdf output.pdf`

2. If the PDF has unusual fonts or formatting:
   - Install poppler-utils for better extraction
   - Try using the `-layout` option with pdftotext manually:
     ```bash
     pdftotext -layout problem_document.pdf output.txt
     ```

### **Memory Issues with Large Documents**

**Problem**: Application crashes with large PDFs or many documents.

**Solution**:
1. Process one document at a time for very large PDFs
2. Reduce the chunk size in the code (default is 512 characters)
3. Increase your system's available memory or use a swap file
4. For server deployments, consider using a machine with more RAM

### **API Server Not Starting**

**Problem**: Error when trying to start the API server.

**Solution**:
1. Check for port conflicts: `lsof -i :8000`
2. If another process is using port 8000, kill it or change the port
3. Verify FastAPI is installed: `pip install fastapi uvicorn`
4. Check for Python version compatibility (requires Python 3.7+)

## **💡 Features**

| Feature | Description |
|---------|-------------|
| **Multi-method PDF Extraction** | Uses both PyPDF2 and pdftotext for best results |
| **Format Conversion** | Converts PDFs to TXT, Markdown, and DOCX |
| **Semantic Search** | Uses vector embeddings to find relevant information |
| **Interactive Chat** | Discuss your documents with AI assistance |
| **Local Privacy** | 100% offline, no data sent to external servers |
| **Filename Preservation** | Maintains original document names in converted files |
| **REST API** | Web server for multi-user/application integration |
| **Document Summarization** | AI-generated summaries of uploaded documents |
| **OCR Processing** | Extract text from scanned documents using image recognition |

## **Comparing flockparsecli.py and flock_ai_api.py**

| Feature | flockparsecli.py | flock_ai_api.py |
|---------|----------------|-----------|
| **Interface** | Command line | REST API over HTTP |
| **Use case** | Personal document processing | Service/application integration |
| **Document formats** | Creates TXT, MD, DOCX | Stores extracted text only |
| **Interaction** | Interactive chat mode | Query/response via API |
| **Multi-user** | Single user | Multiple users/applications |
| **Storage** | Local file-based | ChromaDB vector database |

## **📁 Project Structure**

- `/converted_files` - Stores the converted document formats (flockparsecli.py)
- `/knowledge_base` - Contains the vector database and document chunks (flockparsecli.py)
- `/uploads` - Temporary storage for uploaded documents (flock_ai_api.py)
- `/chroma_db` - ChromaDB vector database (flock_ai_api.py)

## **🚀 Future Additions**
- ⬜ **Web UI** for easy document management  
- ⬜ **Advanced OCR Support** for better handling of scanned documents
- ⬜ **Multi-language Support** for processing non-English documents
- ⬜ **Authentication** for the flock_ai_api.py API endpoints
- ⬜ **Document versioning** to track changes over time

## **🤝 Contributing**
Contributions are welcome! Please feel free to submit a Pull Request.

## **📄 License**
This project is licensed under the MIT License - see the LICENSE file for details.
