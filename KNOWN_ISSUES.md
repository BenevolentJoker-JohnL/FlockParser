# Known Issues and Limitations

**Last Updated:** 2025-10-01
**Version:** 1.0.0

This document honestly documents known limitations, edge cases, and areas for improvement. We believe in transparency over marketing hype.

---

## Table of Contents

- [Maturity & Production Readiness](#maturity--production-readiness)
- [PDF Processing Limitations](#pdf-processing-limitations)
- [Performance & Scaling](#performance--scaling)
- [Network & Distributed System Issues](#network--distributed-system-issues)
- [Security Concerns](#security-concerns)
- [Test Coverage](#test-coverage)
- [UI/UX Polish](#uiux-polish)
- [Roadmap](#roadmap)

---

## Maturity & Production Readiness

### Current Status: **Beta (4 - Development Status)**

**What works well:**
- ✅ Core distributed processing (tested on 3-node heterogeneous cluster)
- ✅ GPU detection and VRAM monitoring (NVIDIA GPUs via Ollama)
- ✅ Basic PDF extraction (text-based PDFs work reliably)
- ✅ ChromaDB vector storage (tested with 1000+ documents)
- ✅ Node auto-discovery on local networks

**What needs improvement:**
- ⚠️ **Battle testing:** Only tested by 1-2 developers (me) on specific hardware
- ⚠️ **User feedback:** No production deployments yet
- ⚠️ **Long-term stability:** Longest continuous run was ~12 hours
- ⚠️ **Documentation gaps:** Some edge cases not documented
- ⚠️ **Error recovery:** Some failure modes require manual intervention

**Risks:**
- **Early adopter risk:** You're testing software that hasn't been proven at scale
- **Breaking changes:** API may change in minor versions (until 2.0.0)
- **Limited support:** Community-driven support only (no SLA)

**Mitigation:**
- Start with non-critical use cases
- Test thoroughly on your specific workload
- Keep backups of important documents
- Report issues on GitHub: https://github.com/B-A-M-N/FlockParser/issues

---

## PDF Processing Limitations

### What We Handle Well

| PDF Type | Support Level | Notes |
|----------|---------------|-------|
| Text-based PDFs | ✅ Excellent | pdfplumber extracts reliably |
| Simple tables | ✅ Good | Table structure preserved |
| Images in PDFs | ✅ Good | OCR fallback with Tesseract |
| Modern PDFs (2010+) | ✅ Good | Standard encodings |

### Known Edge Cases

#### 1. **Encrypted/Password-Protected PDFs**

**Issue:** Extraction fails silently or returns empty text.

**Current behavior:**
```python
# Fails with: pypdf.errors.FileNotDecryptedError
```

**Workaround:**
- Decrypt PDFs manually first using `qpdf --decrypt --password=PASSWORD input.pdf output.pdf`
- Or use `pdftk` to remove password protection

**Planned fix:** v1.1.0 will prompt for password and retry.

---

#### 2. **Scanned Documents (Image-Only PDFs)**

**Issue:** OCR is slow and quality depends on scan resolution.

**Current behavior:**
- Falls back to Tesseract OCR automatically
- Processing time: ~10-30 seconds per page
- Accuracy: 80-95% depending on scan quality

**Limitations:**
- Handwritten text: Poor recognition
- Low DPI scans (<150 DPI): Unreliable
- Non-English text: Requires additional language packs

**Workaround:**
- Rescan at 300+ DPI for better results
- Install language packs: `sudo apt-get install tesseract-ocr-fra` (for French, etc.)
- Use `ocrmypdf` preprocessing: `pip install flockparser[ocr]`

**Known failures:**
- Extremely low-quality scans (pixelated, faded)
- Complex layouts with multiple columns
- Tables in scanned documents (structure lost)

---

#### 3. **Complex Layouts**

**Issue:** Multi-column layouts, text boxes, annotations may be extracted out of order.

**Example failure:**
```
Expected: "Column A text... Column B text..."
Actual:   "Column A line 1, Column B line 1, Column A line 2, Column B line 2..."
```

**Affected PDF types:**
- Academic papers with multiple columns
- Newspapers
- Magazine layouts
- PDFs with floating text boxes

**Current workaround:** None (requires manual post-processing)

**Planned fix:** v1.2.0 will add layout-aware extraction.

---

#### 4. **Form Fields**

**Issue:** Interactive PDF form fields are not extracted as structured data.

**Current behavior:**
- Field values may be extracted as plain text
- Field names are lost
- Checkboxes/radio buttons not detected

**Use case impact:** Legal documents, tax forms, surveys will lose structure.

**Workaround:** Use `pdftotext -layout` preprocessing or dedicated form extraction tools.

---

#### 5. **Non-Standard Fonts & Encodings**

**Issue:** Custom fonts or unusual encodings may cause garbled text.

**Example:**
```
Expected: "€50.00"
Actual:   "?50.00" or "â‚¬50.00"
```

**Affected PDFs:**
- Very old PDFs (pre-2000)
- PDFs from non-Western languages without embedded fonts
- PDFs created with buggy tools

**Workaround:** Re-save PDF in Adobe Acrobat or use `gs` (Ghostscript) to normalize.

---

#### 6. **Corrupted or Malformed PDFs**

**Issue:** Malformed PDF structure causes crashes or hangs.

**Current behavior:**
- May crash Python process (no graceful recovery)
- Hangs indefinitely on some corrupted PDFs

**Detection:** Check logs for:
```
ERROR: Failed to parse PDF: <exception>
```

**Workaround:**
- Repair PDF with `gs -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile=fixed.pdf input.pdf`
- Or use online PDF repair tools

**Planned fix:** v1.1.0 will add timeout and graceful failure.

---

## Performance & Scaling

### Documented Limits

| Metric | Single Node | 3-Node Cluster | Notes |
|--------|-------------|----------------|-------|
| **Document size** | 100 MB | 500 MB | Larger PDFs may OOM |
| **Total corpus** | 10 GB | 50 GB | Limited by ChromaDB SQLite backend |
| **Concurrent queries** | 10 | 50 | With 50-worker thread pool |
| **Embedding generation** | 100 chunks/sec (GPU) | 500 chunks/sec | Bottleneck at ~5 GPU nodes |
| **LLM inference** | 50 tokens/sec (A4000) | 500 tokens/sec | Model-dependent |
| **Network latency** | <10ms (LAN) | <100ms (WAN) | Higher latency degrades performance |

### Known Bottlenecks

#### 1. **ChromaDB SQLite Backend**

**Issue:** Concurrent writes cause database locking.

**Symptom:**
```
sqlite3.OperationalError: database is locked
```

**Current limit:** ~10 concurrent operations

**Impact:**
- Multi-user scenarios may experience delays
- High-throughput workloads may fail

**Workaround:**
- Use separate ChromaDB databases per interface
- Or upgrade to PostgreSQL backend (not officially supported yet)

**Planned fix:** v1.2.0 will add optional PostgreSQL support.

---

#### 2. **Memory Usage on Large Documents**

**Issue:** Large PDFs (>100 MB) may cause OOM errors.

**Current behavior:**
- Entire PDF loaded into memory during processing
- Embedding generation processes all chunks at once

**Memory formula:** ~10x PDF size during processing

**Example:**
- 100 MB PDF → ~1 GB RAM usage during processing

**Workaround:**
- Split large PDFs into smaller files
- Increase system swap space

**Planned fix:** v1.1.0 will add streaming processing.

---

#### 3. **Network Failure Handling**

**Issue:** Node failures mid-request may cause request to hang or fail.

**Current behavior:**
- 30-second timeout per node
- Failover to next node (automatic)
- But: Already-processed work is lost

**Failure scenarios:**
- Node goes offline mid-request → 30s delay, then retry on next node
- Network partition → All nodes on other side unreachable
- VRAM exhaustion → Node hangs (no timeout)

**Workaround:**
- Monitor nodes with `lb_stats`
- Remove unhealthy nodes manually

**Planned fix:** v1.1.0 will add health checks and graceful degradation.

---

#### 4. **VRAM Saturation**

**Issue:** When GPU VRAM is full, inference may hang indefinitely.

**Current behavior:**
- No VRAM usage verification (only checks available VRAM at start)
- Model loads may hang if VRAM is actually exhausted
- No automatic unloading of unused models

**Detection:** Check `nvidia-smi` output:
```bash
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

**Workaround:**
- Manually unload models: `ollama stop <model>`
- Restart Ollama service

**Planned fix:** v1.2.0 will add active VRAM monitoring and model eviction.

---

## Network & Distributed System Issues

### Node Discovery Limitations

**Issue:** Auto-discovery only works on same subnet.

**Current behavior:**
- Scans 192.168.x.0/24 or similar local subnets
- Cannot discover nodes across VLANs or different networks

**Workaround:** Manually configure nodes in `flockparsecli.py`:
```python
NODES = [
    {"url": "http://10.0.1.50:11434"},  # Different subnet
    {"url": "http://remote-node.example.com:11434"},  # DNS
]
```

---

### Network Latency Sensitivity

**Issue:** High latency (>100ms) degrades performance significantly.

**Measured impact:**
- 10ms latency: 5% overhead
- 50ms latency: 20% overhead
- 200ms latency: 50% overhead (worse than single node!)

**Recommendation:** Only use FlockParser over LAN or low-latency WAN (<50ms).

**Use case impact:**
- Multi-region clusters: Not recommended
- Cloud + local hybrid: Possible but slower
- VPN connections: Test latency first

---

### Split-Brain Scenarios

**Issue:** Network partition can cause state inconsistencies.

**Example:**
- Main node and GPU node 1 are on one side of partition
- GPU node 2 is on other side
- Both sides continue processing independently
- ChromaDB databases diverge

**Current mitigation:** None (single-master design)

**Workaround:** Ensure reliable networking or manually reconcile after partition heals.

---

## Security Concerns

### Authentication & Authorization

#### REST API

**Current state:**
- ✅ API key authentication (via `X-API-Key` header)
- ❌ No user management
- ❌ No role-based access control
- ❌ No rate limiting (can be DoS'd)

**Risk:**
- Anyone with API key has full access
- Single compromised key = full access
- No audit logging

**Mitigation:**
- Change default API key immediately
- Use strong random keys: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- Put behind reverse proxy (nginx) with rate limiting
- Use HTTPS (generate cert with Let's Encrypt)

**Planned:** v1.1.0 will add rate limiting and audit logs.

---

#### MCP Server

**Current state:**
- ❌ No authentication (stdio transport)
- ⚠️ Runs with same permissions as Claude Desktop
- ⚠️ Document snippets sent to Anthropic cloud

**Risk:**
- Any process can spawn MCP server and access documents
- Sensitive documents may be sent to Anthropic (privacy risk)

**Mitigation:**
- Only use MCP with non-sensitive documents
- Review Claude Desktop security settings
- Consider using CLI/Web UI for sensitive data

**Planned:** v1.2.0 will add MCP authentication.

---

### Data Security

#### Encryption at Rest

**Current state:**
- ❌ No encryption of ChromaDB database
- ❌ No encryption of processed documents in `converted_files/`
- ❌ No encryption of uploaded files in `uploads/`

**Risk:**
- Anyone with filesystem access can read all documents
- Disk theft = data breach

**Mitigation:**
- Use filesystem-level encryption (LUKS, BitLocker, FileVault)
- Set restrictive permissions: `chmod 700 chroma_db*/`
- Consider encrypted home directory

**Planned:** v1.3.0 may add application-level encryption.

---

#### Network Security

**Current state:**
- ⚠️ Ollama nodes communicate over plain HTTP (no TLS)
- ⚠️ Document content sent over network unencrypted
- ⚠️ No mutual TLS between nodes

**Risk:**
- Network sniffer can see all documents
- Man-in-the-middle attacks possible

**Mitigation:**
- Use VPN (WireGuard, Tailscale) for node-to-node communication
- Or use SSH tunnels: `ssh -L 11434:localhost:11434 user@node`
- Firewall rules to restrict access

**Planned:** v1.2.0 will document TLS setup with reverse proxy.

---

### Input Validation

**Current state:**
- ⚠️ Limited validation of PDF inputs
- ⚠️ No file size limits enforced
- ⚠️ No content scanning for malware

**Risk:**
- Malicious PDF could exploit parsing library vulnerabilities
- Zip bombs or large files could DoS the system
- PDF with embedded malware could be processed and stored

**Mitigation:**
- Run FlockParser in sandboxed environment (Docker, VM)
- Use antivirus scanning before processing
- Set file size limits in nginx: `client_max_body_size 100m;`

**Planned:** v1.1.0 will add file size limits and better validation.

---

## Test Coverage

### Current Coverage (Estimated)

| Component | Coverage | Test Type |
|-----------|----------|-----------|
| **Core parsing** | ~60% | Unit + smoke tests |
| **Distributed routing** | ~40% | Manual testing only |
| **ChromaDB integration** | ~50% | Smoke tests |
| **API endpoints** | ~30% | Manual testing |
| **MCP server** | ~20% | Manual testing |
| **Error handling** | ~25% | Minimal coverage |

### Test Gaps

**Missing tests:**
- ❌ No integration tests for multi-node scenarios
- ❌ No stress tests (100+ documents, high concurrency)
- ❌ No fuzz testing of PDF inputs
- ❌ No network failure simulation tests
- ❌ No VRAM exhaustion tests
- ❌ No security penetration tests

**CI/CD status:**
- ✅ GitHub Actions configured
- ✅ Smoke tests run on Python 3.10, 3.11, 3.12
- ✅ Linting with flake8 and black
- ❌ No coverage reporting
- ❌ No performance benchmarking in CI

**Planned:**
- v1.1.0: Add integration tests
- v1.1.0: Add code coverage reporting (target: 80%)
- v1.2.0: Add stress testing suite
- v1.2.0: Add security scanning (Bandit, safety)

---

## UI/UX Polish

### Web UI (Streamlit)

**Current state:**
- ✅ Functional interface
- ⚠️ Basic styling (Streamlit defaults)
- ❌ No progress bars for long operations
- ❌ Minimal error feedback
- ❌ No loading states

**Known issues:**
- Large PDF uploads may appear to hang (no progress indicator)
- Errors shown as raw exceptions (not user-friendly)
- No undo functionality
- No batch operations UI

**Planned:**
- v1.1.0: Add progress bars and loading states
- v1.1.0: Better error messages
- v1.2.0: Redesign UI with custom CSS

---

### CLI

**Current state:**
- ✅ Functional commands
- ⚠️ Basic help text
- ❌ No command completion
- ❌ No interactive mode enhancements

**Known issues:**
- Help text doesn't show all available commands
- No command history
- No syntax highlighting
- Error messages sometimes cryptic

**Planned:**
- v1.1.0: Add command autocompletion
- v1.1.0: Improve help system
- v1.2.0: Add rich formatting and colors

---

## Roadmap

### v1.1.0 (Target: 2025-11)

**Focus: Robustness & Error Handling**

- [ ] Graceful handling of encrypted PDFs (prompt for password)
- [ ] Timeout and recovery for corrupted PDFs
- [ ] Streaming processing for large PDFs (reduce memory usage)
- [ ] Health checks for nodes (automatic unhealthy node removal)
- [ ] Rate limiting for REST API
- [ ] File size limits and validation
- [ ] Progress indicators in Web UI
- [ ] Integration tests for multi-node scenarios
- [ ] Code coverage reporting (target: 80%)

---

### v1.2.0 (Target: 2025-Q1)

**Focus: Scaling & Security**

- [ ] Optional PostgreSQL backend for ChromaDB (remove SQLite locking issues)
- [ ] Active VRAM monitoring and model eviction
- [ ] Layout-aware PDF extraction (preserve columns)
- [ ] TLS documentation for secure node communication
- [ ] MCP authentication
- [ ] CLI command autocompletion
- [ ] Stress testing suite
- [ ] Prometheus metrics exporter

---

### v1.3.0 (Target: 2025-Q2)

**Focus: Features & Polish**

- [ ] Application-level encryption for ChromaDB
- [ ] PDF form field extraction
- [ ] Multi-language OCR support
- [ ] Web UI redesign (custom CSS)
- [ ] WebSocket support for streaming responses
- [ ] Document versioning
- [ ] Distributed cluster federation (multi-region)

---

### v2.0.0 (Target: 2025-Q3+)

**Focus: Production-Grade Platform**

- [ ] User management and RBAC
- [ ] Audit logging and compliance features
- [ ] Real-time collaboration features
- [ ] Cloud deployment templates (AWS, GCP, Azure)
- [ ] Managed service offering (optional)

---

## Contributing

Found an issue not listed here? Please report it:
https://github.com/B-A-M-N/FlockParser/issues

Want to help fix these issues?
- See [CONTRIBUTING.md](CONTRIBUTING.md)
- Check issues labeled `good-first-issue` or `help-wanted`

---

## Honest Assessment

**Is FlockParser production-ready?**

**For hobbyists / tinkerers:** Yes, with caveats. Great for learning distributed systems.

**For small teams (<10 users):** Maybe. Test thoroughly on your specific use case first.

**For enterprise / mission-critical:** Not yet. Wait for v1.2.0+ or be prepared to contribute fixes.

**Why use it anyway?**
- **Privacy:** 100% local processing (CLI/Web UI)
- **Cost:** No per-token charges (unlike cloud APIs)
- **Learning:** Real distributed systems to study and extend
- **Flexibility:** Full control over models and infrastructure

**Why wait?**
- **Stability:** Limited battle testing
- **Support:** Community-only (no SLA)
- **Security:** Gaps in authentication and encryption
- **Scale:** Known limits at ~50GB corpus and ~50 concurrent users

---

**Bottom line:** FlockParser is a powerful tool for those willing to be early adopters and contribute to its maturity. If you need rock-solid stability today, consider waiting for v1.2.0+ or using commercial alternatives.
