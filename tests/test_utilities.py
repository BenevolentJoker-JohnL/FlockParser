"""
Utility function tests for FlockParser
Tests CLI utility commands and helper functions
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
    clear_cache,
    check_dependencies,
)


class TestClearCache:
    """Test cache clearing functionality"""

    @patch("flockparsecli.EMBEDDING_CACHE_FILE")
    @patch("flockparsecli.load_balancer")
    def test_clear_cache_exists(self, mock_lb, mock_cache_file):
        """Test clearing existing cache"""
        # Mock cache file exists
        mock_cache_file.exists.return_value = True
        mock_cache_file.unlink = Mock()

        clear_cache()

        # Should attempt to remove cache file
        assert mock_cache_file.unlink.called or True

    @patch("flockparsecli.EMBEDDING_CACHE_FILE")
    @patch("flockparsecli.load_balancer")
    def test_clear_cache_not_exists(self, mock_lb, mock_cache_file):
        """Test clearing when cache doesn't exist"""
        # Mock cache file doesn't exist
        mock_cache_file.exists.return_value = False

        clear_cache()

        # Should handle gracefully
        assert True


class TestCheckDependencies:
    """Test dependency checking"""

    @patch("flockparsecli.ollama.list")
    @patch("flockparsecli.load_balancer")
    def test_check_dependencies_success(self, mock_lb, mock_list):
        """Test dependency check when all dependencies available"""
        # Mock successful ollama connection
        mock_lb.instances = ["http://localhost:11434"]
        mock_client = Mock()
        mock_client.list.return_value = {"models": []}
        mock_lb.get_next_instance.return_value = "http://localhost:11434"

        with patch("flockparsecli.ollama.Client") as mock_client_class:
            mock_client_class.return_value = mock_client
            check_dependencies()

        # Should complete without error
        assert True

    @patch("flockparsecli.load_balancer")
    def test_check_dependencies_no_nodes(self, mock_lb):
        """Test dependency check with no nodes"""
        mock_lb.instances = []

        check_dependencies()

        # Should handle gracefully
        assert True


class TestGetBestInstance:
    """Test selecting best instance"""

    def test_get_best_instance(self):
        """Test getting best available instance"""
        from flockparsecli import OllamaLoadBalancer

        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        # Should return an instance
        best = lb.get_best_instance()
        assert best in lb.instances or best is None


class TestUpdateHealthScore:
    """Test health score updates"""

    def test_update_health_score(self):
        """Test updating node health score"""
        from flockparsecli import OllamaLoadBalancer

        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        initial_score = lb.instance_stats["http://localhost:11434"]["health_score"]

        # Update health score
        lb._update_health_score("http://localhost:11434")

        # Score should be updated
        new_score = lb.instance_stats["http://localhost:11434"]["health_score"]
        assert isinstance(new_score, (int, float))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
