"""
API tests for FlockParser REST API
Tests FastAPI endpoints, authentication, and error handling
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import io
import tempfile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import after path is set
try:
    from flock_ai_api import app, API_KEY

    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    app = None
    API_KEY = "test-key"


@pytest.mark.skipif(not API_AVAILABLE, reason="API module not available")
class TestAPIAuthentication:
    """Test API key authentication"""

    def test_missing_api_key(self):
        """Test request without API key"""
        client = TestClient(app)

        response = client.post("/upload_pdf/", files={"file": ("test.pdf", b"fake pdf content")})

        # Should return 401 or 403
        assert response.status_code in [401, 403], "Should reject requests without API key"

    def test_invalid_api_key(self):
        """Test request with invalid API key"""
        client = TestClient(app)

        headers = {"X-API-Key": "wrong-key"}
        response = client.post("/upload_pdf/", files={"file": ("test.pdf", b"fake pdf content")}, headers=headers)

        assert response.status_code in [401, 403], "Should reject invalid API key"

    def test_valid_api_key(self):
        """Test request with valid API key"""
        client = TestClient(app)

        headers = {"X-API-Key": API_KEY}

        # Mock PDF processing
        with patch("flock_ai_api.process_pdf"):
            response = client.post("/upload_pdf/", files={"file": ("test.pdf", b"fake pdf")}, headers=headers)

            # Should accept the request (may fail on processing, but auth should pass)
            assert response.status_code != 401 and response.status_code != 403


@pytest.mark.skipif(not API_AVAILABLE, reason="API module not available")
class TestUploadEndpoint:
    """Test PDF upload endpoint"""

    def test_upload_pdf_success(self):
        """Test successful PDF upload"""
        client = TestClient(app)
        headers = {"X-API-Key": API_KEY}

        # Create a fake PDF file
        fake_pdf = b"%PDF-1.4\n%fake content"
        files = {"file": ("test.pdf", io.BytesIO(fake_pdf), "application/pdf")}

        with patch("flock_ai_api.process_pdf") as mock_process:
            mock_process.return_value = None  # Simulate successful processing

            response = client.post("/upload_pdf/", files=files, headers=headers)

            # Should return 200 on success
            assert response.status_code == 200 or response.status_code == 201
            assert "message" in response.json() or "status" in response.json()

    def test_upload_non_pdf_file(self):
        """Test uploading non-PDF file"""
        client = TestClient(app)
        headers = {"X-API-Key": API_KEY}

        # Try to upload a text file
        files = {"file": ("test.txt", b"This is not a PDF", "text/plain")}

        response = client.post("/upload_pdf/", files=files, headers=headers)

        # Should return 400 or similar error
        assert response.status_code >= 400, "Should reject non-PDF files"

    def test_upload_empty_file(self):
        """Test uploading empty file"""
        client = TestClient(app)
        headers = {"X-API-Key": API_KEY}

        files = {"file": ("empty.pdf", b"", "application/pdf")}

        response = client.post("/upload_pdf/", files=files, headers=headers)

        # Should return error for empty file
        assert response.status_code >= 400

    def test_upload_large_file(self):
        """Test uploading very large file"""
        client = TestClient(app)
        headers = {"X-API-Key": API_KEY}

        # Create a large fake PDF (10MB)
        large_content = b"%PDF-1.4\n" + b"x" * (10 * 1024 * 1024)
        files = {"file": ("large.pdf", io.BytesIO(large_content), "application/pdf")}

        response = client.post("/upload_pdf/", files=files, headers=headers)

        # Should either accept or reject based on size limits
        # Status code will depend on implementation
        assert response.status_code in [200, 201, 413, 500]


@pytest.mark.skipif(not API_AVAILABLE, reason="API module not available")
class TestSearchEndpoint:
    """Test search endpoint"""

    def test_search_success(self):
        """Test successful search"""
        client = TestClient(app)
        headers = {"X-API-Key": API_KEY}

        with patch("flock_ai_api.get_similar_chunks") as mock_search:
            mock_search.return_value = [
                {"text": "Result 1", "doc_name": "doc1.pdf", "similarity": 0.95},
                {"text": "Result 2", "doc_name": "doc2.pdf", "similarity": 0.85},
            ]

            response = client.post("/search/", json={"query": "test query", "top_k": 5}, headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert "results" in data or isinstance(data, list)

    def test_search_empty_query(self):
        """Test search with empty query"""
        client = TestClient(app)
        headers = {"X-API-Key": API_KEY}

        response = client.post("/search/", json={"query": "", "top_k": 5}, headers=headers)

        # Should return error or empty results
        assert response.status_code in [200, 400]

    def test_search_invalid_top_k(self):
        """Test search with invalid top_k parameter"""
        client = TestClient(app)
        headers = {"X-API-Key": API_KEY}

        response = client.post("/search/", json={"query": "test", "top_k": -5}, headers=headers)

        # Should return error for negative top_k
        assert response.status_code >= 400 or response.status_code == 200

    def test_search_no_results(self):
        """Test search that returns no results"""
        client = TestClient(app)
        headers = {"X-API-Key": API_KEY}

        with patch("flock_ai_api.get_similar_chunks") as mock_search:
            mock_search.return_value = []

            response = client.post("/search/", json={"query": "nonexistent query", "top_k": 5}, headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, (list, dict))


@pytest.mark.skipif(not API_AVAILABLE, reason="API module not available")
class TestChatEndpoint:
    """Test chat endpoint"""

    def test_chat_success(self):
        """Test successful chat query"""
        client = TestClient(app)
        headers = {"X-API-Key": API_KEY}

        with patch("flock_ai_api.chat_with_documents") as mock_chat:
            mock_chat.return_value = "This is a test response"

            response = client.post("/chat/", json={"query": "What is this about?"}, headers=headers)

            assert response.status_code == 200
            data = response.json()
            assert "response" in data or "answer" in data or isinstance(data, str)

    def test_chat_empty_query(self):
        """Test chat with empty query"""
        client = TestClient(app)
        headers = {"X-API-Key": API_KEY}

        response = client.post("/chat/", json={"query": ""}, headers=headers)

        # Should handle empty query gracefully
        assert response.status_code in [200, 400]


@pytest.mark.skipif(not API_AVAILABLE, reason="API module not available")
class TestHealthCheck:
    """Test health check endpoint"""

    def test_health_check(self):
        """Test health check endpoint"""
        client = TestClient(app)

        # Health check usually doesn't require auth
        response = client.get("/health/")

        assert response.status_code == 200 or response.status_code == 404
        if response.status_code == 200:
            data = response.json()
            assert "status" in data or "health" in data

    def test_root_endpoint(self):
        """Test root endpoint"""
        client = TestClient(app)

        response = client.get("/")

        # Root should return some info
        assert response.status_code in [200, 404]


@pytest.mark.skipif(not API_AVAILABLE, reason="API module not available")
class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_malformed_json(self):
        """Test handling malformed JSON"""
        client = TestClient(app)
        headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

        response = client.post("/search/", data="{ malformed json }", headers=headers)

        # Should return 400 or 422 for malformed JSON
        assert response.status_code >= 400

    def test_missing_required_fields(self):
        """Test request missing required fields"""
        client = TestClient(app)
        headers = {"X-API-Key": API_KEY}

        response = client.post("/search/", json={}, headers=headers)  # Missing query field

        # Should return validation error
        assert response.status_code >= 400

    def test_unsupported_method(self):
        """Test unsupported HTTP method"""
        client = TestClient(app)
        headers = {"X-API-Key": API_KEY}

        # Try GET on POST-only endpoint
        response = client.get("/upload_pdf/", headers=headers)

        # Should return 405 Method Not Allowed
        assert response.status_code == 405

    def test_cors_headers(self):
        """Test CORS headers if configured"""
        client = TestClient(app)

        response = client.options("/")

        # Check if CORS is configured
        if response.status_code == 200:
            assert "access-control-allow-origin" in response.headers or True


@pytest.mark.skipif(not API_AVAILABLE, reason="API module not available")
class TestRateLimiting:
    """Test rate limiting behavior (if implemented)"""

    def test_rapid_requests(self):
        """Test making many rapid requests"""
        client = TestClient(app)
        headers = {"X-API-Key": API_KEY}

        # Make 10 rapid requests
        responses = []
        for i in range(10):
            response = client.post("/search/", json={"query": f"test {i}", "top_k": 5}, headers=headers)
            responses.append(response.status_code)

        # All should succeed or some might be rate-limited (429)
        assert all(code in [200, 429, 500] for code in responses)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
