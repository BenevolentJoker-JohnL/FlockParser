# FlockParser Remote Access for SynapticLlamas

## Question: Can SynapticLlamas access FlockParser on a different machine without MCP?

**Answer: YES!** Multiple options available.

---

## Current Situation (Same Machine)

```python
# FlockParserAdapter reads local files directly
flockparser_path = "/home/joker/FlockParser"
knowledge_base = flockparser_path / "knowledge_base"
document_index = flockparser_path / "document_index.json"

# Works on same machine only
with open(document_index, 'r') as f:
    data = json.load(f)
```

---

## Option 1: Network File System (Easiest)

### Setup: Mount FlockParser directory over network

#### On FlockParser Machine (10.9.66.48):

**Install NFS Server:**
```bash
sudo apt install nfs-kernel-server

# Export FlockParser directory
sudo nano /etc/exports
# Add line:
/home/joker/FlockParser 10.9.66.0/24(ro,sync,no_subtree_check)

# Restart NFS
sudo exportfs -ra
sudo systemctl restart nfs-kernel-server
```

#### On SynapticLlamas Machine (10.9.66.154):

**Mount Remote FlockParser:**
```bash
sudo apt install nfs-common

# Create mount point
sudo mkdir -p /mnt/flockparser

# Mount FlockParser from remote machine
sudo mount 10.9.66.48:/home/joker/FlockParser /mnt/flockparser

# Make permanent (add to /etc/fstab)
echo "10.9.66.48:/home/joker/FlockParser /mnt/flockparser nfs ro,soft,intr 0 0" | sudo tee -a /etc/fstab
```

**Configure SynapticLlamas:**
```python
# In flockparser_adapter.py initialization
adapter = FlockParserAdapter(
    flockparser_path="/mnt/flockparser"  # Points to NFS mount
)

# Everything else works identically!
# Reads document_index.json and chunks transparently
```

**Pros:**
- ✅ Zero code changes to SynapticLlamas
- ✅ Transparent file access
- ✅ All existing functionality works
- ✅ Simple setup

**Cons:**
- ⚠️ Requires network file system setup
- ⚠️ Read-only access (but we only read anyway)
- ⚠️ Network latency for file reads

---

## Option 2: HTTP API (Most Flexible)

### Create a simple REST API on FlockParser machine

FlockParser already has `flock_ai_api.py` but it uses ChromaDB. We need a simple API that exposes the JSON files.

#### Create `flockparser_http_api.py` on FlockParser machine:

```python
#!/usr/bin/env python3
"""
FlockParser HTTP API - Expose document index and chunks over HTTP
Run on FlockParser machine to allow remote access
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import json
import uvicorn

app = FastAPI(title="FlockParser Document API")

FLOCKPARSER_ROOT = Path("/home/joker/FlockParser")
KNOWLEDGE_BASE = FLOCKPARSER_ROOT / "knowledge_base"
DOCUMENT_INDEX = FLOCKPARSER_ROOT / "document_index.json"

@app.get("/")
async def root():
    """API status"""
    return {
        "service": "FlockParser Document API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/api/document_index")
async def get_document_index():
    """Get document index JSON"""
    try:
        with open(DOCUMENT_INDEX, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stats")
async def get_stats():
    """Get knowledge base statistics"""
    try:
        with open(DOCUMENT_INDEX, 'r') as f:
            index_data = json.load(f)

        documents = index_data.get('documents', [])
        total_chunks = sum(len(doc.get('chunks', [])) for doc in documents)

        return {
            'available': True,
            'documents': len(documents),
            'chunks': total_chunks,
            'document_names': [Path(doc['original']).name for doc in documents]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chunks/{chunk_filename}")
async def get_chunk(chunk_filename: str):
    """Get a specific chunk JSON file"""
    try:
        chunk_path = KNOWLEDGE_BASE / chunk_filename

        # Security: ensure file is in knowledge_base directory
        if not chunk_path.resolve().is_relative_to(KNOWLEDGE_BASE.resolve()):
            raise HTTPException(status_code=403, detail="Access denied")

        if not chunk_path.exists():
            raise HTTPException(status_code=404, detail="Chunk not found")

        with open(chunk_path, 'r') as f:
            data = json.load(f)

        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search")
async def search_chunks(query: str, top_k: int = 15):
    """Search chunks by query (returns chunk metadata, caller gets embeddings)"""
    try:
        with open(DOCUMENT_INDEX, 'r') as f:
            index_data = json.load(f)

        documents = index_data.get('documents', [])

        # Return all chunk references for client-side similarity calculation
        chunks = []
        for doc in documents:
            for chunk_ref in doc.get('chunks', []):
                chunks.append({
                    'file': chunk_ref['file'],
                    'doc_name': Path(doc['original']).name,
                    'doc_id': doc['id']
                })

        return {
            'query': query,
            'total_chunks': len(chunks),
            'chunks': chunks
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
```

**Run on FlockParser machine:**
```bash
cd /home/joker/FlockParser
python flockparser_http_api.py

# API available at http://10.9.66.48:8001
```

#### Create `flockparser_remote_adapter.py` for SynapticLlamas:

```python
"""
FlockParser Remote Adapter - Access FlockParser over HTTP
For use when FlockParser is on a different machine
"""

import requests
import logging
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np

logger = logging.getLogger(__name__)

class FlockParserRemoteAdapter:
    """
    Remote adapter for FlockParser via HTTP API.
    Compatible with local FlockParserAdapter interface.
    """

    def __init__(
        self,
        flockparser_url: str = "http://10.9.66.48:8001",
        embedding_model: str = "mxbai-embed-large",
        hybrid_router_sync=None,
        load_balancer=None,
        timeout: float = 30.0
    ):
        """
        Initialize remote FlockParser adapter.

        Args:
            flockparser_url: Base URL of FlockParser HTTP API
            embedding_model: Embedding model for queries
            hybrid_router_sync: Optional HybridRouterSync for embeddings
            load_balancer: Optional load balancer
            timeout: HTTP request timeout
        """
        self.flockparser_url = flockparser_url.rstrip('/')
        self.embedding_model = embedding_model
        self.hybrid_router_sync = hybrid_router_sync
        self.load_balancer = load_balancer
        self.timeout = timeout
        self.distributed_mode = hybrid_router_sync is not None

        # Check availability
        self.available = self._check_availability()

        if self.available:
            stats = self.get_statistics()
            mode_str = " (distributed mode)" if self.distributed_mode else ""
            logger.info(f"✅ FlockParser remote adapter initialized "
                       f"at {flockparser_url} ({stats['documents']} docs){mode_str}")

    def _check_availability(self) -> bool:
        """Check if remote FlockParser API is available."""
        try:
            response = requests.get(f"{self.flockparser_url}/", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"FlockParser remote API not available: {e}")
            return False

    def _get_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding (same as local adapter)."""
        try:
            if self.hybrid_router_sync:
                result = self.hybrid_router_sync.generate_embedding(
                    model=self.embedding_model,
                    prompt=text
                )
                return result.get('embedding', [])

            # Fallback to direct Ollama
            import ollama
            response = ollama.embed(model=self.embedding_model, input=text)
            return response['embedding']
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return None

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity (same as local adapter)."""
        try:
            vec1 = np.array(vec1)
            vec2 = np.array(vec2)

            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0

    def query_documents(
        self,
        query: str,
        top_k: int = 15,
        min_similarity: float = 0.3
    ) -> List[Dict]:
        """
        Query remote FlockParser knowledge base.

        Same interface as local FlockParserAdapter.
        """
        if not self.available:
            logger.warning("FlockParser remote API not available")
            return []

        try:
            logger.info(f"🔍 Querying remote FlockParser: '{query[:60]}...'")

            # Generate query embedding locally (or via SOLLOL)
            query_embedding = self._get_embedding(query)
            if not query_embedding:
                return []

            # Get document index from remote API
            response = requests.get(
                f"{self.flockparser_url}/api/document_index",
                timeout=self.timeout
            )
            response.raise_for_status()
            index_data = response.json()

            documents = index_data.get('documents', [])
            if not documents:
                return []

            # Fetch chunks and calculate similarity
            chunks_with_similarity = []

            for doc in documents:
                for chunk_ref in doc.get('chunks', []):
                    try:
                        # Get chunk filename from path
                        chunk_filename = Path(chunk_ref['file']).name

                        # Fetch chunk from remote API
                        chunk_response = requests.get(
                            f"{self.flockparser_url}/api/chunks/{chunk_filename}",
                            timeout=self.timeout
                        )
                        chunk_response.raise_for_status()
                        chunk_data = chunk_response.json()

                        chunk_embedding = chunk_data.get('embedding', [])
                        if chunk_embedding:
                            similarity = self._cosine_similarity(
                                query_embedding,
                                chunk_embedding
                            )

                            if similarity >= min_similarity:
                                chunks_with_similarity.append({
                                    'text': chunk_data['text'],
                                    'doc_name': Path(doc['original']).name,
                                    'similarity': similarity,
                                    'doc_id': doc['id']
                                })

                    except Exception as e:
                        logger.debug(f"Error fetching chunk: {e}")

            # Sort and return top k
            chunks_with_similarity.sort(key=lambda x: x['similarity'], reverse=True)
            results = chunks_with_similarity[:top_k]

            doc_names = set(chunk['doc_name'] for chunk in results)
            logger.info(f"   📚 Found {len(results)} relevant chunks "
                       f"from {len(doc_names)} document(s)")
            if results:
                logger.info(f"   🎯 Top similarity: {results[0]['similarity']:.3f}")

            return results

        except Exception as e:
            logger.error(f"Error querying remote FlockParser: {e}")
            return []

    def get_statistics(self) -> Dict:
        """Get statistics from remote FlockParser."""
        try:
            response = requests.get(
                f"{self.flockparser_url}/api/stats",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting remote stats: {e}")
            return {
                'available': False,
                'error': str(e)
            }

    # All other methods (format_context_for_research, enhance_research_query, etc.)
    # are identical to local FlockParserAdapter - copy from flockparser_adapter.py
```

**Use in SynapticLlamas:**
```python
# In distributed_orchestrator.py
from flockparser_remote_adapter import FlockParserRemoteAdapter

self.flockparser_adapter = FlockParserRemoteAdapter(
    flockparser_url="http://10.9.66.48:8001",
    hybrid_router_sync=self.hybrid_router_sync
)

# Everything else works identically!
```

**Pros:**
- ✅ Works across any network
- ✅ Firewall-friendly (HTTP)
- ✅ Can add authentication/encryption
- ✅ Can scale (multiple SynapticLlamas → one FlockParser)

**Cons:**
- ⚠️ Requires HTTP API server on FlockParser machine
- ⚠️ Network latency for each chunk fetch
- ⚠️ More complex setup

---

## Option 3: SSHFS (Simplest for Dev)

### Mount FlockParser directory via SSH

**On SynapticLlamas Machine:**

```bash
# Install SSHFS
sudo apt install sshfs

# Mount remote directory
mkdir ~/remote_flockparser
sshfs joker@10.9.66.48:/home/joker/FlockParser ~/remote_flockparser

# Use in SynapticLlamas
adapter = FlockParserAdapter(
    flockparser_path="/home/joker/remote_flockparser"
)

# Unmount when done
fusermount -u ~/remote_flockparser
```

**Pros:**
- ✅ Zero code changes
- ✅ Quick setup for development
- ✅ Uses existing SSH access

**Cons:**
- ⚠️ Requires SSH access
- ⚠️ Can be slow over network
- ⚠️ Not suitable for production

---

## Option 4: Rsync Sync (Simple Batch)

### Periodically sync FlockParser data

**On SynapticLlamas Machine:**

```bash
#!/bin/bash
# sync_flockparser.sh

# Sync FlockParser knowledge base from remote machine
rsync -avz --delete \
  joker@10.9.66.48:/home/joker/FlockParser/knowledge_base/ \
  /home/joker/FlockParser_mirror/knowledge_base/

rsync -avz \
  joker@10.9.66.48:/home/joker/FlockParser/document_index.json \
  /home/joker/FlockParser_mirror/

echo "✅ FlockParser data synced"
```

**Run periodically:**
```bash
# Add to crontab
*/15 * * * * /home/joker/sync_flockparser.sh  # Every 15 minutes

# Or manually before research session
./sync_flockparser.sh
```

**Use local mirror:**
```python
adapter = FlockParserAdapter(
    flockparser_path="/home/joker/FlockParser_mirror"
)
```

**Pros:**
- ✅ No code changes
- ✅ Fast local access
- ✅ Works offline after sync

**Cons:**
- ⚠️ Data can be stale (up to sync interval)
- ⚠️ Requires storage on both machines

---

## Performance Comparison

| Method | Latency | Setup Complexity | Best For |
|--------|---------|------------------|----------|
| **NFS** | ~5ms | Medium | Production, always-on |
| **HTTP API** | ~20ms | High | Multi-client, scalable |
| **SSHFS** | ~15ms | Low | Development, testing |
| **Rsync** | 0ms (local) | Low | Batch updates, offline |

---

## Recommendation

### For Development/Testing:
**Use SSHFS** - Quick, zero code changes, SSH access already exists

```bash
sshfs joker@10.9.66.48:/home/joker/FlockParser ~/remote_flockparser
```

### For Production:
**Use NFS** - Transparent, reliable, good performance

```bash
# FlockParser machine exports directory
# SynapticLlamas mounts it
# Zero code changes
```

### For Multiple SynapticLlamas Instances:
**Use HTTP API** - Scalable, one FlockParser serves many clients

```python
# Each SynapticLlamas connects via HTTP
adapter = FlockParserRemoteAdapter(
    flockparser_url="http://10.9.66.48:8001"
)
```

---

## Security Considerations

### NFS:
- Use `ro` (read-only) export
- Restrict by IP subnet: `10.9.66.0/24`
- Consider NFSv4 with Kerberos for encryption

### HTTP API:
- Add API key authentication
- Use HTTPS (TLS encryption)
- Rate limiting

### SSHFS:
- Uses SSH encryption (already secure)
- Requires SSH key access

---

## Complete Setup Example (NFS - Recommended)

### FlockParser Machine (10.9.66.48):

```bash
# 1. Install NFS server
sudo apt install nfs-kernel-server

# 2. Export FlockParser directory
sudo tee -a /etc/exports << EOF
/home/joker/FlockParser 10.9.66.0/24(ro,sync,no_subtree_check)
EOF

# 3. Apply and start
sudo exportfs -ra
sudo systemctl enable nfs-kernel-server
sudo systemctl start nfs-kernel-server

# 4. Open firewall
sudo ufw allow from 10.9.66.0/24 to any port nfs
```

### SynapticLlamas Machine (10.9.66.154):

```bash
# 1. Install NFS client
sudo apt install nfs-common

# 2. Create mount point
sudo mkdir -p /mnt/flockparser

# 3. Test mount
sudo mount -t nfs 10.9.66.48:/home/joker/FlockParser /mnt/flockparser

# 4. Verify access
ls /mnt/flockparser/knowledge_base/

# 5. Make permanent
echo "10.9.66.48:/home/joker/FlockParser /mnt/flockparser nfs ro,soft,intr 0 0" | sudo tee -a /etc/fstab

# 6. Update SynapticLlamas config
# No code changes needed! Just point to mount:
# adapter = FlockParserAdapter(flockparser_path="/mnt/flockparser")
```

### Configure SynapticLlamas:

```bash
cd /home/joker/SynapticLlamas

# Edit distributed_orchestrator.py (if hardcoded path)
# Or pass as parameter:
python main.py

SynapticLlamas> rag on
✅ FlockParser RAG ENABLED (using /mnt/flockparser)

SynapticLlamas> Explain quantum computing
📚 Enhancing query with FlockParser document context...
[Works with remote FlockParser transparently!]
```

---

## Summary

**YES - Multiple ways to access FlockParser remotely without MCP:**

1. ✅ **NFS** - Best for production (transparent, fast)
2. ✅ **HTTP API** - Best for scalability (multiple clients)
3. ✅ **SSHFS** - Best for development (quick setup)
4. ✅ **Rsync** - Best for batch/offline use

**All methods work with existing SynapticLlamas code** - just change the `flockparser_path` parameter! 🚀
