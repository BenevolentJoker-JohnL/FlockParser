# **LocalDocAI - Offline AI-Powered Document Processing**  

## **Overview**  
`LocalDocAI` is a **fully local** AI-powered document processor that:  
✅ Extracts **text from PDFs** with multiple methods (PyPDF2 and pdftotext).  
✅ Converts PDFs to **multiple formats** (TXT, Markdown, DOCX).  
✅ Uses **Ollama embeddings** (`mxbai-embed-large`) for **semantic search**.  
✅ Enables **AI-powered chat** with your document knowledge base using `llama3.1`.  
✅ Works entirely offline with no data sent to external servers.  
✅ Preserves original document names in all converted files.

## **🔧 Installation**  

### **1. Clone the Repository**  
```bash
git clone https://github.com/yourusername/local-doc-ai.git
cd local-doc-ai
```

### **2. Install Python Dependencies**  
```bash
pip install -r requirements.txt
```

### **3. Install External Dependencies**  

#### For Better PDF Text Extraction:
- **Linux**: `sudo apt-get install poppler-utils`
- **macOS**: `brew install poppler`
- **Windows**: Download from [Poppler for Windows](http://blog.alivate.com.au/poppler-windows/)

#### For OCR Support (Optional):
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

### **Command Line Interface**

Run the script:
```bash
python local_doc_ai.py
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

### **Example Workflow**

1. **Check Dependencies**:
   ```
   ⚡ Enter command: check_deps
   ```

2. **Process a PDF**:
   ```
   ⚡ Enter command: open_pdf path/to/your/document.pdf
   ```

3. **Process All PDFs in a Directory**:
   ```
   ⚡ Enter command: open_dir path/to/pdf/folder
   ```

4. **Chat with Your Documents**:
   ```
   ⚡ Enter command: chat
   ```
   Then ask questions about your processed documents.

5. **List Processed Documents**:
   ```
   ⚡ Enter command: list_docs
   ```

## **💡 Features**

| Feature | Description |
|---------|-------------|
| **Multi-method PDF Extraction** | Uses both PyPDF2 and pdftotext for best results |
| **Format Conversion** | Converts PDFs to TXT, Markdown, and DOCX |
| **Semantic Search** | Uses vector embeddings to find relevant information |
| **Interactive Chat** | Discuss your documents with AI assistance |
| **Local Privacy** | 100% offline, no data sent to external servers |
| **Filename Preservation** | Maintains original document names in converted files |

## **📁 Project Structure**

- `/converted_files` - Stores the converted document formats
- `/knowledge_base` - Contains the vector database and document chunks

## **🚀 Future Additions**
- ⬜ **Web UI** for easy document management  
- ⬜ **Advanced OCR Support** for better handling of scanned documents
- ⬜ **Multi-language Support** for processing non-English documents

## **🤝 Contributing**
Contributions are welcome! Please feel free to submit a Pull Request.

## **📄 License**
This project is licensed under the MIT License - see the LICENSE file for details.
