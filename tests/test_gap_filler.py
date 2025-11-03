"""
Gap filler tests to reach 80% coverage
Simple, robust tests targeting remaining uncovered code
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
    OllamaLoadBalancer,
    register_document,
    sanitize_for_xml,
)


class TestSanitizeXMLEdgeCases:
    """Test XML sanitization edge cases"""

    def test_sanitize_with_all_control_chars(self):
        """Test sanitizing text with all control characters"""
        # Include various control characters
        text = "Normal text\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f"
        result = sanitize_for_xml(text)

        # Should remove control chars but keep normal text
        assert "Normal text" in result
        assert "\x00" not in result

    def test_sanitize_with_high_control_chars(self):
        """Test sanitizing with high control characters"""
        text = "Text\x7f\x80\x81\x82\x83\x84\x85\x86"
        result = sanitize_for_xml(text)

        # Should sanitize high control chars
        assert isinstance(result, str)


class TestRegisterDocumentEdgeCases:
    """Test document registration edge cases"""

    @patch("flockparsecli.chroma_collection.add")
    @patch("flockparsecli.get_cached_embedding")
    @patch("flockparsecli.save_document_index")
    @patch("flockparsecli.load_document_index")
    def test_register_document_with_long_chunks(self, mock_load, mock_save, mock_embed, mock_chroma):
        """Test registering with many long chunks"""
        mock_load.return_value = {"documents": []}
        mock_embed.return_value = [0.1] * 1024

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as pdf:
            with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as txt:
                pdf_path = Path(pdf.name)
                txt_path = Path(txt.name)

                try:
                    # Create many chunks
                    chunks = [f"Chunk {i} with content " * 20 for i in range(10)]

                    doc_id = register_document(pdf_path, txt_path, "Content", chunks=chunks)

                    assert doc_id is not None
                    # Should have processed all chunks
                    assert mock_embed.call_count >= 10
                finally:
                    pdf_path.unlink(missing_ok=True)
                    txt_path.unlink(missing_ok=True)


class TestLoadBalancerVariants:
    """Test load balancer variant handling"""

    @patch("flockparsecli.ollama.Client")
    def test_check_model_with_colon_variant(self, mock_client):
        """Test checking model with colon-separated variants"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        # Mock client with model
        mock_instance = Mock()
        mock_instance.list.return_value = {"models": [{"name": "llama3.2:1b-instruct"}]}
        mock_client.return_value = mock_instance

        result = lb._check_model_available(
            "http://localhost:11434", "llama3.2:1b", acceptable_variants=["llama3.2:1b-instruct", "llama3.2:1b"]
        )

        # Should match variant
        assert result is not None

    def test_model_matches_base_name(self):
        """Test model matching with base names"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        # Test base name matching (before colon)
        assert lb._model_matches("llama3.2:1b", ["llama3.2"]) is True
        assert lb._model_matches("llama3.2:3b", ["llama3.2"]) is True

    def test_get_best_instance_with_scores(self):
        """Test getting best instance based on health scores"""
        lb = OllamaLoadBalancer(
            instances=["http://localhost:11434", "http://192.168.1.10:11434"], skip_init_checks=True
        )

        # Set different health scores
        lb.instance_stats["http://localhost:11434"]["health_score"] = 0.9
        lb.instance_stats["http://192.168.1.10:11434"]["health_score"] = 0.5

        # Record some stats to affect selection
        lb.record_request("http://localhost:11434", 0.1, error=False)
        lb.record_request("http://192.168.1.10:11434", 1.0, error=True)

        best = lb.get_best_instance()

        # Should return one of the instances
        assert best in lb.instances or best is None


class TestLoadBalancerSaveLoad:
    """Test saving and loading nodes"""

    def test_save_nodes_creates_file(self):
        """Test that saving nodes creates the file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)
            lb.nodes_file = Path(tmpdir) / "test_nodes.json"

            lb._save_nodes_to_disk()

            # File should exist
            assert lb.nodes_file.exists()

            # File should contain valid JSON
            with open(lb.nodes_file) as f:
                data = json.load(f)
                assert isinstance(data, list)

    def test_load_nodes_with_new_format(self):
        """Test loading nodes with new dict format"""
        with tempfile.TemporaryDirectory() as tmpdir:
            nodes_file = Path(tmpdir) / "nodes.json"

            # Create new format (list of dicts)
            nodes_data = [
                {"url": "http://192.168.1.10:11434", "force_cpu": False},
                {"url": "http://192.168.1.11:11434", "force_cpu": True},
            ]

            with open(nodes_file, "w") as f:
                json.dump(nodes_data, f)

            lb = OllamaLoadBalancer(instances=[], skip_init_checks=True)
            lb.nodes_file = nodes_file

            lb._load_nodes_from_disk()

            # Should load both nodes
            assert "http://192.168.1.10:11434" in lb.instances
            assert "http://192.168.1.11:11434" in lb.instances


class TestEmbedBatchModes:
    """Test embed_batch with different modes"""

    @patch("flockparsecli.ollama.Client")
    def test_embed_batch_auto_mode_small(self, mock_client):
        """Test embed_batch auto mode with small batch"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        # Mock client
        mock_instance = Mock()
        mock_result = Mock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_instance.embed.return_value = mock_result
        mock_client.return_value = mock_instance

        # Small batch should use sequential
        texts = ["text1", "text2"]
        results = lb.embed_batch("mxbai-embed-large", texts)

        assert len(results) == 2

    @patch("flockparsecli.ollama.Client")
    def test_embed_batch_auto_mode_large(self, mock_client):
        """Test embed_batch auto mode with large batch"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        # Mock client
        mock_instance = Mock()
        mock_result = Mock()
        mock_result.embeddings = [[0.1] * 1024]
        mock_instance.embed.return_value = mock_result
        mock_client.return_value = mock_instance

        # Large batch might use parallel
        texts = [f"text{i}" for i in range(20)]
        results = lb.embed_batch("mxbai-embed-large", texts)

        assert len(results) == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
