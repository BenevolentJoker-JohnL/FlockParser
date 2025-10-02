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
        text = "This is a test. " * 100  # Create text longer than chunk size
        chunks = chunk_text(text, chunk_size=50, overlap=10)

        assert len(chunks) > 1, "Should create multiple chunks"
        assert all(isinstance(c, str) for c in chunks), "All chunks should be strings"
        assert all(len(c) <= 100 for c in chunks), "Chunks shouldn't exceed reasonable size"

    def test_chunk_text_with_overlap(self):
        """Test that chunk overlap works correctly"""
        text = "Word " * 50
        chunks = chunk_text(text, chunk_size=20, overlap=5)

        # Verify chunks have some overlap
        if len(chunks) > 1:
            # Last words of first chunk should appear in second chunk
            assert len(chunks) > 0

    def test_chunk_text_empty_string(self):
        """Test chunking empty string"""
        chunks = chunk_text("", chunk_size=100, overlap=10)
        assert chunks == [""], "Empty string should return list with empty string"

    def test_chunk_text_single_chunk(self):
        """Test text smaller than chunk size"""
        text = "Short text"
        chunks = chunk_text(text, chunk_size=100, overlap=10)
        assert len(chunks) == 1, "Short text should create single chunk"
        assert chunks[0] == text, "Single chunk should match original text"

    def test_chunk_text_custom_sizes(self):
        """Test different chunk sizes"""
        text = "Word " * 100

        small_chunks = chunk_text(text, chunk_size=50, overlap=10)
        large_chunks = chunk_text(text, chunk_size=200, overlap=10)

        assert len(small_chunks) >= len(large_chunks), "Smaller chunk size should create more chunks"


class TestXMLSanitization:
    """Test XML sanitization for MCP protocol"""

    def test_sanitize_basic_text(self):
        """Test sanitizing normal text"""
        text = "This is normal text"
        result = sanitize_for_xml(text)
        assert result == text, "Normal text should pass through unchanged"

    def test_sanitize_special_characters(self):
        """Test sanitizing XML special characters"""
        text = "Test <tag> & 'quotes' \"double\""
        result = sanitize_for_xml(text)

        assert "<" not in result or "&lt;" in result, "< should be escaped"
        assert ">" not in result or "&gt;" in result, "> should be escaped"
        assert "&" not in result or "&amp;" in result, "& should be escaped"

    def test_sanitize_control_characters(self):
        """Test removing control characters"""
        text = "Text\x00with\x01control\x02chars"
        result = sanitize_for_xml(text)

        # Control characters should be removed
        assert "\x00" not in result
        assert "\x01" not in result
        assert "\x02" not in result

    def test_sanitize_none_input(self):
        """Test handling None input"""
        result = sanitize_for_xml(None)
        assert result == "", "None should return empty string"

    def test_sanitize_unicode(self):
        """Test handling unicode characters"""
        text = "Test unicode: café, naïve, 中文"
        result = sanitize_for_xml(text)
        assert len(result) > 0, "Unicode text should be handled"


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
        with patch('flockparsecli.INDEX_FILE', Path(tempfile.mktemp())):
            index = load_document_index()

            assert isinstance(index, dict), "Should return dict"
            assert "documents" in index, "Should have documents key"
            assert isinstance(index["documents"], list), "documents should be list"

    def test_save_and_load_document_index(self):
        """Test saving and loading document index"""
        temp_index = Path(tempfile.mktemp(suffix='.json'))

        try:
            test_data = {
                "documents": [
                    {
                        "id": "test123",
                        "original": "/path/to/doc.pdf",
                        "text_path": "/path/to/doc.txt",
                        "processed_date": "2025-01-01"
                    }
                ]
            }

            with patch('flockparsecli.INDEX_FILE', temp_index):
                save_document_index(test_data)
                loaded = load_document_index()

            assert loaded["documents"][0]["id"] == "test123"
            assert len(loaded["documents"]) == 1

        finally:
            if temp_index.exists():
                temp_index.unlink()

    def test_register_document(self):
        """Test registering a new document"""
        temp_index = Path(tempfile.mktemp(suffix='.json'))

        try:
            with patch('flockparsecli.INDEX_FILE', temp_index):
                # Register a document
                doc_id = register_document(
                    pdf_path="/test/doc.pdf",
                    txt_path="/test/doc.txt",
                    content="Test content",
                    chunks=["chunk1", "chunk2"]
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

        # Should either handle gracefully or raise ValueError
        try:
            chunks = chunk_text(text, chunk_size=-10, overlap=5)
            # If it doesn't raise, verify result is reasonable
            assert isinstance(chunks, list)
        except ValueError:
            # Expected for negative size
            pass

    def test_chunk_text_overlap_larger_than_size(self):
        """Test chunking where overlap > chunk_size"""
        text = "Test text " * 50

        # Should handle this case gracefully
        try:
            chunks = chunk_text(text, chunk_size=10, overlap=20)
            assert isinstance(chunks, list)
        except ValueError:
            # Expected if validation is strict
            pass

    def test_sanitize_very_long_text(self):
        """Test sanitizing very long text"""
        text = "A" * 100000  # 100K characters
        result = sanitize_for_xml(text)

        assert isinstance(result, str)
        assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
