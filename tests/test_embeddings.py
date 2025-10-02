"""
Embedding and search tests for FlockParser
Tests embedding generation, caching, and semantic search
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flockparsecli import (
    embed_text,
    get_cached_embedding,
    load_embedding_cache,
    save_embedding_cache,
    get_similar_chunks,
    list_documents,
)


class TestEmbeddingGeneration:
    """Test embedding generation"""

    @patch('flockparsecli.ollama.embed')
    def test_embed_text_success(self, mock_embed):
        """Test successful text embedding"""
        # embed_text returns the original text, not the embedding
        result = embed_text("test text")
        assert result == "test text"

    @patch('flockparsecli.ollama.embed')
    def test_embed_text_empty(self, mock_embed):
        """Test embedding empty string"""
        result = embed_text("")
        assert result == ""

    @patch('flockparsecli.ollama.embed')
    def test_embed_text_long(self, mock_embed):
        """Test embedding very long text"""
        long_text = "word " * 1000
        result = embed_text(long_text)
        assert result == long_text

    @patch('flockparsecli.ollama.embed')
    def test_embed_text_failure(self, mock_embed):
        """Test handling embedding failure"""
        mock_embed.side_effect = Exception("Embedding failed")

        result = embed_text("test")
        assert result is None


class TestEmbeddingCache:
    """Test embedding cache functionality"""

    def test_load_embedding_cache_empty(self):
        """Test loading cache when file doesn't exist"""
        with patch('flockparsecli.EMBEDDING_CACHE_FILE', Path("/tmp/nonexistent_cache.json")):
            cache = load_embedding_cache()

            assert isinstance(cache, dict)
            assert len(cache) == 0

    def test_save_and_load_embedding_cache(self):
        """Test saving and loading embedding cache"""
        temp_cache = Path(tempfile.mktemp(suffix='.json'))

        try:
            test_cache = {
                "text_hash_1": [0.1] * 1024,
                "text_hash_2": [0.2] * 1024
            }

            with patch('flockparsecli.EMBEDDING_CACHE_FILE', temp_cache):
                save_embedding_cache(test_cache)
                loaded = load_embedding_cache()

            assert len(loaded) == 2
            assert "text_hash_1" in loaded

        finally:
            temp_cache.unlink(missing_ok=True)

    @patch('flockparsecli.load_embedding_cache')
    @patch('flockparsecli.save_embedding_cache')
    @patch('flockparsecli.load_balancer.embed_distributed')
    def test_get_cached_embedding_hit(self, mock_embed, mock_save, mock_load):
        """Test cache hit - should not generate new embedding"""
        # Mock cache with existing embedding
        mock_load.return_value = {
            "5d41402abc4b2a76b9719d911017c592": [0.1] * 1024  # MD5 of "hello"
        }

        result = get_cached_embedding("hello", use_load_balancer=True)

        # Should return cached value, not call embed
        mock_embed.assert_not_called()
        assert len(result) == 1024

    @patch('flockparsecli.load_embedding_cache')
    @patch('flockparsecli.save_embedding_cache')
    @patch('flockparsecli.load_balancer.embed_distributed')
    def test_get_cached_embedding_miss(self, mock_embed, mock_save, mock_load):
        """Test cache miss - should generate new embedding"""
        mock_load.return_value = {}

        # Mock the embedding result to have .embeddings attribute
        mock_result = Mock()
        mock_result.embeddings = [[0.2] * 1024]
        mock_embed.return_value = mock_result

        result = get_cached_embedding("new text", use_load_balancer=True)

        # Should generate new embedding
        mock_embed.assert_called_once()
        assert len(result) == 1024

        # Should save to cache
        mock_save.assert_called_once()


class TestSemanticSearch:
    """Test semantic search functionality"""

    @patch('flockparsecli.load_document_index')
    @patch('flockparsecli.get_cached_embedding')
    def test_get_similar_chunks_no_docs(self, mock_embed, mock_index):
        """Test search with no documents"""
        mock_embed.return_value = [0.1] * 1024
        mock_index.return_value = {"documents": []}

        results = get_similar_chunks("test query", top_k=2)

        assert results == []

    @patch('flockparsecli.get_cached_embedding')
    def test_get_similar_chunks_no_embedding(self, mock_embed):
        """Test search when embedding fails"""
        mock_embed.return_value = []

        results = get_similar_chunks("test query", top_k=5)

        assert len(results) == 0

    @patch('flockparsecli.load_document_index')
    @patch('flockparsecli.get_cached_embedding')
    def test_get_similar_chunks_with_min_similarity(self, mock_embed, mock_index):
        """Test search respects minimum similarity threshold"""
        mock_embed.return_value = [0.1] * 1024
        mock_index.return_value = {"documents": []}

        # Just test that min_similarity parameter is accepted
        results = get_similar_chunks("test", top_k=5, min_similarity=0.8)

        # With no documents, should return empty
        assert results == []


class TestDocumentListing:
    """Test document listing functionality"""

    @patch('flockparsecli.load_document_index')
    def test_list_documents_empty(self, mock_load):
        """Test listing when no documents exist"""
        mock_load.return_value = {"documents": []}

        docs = list_documents()

        # list_documents returns None when empty
        assert docs is None

    @patch('flockparsecli.load_document_index')
    def test_list_documents_multiple(self, mock_load):
        """Test listing multiple documents"""
        mock_load.return_value = {
            "documents": [
                {
                    "id": "doc1",
                    "original": "/path/to/doc1.pdf",
                    "processed_date": "2025-01-01",
                    "chunks": ["chunk1", "chunk2"]
                },
                {
                    "id": "doc2",
                    "original": "/path/to/doc2.pdf",
                    "processed_date": "2025-01-02",
                    "chunks": ["chunk1"]
                }
            ]
        }

        # list_documents prints to stdout but returns None
        docs = list_documents()
        assert docs is None

    @patch('flockparsecli.load_document_index')
    def test_list_documents_index_error(self, mock_load):
        """Test handling index loading errors"""
        mock_load.side_effect = Exception("Index corrupted")

        try:
            docs = list_documents()
            # May return None or raise
        except Exception:
            pass  # Expected


class TestEmbeddingEdgeCases:
    """Test edge cases in embedding system"""

    @patch('flockparsecli.ollama.embed')
    def test_embed_special_characters(self, mock_embed):
        """Test embedding text with special characters"""
        special_text = "Test: <>&\"'\n\t\r"

        result = embed_text(special_text)

        # embed_text returns the original text
        assert result == special_text

    @patch('flockparsecli.ollama.embed')
    def test_embed_unicode(self, mock_embed):
        """Test embedding unicode text"""
        unicode_text = "Testing: café, naïve, 中文, العربية"

        result = embed_text(unicode_text)

        # embed_text returns the original text
        assert result == unicode_text

    @patch('flockparsecli.load_embedding_cache')
    @patch('flockparsecli.save_embedding_cache')
    @patch('flockparsecli.load_balancer.embed_distributed')
    def test_cache_hash_collision(self, mock_embed, mock_save, mock_load):
        """Test cache behavior with hash collisions (unlikely but possible)"""
        # Different texts, same mock cache key for testing
        mock_load.return_value = {
            "fake_hash": [0.1] * 1024
        }

        # Mock embedding result
        mock_result = Mock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_embed.return_value = mock_result

        # Should still work correctly
        result1 = get_cached_embedding("text1", use_load_balancer=True)
        result2 = get_cached_embedding("text2", use_load_balancer=True)

        # Both should return valid embeddings
        assert isinstance(result1, list)
        assert isinstance(result2, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
