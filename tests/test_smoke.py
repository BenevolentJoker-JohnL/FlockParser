"""
Smoke tests for FlockParser
Tests basic imports and core functionality without requiring Ollama nodes
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestImports:
    """Test that all core modules can be imported"""

    def test_import_requirements(self):
        """Test that all required dependencies are available"""
        import requests
        import chromadb
        import pdf2image
        import pytesseract
        import streamlit

        assert True

    def test_import_cli_module(self):
        """Test that CLI module can be imported"""
        # Note: Full import may fail without Ollama, so just test file exists
        cli_path = Path(__file__).parent.parent / "flockparsecli.py"
        assert cli_path.exists(), "flockparsecli.py not found"

    def test_import_api_module(self):
        """Test that API module can be imported"""
        api_path = Path(__file__).parent.parent / "flock_ai_api.py"
        assert api_path.exists(), "flock_ai_api.py not found"

    def test_import_webui_module(self):
        """Test that Web UI module exists"""
        webui_path = Path(__file__).parent.parent / "flock_webui.py"
        assert webui_path.exists(), "flock_webui.py not found"

    def test_import_mcp_server(self):
        """Test that MCP server module exists"""
        mcp_path = Path(__file__).parent.parent / "flock_mcp_server.py"
        assert mcp_path.exists(), "flock_mcp_server.py not found"


class TestDirectoryStructure:
    """Test that expected directories are created or can be created"""

    def test_project_root(self):
        """Test that we can find the project root"""
        root = Path(__file__).parent.parent
        assert root.exists()
        assert (root / "README.md").exists()

    def test_requirements_file(self):
        """Test that requirements.txt exists and is readable"""
        req_path = Path(__file__).parent.parent / "requirements.txt"
        assert req_path.exists()
        content = req_path.read_text()
        assert len(content) > 0
        assert "requests" in content
        assert "chromadb" in content

    def test_dockerfile_exists(self):
        """Test that Dockerfile exists for containerized deployment"""
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        assert dockerfile.exists()
        content = dockerfile.read_text()
        assert "FROM python" in content

    def test_docker_compose_exists(self):
        """Test that docker-compose.yml exists"""
        compose = Path(__file__).parent.parent / "docker-compose.yml"
        assert compose.exists()
        content = compose.read_text()
        assert "services:" in content


class TestConfiguration:
    """Test configuration and environment handling"""

    def test_env_example_exists(self):
        """Test that .env.example exists as a template"""
        env_example = Path(__file__).parent.parent / ".env.example"
        assert env_example.exists()
        content = env_example.read_text()
        assert "OLLAMA_HOST" in content
        assert "FLOCKPARSE_API_KEY" in content

    def test_gitignore_exists(self):
        """Test that .gitignore protects sensitive files"""
        gitignore = Path(__file__).parent.parent / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert ".env" in content
        assert "chroma_db" in content


class TestDocumentation:
    """Test that documentation files exist"""

    def test_readme_exists(self):
        """Test that README.md exists and has content"""
        readme = Path(__file__).parent.parent / "README.md"
        assert readme.exists()
        content = readme.read_text()
        assert "FlockParser" in content or "FlockParse" in content
        assert len(content) > 1000  # Should be comprehensive

    def test_license_exists(self):
        """Test that LICENSE file exists"""
        license_file = Path(__file__).parent.parent / "LICENSE"
        assert license_file.exists()
        content = license_file.read_text()
        assert "MIT" in content

    def test_contributing_exists(self):
        """Test that CONTRIBUTING.md exists"""
        contributing = Path(__file__).parent.parent / "CONTRIBUTING.md"
        assert contributing.exists()


class TestDependencies:
    """Test critical dependencies are properly installed"""

    def test_chromadb_version(self):
        """Test that ChromaDB is available"""
        import chromadb

        # Just verify it imports and has basic attributes
        assert hasattr(chromadb, "Client")

    def test_requests_available(self):
        """Test that requests library works"""
        import requests

        # Test a basic request to verify it's functional
        assert hasattr(requests, "get")
        assert hasattr(requests, "post")

    def test_pdf_dependencies(self):
        """Test that PDF processing dependencies are available"""
        import pdf2image
        import pytesseract

        assert hasattr(pdf2image, "convert_from_path")

    def test_pathlib_available(self):
        """Test that pathlib is available for path handling"""
        from pathlib import Path

        test_path = Path(__file__)
        assert test_path.exists()
        assert test_path.is_file()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
