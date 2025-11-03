"""
Core functionality tests for FlockParser
Tests PDF processing, text chunking, and document management
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flockparsecli import (
    chunk_text,
    sanitize_for_xml,
    cosine_similarity,
    load_document_index,
    save_document_index,
    register_document,
)


class TestTextChunking:
    """Test text chunking functionality"""

    def test_chunk_text_basic(self):
        """Test basic text chunking"""
        # chunk_size is in TOKENS (1 token ≈ 4 chars)
        # MAX_CHARS = 1920, so need >1920 chars to force split
        text = "This is a test sentence. " * 100  # ~2500 chars
        chunks = chunk_text(text, chunk_size=512, overlap=100)

        assert len(chunks) >= 1, "Should create at least one chunk"
        assert all(isinstance(c, str) for c in chunks), "All chunks should be strings"
        # Each chunk should respect MAX_CHARS limit (1920)
        assert all(len(c) <= 2000 for c in chunks), "Chunks shouldn't exceed MAX_CHARS"

    def test_chunk_text_with_paragraphs(self):
        """Test chunking with paragraph breaks"""
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = chunk_text(text, chunk_size=512, overlap=100)

        # Should keep paragraphs together if they fit
        assert len(chunks) >= 1
        assert isinstance(chunks[0], str)

    def test_chunk_text_empty_string(self):
        """Test chunking empty string"""
        chunks = chunk_text("", chunk_size=100, overlap=10)
        # Empty string results in empty list
        assert chunks == [] or chunks == [""], "Empty string should return empty or single empty chunk"

    def test_chunk_text_single_chunk(self):
        """Test text smaller than MAX_CHARS"""
        text = "Short text that fits in one chunk"
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        assert len(chunks) == 1, "Short text should create single chunk"
        assert chunks[0] == text, "Single chunk should match original text"

    def test_chunk_text_very_long(self):
        """Test text much larger than MAX_CHARS"""
        # Create text > 4000 chars to force multiple chunks
        text = "This is a test sentence. " * 200  # ~5000 chars
        chunks = chunk_text(text, chunk_size=512, overlap=100)

        # Should split into multiple chunks
        assert len(chunks) >= 2, "Long text should create multiple chunks"
        # Each chunk respects MAX_CHARS
        assert all(len(c) <= 2000 for c in chunks)


class TestXMLSanitization:
    """Test XML sanitization for MCP protocol"""

    def test_sanitize_basic_text(self):
        """Test sanitizing normal text"""
        text = "This is normal text"
        result = sanitize_for_xml(text)
        assert result == text, "Normal text should pass through unchanged"

    def test_sanitize_keeps_xml_chars(self):
        """Test that XML chars are NOT escaped (just removes control chars)"""
        text = "Test <tag> & 'quotes' \"double\""
        result = sanitize_for_xml(text)

        # sanitize_for_xml does NOT escape, just removes control chars
        assert result == text, "XML chars should remain unchanged"

    def test_sanitize_control_characters(self):
        """Test removing control characters"""
        text = "Text\x00with\x01control\x02chars"
        result = sanitize_for_xml(text)

        # Control characters should be removed
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x02" not in result
        assert "Text" in result
        assert "with" in result

    def test_sanitize_none_input(self):
        """Test handling None input"""
        # Function doesn't handle None, will raise AttributeError
        try:
            result = sanitize_for_xml(None)
            assert False, "Should raise error for None"
        except AttributeError:
            pass  # Expected

    def test_sanitize_unicode(self):
        """Test handling unicode characters"""
        text = "Test unicode: café, naïve, 中文"
        result = sanitize_for_xml(text)
        # Unicode should pass through
        assert "café" in result
        assert "中文" in result


class TestCosineSimilarity:
    """Test cosine similarity calculation"""

    def test_identical_vectors(self):
        """Test similarity of identical vectors"""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0, 3.0]
        similarity = cosine_similarity(vec1, vec2)

        assert 0.99 <= similarity <= 1.01, "Identical vectors should have similarity ~1.0"

    def test_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors"""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = cosine_similarity(vec1, vec2)

        assert -0.1 <= similarity <= 0.1, "Orthogonal vectors should have similarity ~0.0"

    def test_opposite_vectors(self):
        """Test similarity of opposite vectors"""
        vec1 = [1.0, 1.0, 1.0]
        vec2 = [-1.0, -1.0, -1.0]
        similarity = cosine_similarity(vec1, vec2)

        assert -1.01 <= similarity <= -0.99, "Opposite vectors should have similarity ~-1.0"

    def test_different_length_vectors(self):
        """Test handling vectors of different lengths"""
        vec1 = [1.0, 2.0]
        vec2 = [1.0, 2.0, 3.0]

        # Should either handle gracefully or raise appropriate error
        try:
            similarity = cosine_similarity(vec1, vec2)
            # If it doesn't raise, verify result is reasonable
            assert -1.1 <= similarity <= 1.1
        except (ValueError, IndexError):
            # Expected for different length vectors
            pass

    def test_zero_vector(self):
        """Test handling zero vector"""
        vec1 = [0.0, 0.0, 0.0]
        vec2 = [1.0, 2.0, 3.0]

        # Should handle zero vector gracefully (either return 0 or handle error)
        try:
            similarity = cosine_similarity(vec1, vec2)
            assert similarity == 0.0 or similarity is None
        except (ZeroDivisionError, ValueError):
            # Expected for zero vector
            pass


class TestDocumentIndex:
    """Test document index management"""

    def test_load_document_index_creates_default(self):
        """Test that load_document_index creates default structure"""
        with patch("flockparsecli.INDEX_FILE", Path(tempfile.mktemp())):
            index = load_document_index()

            assert isinstance(index, dict), "Should return dict"
            assert "documents" in index, "Should have documents key"
            assert isinstance(index["documents"], list), "documents should be list"

    def test_save_and_load_document_index(self):
        """Test saving and loading document index"""
        temp_index = Path(tempfile.mktemp(suffix=".json"))

        try:
            test_data = {
                "documents": [
                    {
                        "id": "test123",
                        "original": "/path/to/doc.pdf",
                        "text_path": "/path/to/doc.txt",
                        "processed_date": "2025-01-01",
                    }
                ]
            }

            with patch("flockparsecli.INDEX_FILE", temp_index):
                save_document_index(test_data)
                loaded = load_document_index()

            assert loaded["documents"][0]["id"] == "test123"
            assert len(loaded["documents"]) == 1

        finally:
            if temp_index.exists():
                temp_index.unlink()

    def test_register_document(self):
        """Test registering a new document"""
        temp_index = Path(tempfile.mktemp(suffix=".json"))

        try:
            with patch("flockparsecli.INDEX_FILE", temp_index):
                # Register a document
                doc_id = register_document(
                    pdf_path="/test/doc.pdf",
                    txt_path="/test/doc.txt",
                    content="Test content",
                    chunks=["chunk1", "chunk2"],
                )

                assert isinstance(doc_id, str), "Should return document ID"

                # Verify it was saved
                index = load_document_index()
                assert len(index["documents"]) > 0

                # Find our document
                doc = next((d for d in index["documents"] if d["id"] == doc_id), None)
                assert doc is not None, "Document should be in index"
                assert doc["original"] == "/test/doc.pdf"
                assert len(doc["chunks"]) == 2

        finally:
            if temp_index.exists():
                temp_index.unlink()


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_chunk_text_negative_size(self):
        """Test chunking with negative chunk size"""
        text = "Test text"

        # Function doesn't validate, will use negative * 4 for TARGET_CHARS
        # But MAX_CHARS is still 1920, so short text returns as-is
        chunks = chunk_text(text, chunk_size=-10, overlap=5)
        assert isinstance(chunks, list)
        assert len(chunks) >= 1

    def test_chunk_text_zero_size(self):
        """Test chunking with zero chunk size"""
        text = "Test text"

        # chunk_size=0 → TARGET_CHARS=0, but MAX_CHARS=1920 still applies
        chunks = chunk_text(text, chunk_size=0, overlap=0)
        assert isinstance(chunks, list)
        # Short text fits in MAX_CHARS
        assert len(chunks) == 1

    def test_sanitize_very_long_text(self):
        """Test sanitizing very long text"""
        text = "A" * 100000  # 100K characters
        result = sanitize_for_xml(text)

        assert isinstance(result, str)
        assert len(result) == 100000  # No chars removed
        assert result == text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
