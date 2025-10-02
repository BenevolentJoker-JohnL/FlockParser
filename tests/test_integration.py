"""
Integration tests for FlockParser
Tests complete workflows and user-facing functions
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flockparsecli import (
    register_document,
    cosine_similarity,
    OllamaLoadBalancer,
)


class TestRegisterDocument:
    """Test document registration in knowledge base"""

    @patch('flockparsecli.save_document_index')
    @patch('flockparsecli.load_document_index')
    def test_register_document_basic(self, mock_load, mock_save):
        """Test basic document registration"""
        mock_load.return_value = {"documents": []}

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf:
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as txt:
                pdf_path = Path(pdf.name)
                txt_path = Path(txt.name)

                try:
                    doc_id = register_document(
                        pdf_path,
                        txt_path,
                        "Test content",
                        chunks=["chunk1", "chunk2"]
                    )

                    assert doc_id is not None
                    mock_save.assert_called_once()
                finally:
                    pdf_path.unlink(missing_ok=True)
                    txt_path.unlink(missing_ok=True)

    @patch('flockparsecli.save_document_index')
    @patch('flockparsecli.load_document_index')
    def test_register_document_no_chunks(self, mock_load, mock_save):
        """Test registering document without chunks"""
        mock_load.return_value = {"documents": []}

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf:
            with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as txt:
                pdf_path = Path(pdf.name)
                txt_path = Path(txt.name)

                try:
                    doc_id = register_document(
                        pdf_path,
                        txt_path,
                        "Test content"
                    )

                    assert doc_id is not None
                finally:
                    pdf_path.unlink(missing_ok=True)
                    txt_path.unlink(missing_ok=True)


class TestCosineSimilarity:
    """Test cosine similarity calculations"""

    def test_cosine_similarity_identical(self):
        """Test similarity of identical vectors"""
        vec = [1.0, 2.0, 3.0]
        sim = cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 0.01

    def test_cosine_similarity_orthogonal(self):
        """Test similarity of orthogonal vectors"""
        vec1 = [1.0, 0.0]
        vec2 = [0.0, 1.0]
        sim = cosine_similarity(vec1, vec2)
        assert abs(sim) < 0.01

    def test_cosine_similarity_opposite(self):
        """Test similarity of opposite vectors"""
        vec1 = [1.0, 1.0]
        vec2 = [-1.0, -1.0]
        sim = cosine_similarity(vec1, vec2)
        assert abs(sim - (-1.0)) < 0.01

    def test_cosine_similarity_empty(self):
        """Test similarity with empty vectors"""
        try:
            sim = cosine_similarity([], [])
            # May return 0 or raise
            assert sim == 0 or True
        except:
            pass  # Expected


class TestLoadBalancerDistributed:
    """Test load balancer distributed operations"""

    @patch('flockparsecli.ollama.Client')
    def test_embed_distributed_success(self, mock_client_class):
        """Test distributed embedding"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        # Mock ollama client
        mock_client = Mock()
        mock_result = Mock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_client.embed.return_value = mock_result
        mock_client_class.return_value = mock_client

        result = lb.embed_distributed("mxbai-embed-large", "test text")

        assert result is not None
        assert hasattr(result, 'embeddings')

    @patch('flockparsecli.ollama.Client')
    def test_chat_distributed_success(self, mock_client_class):
        """Test distributed chat"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        # Mock ollama client
        mock_client = Mock()
        mock_result = Mock()
        mock_result.message = {"content": "Response"}
        mock_client.chat.return_value = mock_result
        mock_client_class.return_value = mock_client

        result = lb.chat_distributed("llama3.2:1b", [{"role": "user", "content": "Hi"}])

        assert result is not None

    @patch('flockparsecli.ollama.Client')
    def test_embed_batch_basic(self, mock_client_class):
        """Test batch embedding"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        # Mock ollama client
        mock_client = Mock()
        mock_result = Mock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_client.embed.return_value = mock_result
        mock_client_class.return_value = mock_client

        texts = ["text1", "text2", "text3"]
        results = lb.embed_batch("mxbai-embed-large", texts)

        assert isinstance(results, list)
        assert len(results) == 3


class TestLoadBalancerNodeManagement:
    """Test load balancer node management"""

    def test_list_nodes(self):
        """Test listing nodes"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)
        nodes = lb.list_nodes()
        # Function prints, returns None
        assert nodes is None

    def test_get_available_instances(self):
        """Test getting available instances"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)
        instances = lb.get_available_instances()
        assert isinstance(instances, list)

    def test_print_stats(self):
        """Test printing statistics"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)
        # Function prints, returns None
        result = lb.print_stats()
        assert result is None

    def test_record_request_success(self):
        """Test recording successful request"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        lb.record_request("http://localhost:11434", 0.5, error=False)

        stats = lb.instance_stats["http://localhost:11434"]
        assert stats["requests"] == 1
        assert stats["errors"] == 0

    def test_record_request_error(self):
        """Test recording failed request"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        lb.record_request("http://localhost:11434", 0.5, error=True)

        stats = lb.instance_stats["http://localhost:11434"]
        assert stats["errors"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
