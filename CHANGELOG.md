# Changelog

All notable changes to FlockParser will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- MCP (Model Context Protocol) server integration with Claude Desktop
- Custom ThreadPoolExecutor (50 workers) for MCP concurrent request handling
- Timeout handling for all MCP operations (5min PDF, 1min search, 2min chat)
- Detailed error logging with stack traces for MCP debugging
- Absolute path resolution for ChromaDB to fix directory access from different working directories
- Privacy model documentation with clear warnings about MCP cloud usage
- Security section in README covering API keys, TLS, rate limiting, and database security
- VRAM detection method documentation (Ollama `/api/ps` endpoint)

### Changed
- Improved README structure with badges, ToC, and front-loaded privacy info
- Renamed project tagline to "Document RAG Intelligence with Distributed Processing"
- Clarified benchmark claims with specific hardware specs and test conditions
- Updated privacy warnings for all 4 interfaces (CLI, Web UI, REST API, MCP)

### Fixed
- ChromaDB database locking when running CLI and MCP server simultaneously
- Permission errors when MCP server runs from different working directory
- Python bytecode cache issues causing stale code execution

## [1.0.0] - 2025-10-01

### 🎉 Initial Public Release on PyPI

**Published:** https://pypi.org/project/flockparser/1.0.0/

FlockParser v1.0.0 is now publicly available and pip-installable!

#### Core Features Added
- CLI interface (`flockparsecli.py`) for local document processing
- Web UI interface (`flock_webui.py`) with Streamlit
- REST API interface (`flock_ai_api.py`) with FastAPI
- MCP Server interface for Claude Desktop integration
- Intelligent load balancer with auto-discovery of Ollama nodes
- Adaptive routing (sequential vs parallel) based on cluster characteristics (7.2x threshold)
- GPU and VRAM detection via Ollama `/api/ps` endpoint
- Health scoring system prioritizing GPU nodes (+200 for GPU, +100 for VRAM>8GB)
- ChromaDB vector store for persistent embeddings
- PDF processing with 3-tier fallback (pdfplumber → PyPDF2 → OCR)
- Multi-format conversion (TXT, MD, DOCX, JSON)
- RAG (Retrieval-Augmented Generation) with source citations
- MD5-based embedding cache to prevent reprocessing
- Model weight caching for faster repeated inference
- 4 routing strategies: adaptive, round-robin, least-loaded, lowest-latency
- Automatic failover and offline node handling
- Real-time performance tracking and node statistics
- Privacy-first architecture with 100% local processing option

#### Packaging & Distribution
- Published to PyPI as `flockparser`
- Console entry points: `flockparse`, `flockparse-webui`, `flockparse-api`, `flockparse-mcp`
- Docker support (Dockerfile + docker-compose.yml with 4 services)
- Modern pyproject.toml packaging
- GitHub Actions CI/CD (tests on Python 3.10, 3.11, 3.12)

#### Documentation Added
- Comprehensive README with embedded demo video
- 76-second demo video showing 61.7x speedup: https://youtu.be/M-HjXkWYRLM
- Architecture deep dive (500+ lines): `docs/architecture.md`
- Distributed setup guide (400+ lines): `DISTRIBUTED_SETUP.md`
- Known issues & limitations (900+ lines): `KNOWN_ISSUES.md`
- Security policy: `SECURITY.md`
- Error handling guide: `ERROR_HANDLING.md`
- Performance benchmarks: `BENCHMARKS.md`
- Contributing guidelines: `CONTRIBUTING.md`
- Code of Conduct: `CODE_OF_CONDUCT.md`
- Environment configuration template: `.env.example`

#### Performance (Measured)
- **Demo video results (unedited timing):**
  - Single CPU node: 372.76s
  - Parallel (3 nodes): 159.79s (2.3x speedup)
  - GPU routing: 6.04s (**61.7x speedup**)
- Tested up to 10,000 documents in corpus
- Handles PDFs up to 100 MB
- Sub-20ms search latency (ChromaDB with 100K chunks)
- 21.7x GPU speedup for embedding generation (RTX A4000 vs i9-12900K)

#### Known Limitations
See [KNOWN_ISSUES.md](KNOWN_ISSUES.md) for comprehensive list:
- Beta status - limited battle testing
- ~40% test coverage (target: 80% in v1.1.0)
- ChromaDB SQLite backend limits concurrency (~10 writes/sec)
- Some PDF edge cases not handled (encrypted, complex layouts)
- No rate limiting in REST API
- UI needs polish (progress bars, better errors)

#### Security Considerations
See [SECURITY.md](SECURITY.md) for full policy:
- REST API requires manual API key change
- No encryption at rest by default
- Ollama nodes use plain HTTP
- MCP server sends snippets to Anthropic cloud

---

## Version History

- **[Unreleased]** - MCP integration, security hardening, improved docs
- **[1.0.0]** - Initial release with 4 interfaces and distributed processing
