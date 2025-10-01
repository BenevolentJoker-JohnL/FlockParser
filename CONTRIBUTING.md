# Contributing to FlockParser

Thanks for your interest in contributing! This document provides guidelines for contributing to FlockParser.

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/FlockParser.git
   cd FlockParser
   ```
3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install development dependencies (if any)
pip install pytest black flake8

# Start Ollama
ollama serve
ollama pull mxbai-embed-large
ollama pull llama3.1:latest

# Run the CLI to test
python flockparsecli.py
```

## Making Changes

### Code Style

- Follow PEP 8 Python style guidelines
- Use descriptive variable and function names
- Add docstrings to functions and classes
- Keep functions focused and single-purpose

### Testing Your Changes

```bash
# Test the CLI interface
python flockparsecli.py

# Test with a sample PDF
> open_pdf testpdfs/sample.pdf
> chat

# Test the Web UI
streamlit run flock_webui.py

# Test the REST API
python flock_ai_api.py
# In another terminal:
curl -H "X-API-Key: your-secret-api-key-change-this" http://localhost:8000/
```

### Commit Messages

Write clear, concise commit messages:

```
Add feature: Brief description

- More detailed explanation if needed
- Why the change was made
- Any breaking changes or migration notes
```

**Good examples:**
- `Fix: Prevent ChromaDB database locking with concurrent processes`
- `Add: VRAM monitoring via Ollama /api/ps endpoint`
- `Refactor: Consolidate health scoring logic into single function`

**Bad examples:**
- `fix stuff`
- `update code`
- `changes`

## Pull Request Process

1. **Update documentation** - If you changed functionality, update the README.md
2. **Test thoroughly** - Make sure your changes work with all interfaces (CLI, Web UI, API, MCP)
3. **Check for conflicts** - Rebase on latest main if needed
4. **Submit PR** with:
   - Clear description of what changed and why
   - Reference any related issues (e.g., "Fixes #123")
   - Screenshots/logs if UI or performance changes
   - Note any breaking changes

### PR Checklist

- [ ] Code follows PEP 8 style guidelines
- [ ] Changes tested locally on at least 2 interfaces
- [ ] Documentation updated (README, docstrings, etc.)
- [ ] No hardcoded credentials or secrets
- [ ] Commit messages are clear and descriptive

## Types of Contributions

### Bug Fixes

- Check [Issues](https://github.com/yourusername/FlockParser/issues) for known bugs
- Create an issue first if bug is not already reported
- Include reproduction steps, expected vs actual behavior
- Fix and test thoroughly before submitting PR

### New Features

- Open an issue to discuss the feature first
- Explain the use case and why it's valuable
- Get feedback before investing significant time
- Keep features focused and aligned with project goals

### Documentation

- Fix typos, unclear explanations, or outdated info
- Add examples and use cases
- Improve code comments and docstrings
- Update troubleshooting guides

### Performance Improvements

- Include benchmarks showing improvement
- Document test methodology (hardware, dataset, commands)
- Explain trade-offs if any (e.g., memory vs speed)
- Profile before and after if possible

## What We're Looking For

**High Priority:**
- Bug fixes with clear reproduction steps
- Performance improvements with benchmarks
- Documentation improvements
- Security fixes (report privately first)
- Privacy enhancements

**Medium Priority:**
- New routing strategies for load balancer
- Additional file format support (EPUB, HTML, etc.)
- Improved error handling and logging
- Test coverage

**Low Priority / Needs Discussion:**
- Major architectural changes
- New external dependencies
- UI redesigns
- Breaking changes to existing APIs

## What We're NOT Looking For

- ❌ Unrelated feature additions (keep focused on document RAG + distributed processing)
- ❌ Code reformatting without functional changes
- ❌ Dependencies that increase install complexity significantly
- ❌ Features that compromise privacy in default local modes
- ❌ Changes that break existing CLI/API interfaces without migration path

## Questions?

- Check existing [Issues](https://github.com/yourusername/FlockParser/issues) and [Discussions](https://github.com/yourusername/FlockParser/discussions)
- Open a new issue with the "question" label
- Be specific and include context

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
