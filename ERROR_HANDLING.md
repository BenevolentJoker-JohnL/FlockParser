# FlockParser Error Handling Guide

This document covers common error scenarios, their causes, and solutions.

---

## Table of Contents

- [Installation Errors](#installation-errors)
- [Runtime Errors](#runtime-errors)
- [Database Errors](#database-errors)
- [Network Errors](#network-errors)
- [Processing Errors](#processing-errors)
- [MCP Integration Errors](#mcp-integration-errors)

---

## Installation Errors

### Missing System Dependencies

**Error:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'pdftoppm'
```

**Cause:** Poppler utilities not installed

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils

# macOS
brew install poppler

# Windows
# Download from: https://github.com/oschwartz10612/poppler-windows/releases/
```

---

### Tesseract OCR Not Found

**Error:**
```
pytesseract.pytesseract.TesseractNotFoundError
```

**Cause:** Tesseract OCR not installed

**Solution:**
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-eng

# macOS
brew install tesseract

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

---

## Runtime Errors

### Permission Denied Errors

**Error:**
```
PermissionError: [Errno 13] Permission denied: 'converted_files'
```

**Cause:** Working directory mismatch (common with MCP server)

**Solution:**
- FlockParser uses absolute paths internally (fixed in v1.0+)
- Ensure you have write permissions in the project directory
- If using Docker, check volume mount permissions

---

### Python Module Not Found

**Error:**
```
ModuleNotFoundError: No module named 'chromadb'
```

**Cause:** Dependencies not installed

**Solution:**
```bash
pip install -r requirements.txt

# Or install with extras
pip install -e .[dev]
```

---

## Database Errors

### ChromaDB Lock Errors

**Error:**
```
sqlite3.OperationalError: database is locked
```

**Cause:** Multiple processes accessing the same ChromaDB database simultaneously

**Solutions:**

1. **Kill competing processes:**
   ```bash
   # Find processes
   ps aux | grep -E "python.*flock"

   # Kill specific process
   kill <PID>
   ```

2. **Use separate databases per interface:**
   - CLI: `chroma_db_cli/`
   - API: `chroma_db/`
   - Each interface should have its own database

3. **Upgrade to PostgreSQL backend** (production):
   ```python
   # In your code, replace:
   client = chromadb.PersistentClient(path="./chroma_db_cli")

   # With:
   client = chromadb.HttpClient(host="localhost", port=8000)
   ```

---

### ChromaDB Collection Already Exists

**Error:**
```
chromadb.errors.UniqueConstraintError: Collection already exists
```

**Cause:** Attempting to create a collection that already exists

**Solution:**
```python
# Get existing collection instead of creating
collection = client.get_collection(name="your_collection")

# Or delete and recreate (be careful!)
client.delete_collection(name="your_collection")
collection = client.create_collection(name="your_collection")
```

---

## Network Errors

### Ollama Node Connection Timeout

**Error:**
```
requests.exceptions.ConnectionError: Failed to establish connection to http://192.168.1.90:11434
```

**Cause:** Node is down, firewall blocking, or incorrect IP

**Solutions:**

1. **Check node is running:**
   ```bash
   curl http://192.168.1.90:11434/api/tags
   ```

2. **Check firewall:**
   ```bash
   # On Ollama node
   sudo ufw allow 11434
   ```

3. **Verify IP address:**
   ```bash
   # Check node's actual IP
   ip addr show
   ```

---

### Node Discovery Returns Empty List

**Error:**
```
Warning: No Ollama nodes discovered
```

**Cause:** Nodes not advertising or network isolation

**Solutions:**

1. **Manual node addition:**
   ```python
   # In flockparsecli.py, add manually:
   NODES = [
       {"url": "http://192.168.1.90:11434"},
       {"url": "http://192.168.1.91:11434"},
   ]
   ```

2. **Check network connectivity:**
   ```bash
   ping 192.168.1.90
   nc -zv 192.168.1.90 11434
   ```

---

## Processing Errors

### PDF Extraction Fails

**Error:**
```
pdfplumber.exceptions.PDFSyntaxError
```

**Cause:** Corrupted or encrypted PDF

**Solutions:**

1. **Try OCR fallback:**
   - FlockParser automatically attempts OCR if extraction fails
   - Ensure Tesseract is installed (see above)

2. **Repair PDF:**
   ```bash
   # Using ghostscript
   gs -o repaired.pdf -sDEVICE=pdfwrite -dPDFSETTINGS=/prepress input.pdf
   ```

3. **Remove encryption:**
   ```bash
   # Using qpdf
   qpdf --decrypt --password=PASSWORD encrypted.pdf decrypted.pdf
   ```

---

### OCR Returns Empty Text

**Error:**
```
Warning: OCR extracted 0 characters from image
```

**Cause:** Image quality too low, or wrong language pack

**Solutions:**

1. **Install additional language packs:**
   ```bash
   sudo apt-get install tesseract-ocr-spa  # Spanish
   sudo apt-get install tesseract-ocr-fra  # French
   ```

2. **Improve image quality:**
   - Use higher DPI: `dpi=300` parameter in pdf2image
   - Preprocess images (contrast, brightness)

---

### Timeout During Processing

**Error:**
```
asyncio.exceptions.TimeoutError: Task exceeded timeout of 300 seconds
```

**Cause:** Large document or slow model

**Solutions:**

1. **Increase timeout in MCP server:**
   ```python
   # In flock_mcp_server.py
   timeout=600.0  # Increase to 10 minutes
   ```

2. **Use faster model:**
   ```bash
   # Instead of llama3.2:70b, use smaller model
   ollama run llama3.2:8b
   ```

3. **Split large documents:**
   - Process documents in smaller chunks
   - Use batch processing

---

## MCP Integration Errors

### MCP Server Disconnects Immediately

**Error:**
```
Server disconnected
```

**Causes & Solutions:**

1. **Import errors:**
   ```bash
   # Test manually
   python3 flock_mcp_server.py
   # Check for import errors
   ```

2. **Wrong Python version:**
   ```bash
   # MCP requires Python 3.10+
   python3 --version
   ```

3. **Missing dependencies:**
   ```bash
   pip install mcp chromadb requests
   ```

---

### MCP Operations Hang Indefinitely

**Error:**
- No error message, operations just hang forever

**Cause:** Database locked by another process

**Solution:**
```bash
# Find and kill competing processes
ps aux | grep -E "python.*flock" | grep -v grep
kill <PID_of_CLI_or_other_process>

# Restart MCP server
# (Claude Desktop will auto-restart on config reload)
```

---

### Claude Desktop Doesn't See Tools

**Error:**
- MCP server running but tools not appearing in Claude Desktop

**Solution:**

1. **Check config file location:**
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. **Verify config syntax:**
   ```json
   {
     "mcpServers": {
       "flockparse": {
         "command": "python3",
         "args": ["/absolute/path/to/flock_mcp_server.py"]
       }
     }
   }
   ```

3. **Restart Claude Desktop:**
   - Completely quit and restart
   - Check "Servers" icon in bottom right

---

## Advanced Troubleshooting

### Enable Debug Logging

**For CLI:**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**For MCP Server:**
```bash
# Debug output already goes to stderr
# Check Claude Desktop logs:
# macOS: ~/Library/Logs/Claude/mcp-server-flockparse.log
```

**For API:**
```bash
# Run with increased verbosity
uvicorn flock_ai_api:app --log-level debug
```

---

### Check System Resources

**VRAM Usage:**
```bash
nvidia-smi  # NVIDIA GPUs
rocm-smi   # AMD GPUs
```

**Memory Usage:**
```bash
free -h    # Linux
top        # All platforms
```

**Disk Space:**
```bash
df -h
du -sh converted_files/ chroma_db_cli/
```

---

## Getting Help

If you encounter an error not covered here:

1. **Search existing issues:**
   - https://github.com/BenevolentJoker-JohnL/FlockParser/issues

2. **Create a new issue with:**
   - Full error message and stack trace
   - Steps to reproduce
   - Python version: `python3 --version`
   - OS and version: `uname -a` (Linux/Mac) or `ver` (Windows)
   - Installed packages: `pip freeze`

3. **Check the logs:**
   - MCP server: stderr output or Claude Desktop logs
   - API server: `api_server.log`
   - ChromaDB: Check database integrity

---

## Prevention Best Practices

1. **Always use virtual environments:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Keep dependencies updated:**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

3. **Separate databases per interface:**
   - Don't share ChromaDB between CLI and API
   - Use different ports for different services

4. **Monitor resource usage:**
   - Set up VRAM monitoring (see VRAM_MONITORING.md)
   - Watch disk space for large document sets

5. **Use health checks:**
   ```bash
   # Test Ollama connectivity
   curl http://localhost:11434/api/tags

   # Test API health
   curl http://localhost:8000/
   ```

6. **Regular backups:**
   ```bash
   # Backup vector databases
   tar -czf chroma_backup_$(date +%Y%m%d).tar.gz chroma_db_cli/ chroma_db/
   ```

---

## Related Documentation

- [CHROMADB_PRODUCTION.md](CHROMADB_PRODUCTION.md) - Production database setup
- [VRAM_MONITORING.md](VRAM_MONITORING.md) - GPU monitoring
- [GPU_ROUTER_SETUP.md](GPU_ROUTER_SETUP.md) - Distributed setup
- [README.md](README.md) - General usage and quickstart
