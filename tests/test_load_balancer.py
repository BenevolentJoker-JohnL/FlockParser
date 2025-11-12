"""
Load Balancer tests for FlockParser
Tests distributed processing and node management
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flockparsecli import OllamaLoadBalancer


class TestLoadBalancerInitialization:
    """Test load balancer initialization"""

    def test_create_load_balancer(self):
        """Test creating load balancer with initial nodes"""
        nodes = ["http://localhost:11434", "http://192.168.1.10:11434"]
        lb = OllamaLoadBalancer(instances=nodes, skip_init_checks=True)

        # Load balancer loads saved nodes from disk, so may have more than provided
        assert len(lb.instances) >= len(nodes)
        # All provided nodes should be present
        for node in nodes:
            assert node in lb.instances

    def test_create_load_balancer_with_nodes(self):
        """Test that load balancer accepts and stores nodes"""
        lb = OllamaLoadBalancer(instances=["http://test:11434"], skip_init_checks=True)

        # Should have at least our node (may have saved nodes too)
        assert isinstance(lb.instances, list)
        assert len(lb.instances) >= 1

    def test_load_balancer_default_strategy(self):
        """Test default routing strategy"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        assert hasattr(lb, "routing_strategy")
        # SOLLOL's default is now "intelligent" (upgraded from "adaptive")
        assert lb.routing_strategy in ["intelligent", "adaptive"]


class TestNodeManagement:
    """Test adding/removing nodes"""

    @patch("flockparsecli.requests.get")
    def test_add_node_success(self, mock_get):
        """Test adding a valid node"""
        # Mock successful health check and model check
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "mxbai-embed-large"}]}
        mock_get.return_value = mock_response

        lb = OllamaLoadBalancer(instances=[], skip_init_checks=True)
        initial_count = len(lb.instances)

        success = lb.add_node("http://192.168.1.20:11434", save=False, check_models=True)

        assert success is True or len(lb.instances) > initial_count
        if success:
            assert "http://192.168.1.20:11434" in lb.instances

    @patch("flockparsecli.requests.get")
    def test_add_node_failure(self, mock_get):
        """Test adding an unreachable node"""
        # Mock failed health check
        mock_get.side_effect = Exception("Connection refused")

        lb = OllamaLoadBalancer(instances=[], skip_init_checks=True)
        initial_count = len(lb.instances)

        success = lb.add_node("http://invalid-node:11434", save=False, optional=True)

        # Should either fail gracefully or not add the node
        assert success is False or len(lb.instances) == initial_count

    def test_add_duplicate_node(self):
        """Test adding a node that already exists"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        initial_count = len(lb.instances)
        result = lb.add_node("http://localhost:11434", save=False)

        # Should not create duplicate
        assert len(lb.instances) == initial_count
        assert result is False

    def test_remove_node(self):
        """Test removing a node"""
        lb = OllamaLoadBalancer(
            instances=["http://localhost:11434", "http://192.168.1.10:11434"], skip_init_checks=True
        )

        success = lb.remove_node("http://localhost:11434")

        assert success is True
        assert "http://localhost:11434" not in lb.instances
        assert len(lb.instances) == 1

    def test_remove_nonexistent_node(self):
        """Test removing a node that doesn't exist"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        success = lb.remove_node("http://nonexistent:11434")

        # Should return False for nonexistent node
        assert success is False
        assert len(lb.instances) == 1


class TestRoutingStrategies:
    """Test different routing strategies"""

    def test_set_routing_strategy(self):
        """Test changing routing strategy"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        lb.set_routing_strategy("round_robin")
        assert lb.routing_strategy == "round_robin"

        lb.set_routing_strategy("least_loaded")
        assert lb.routing_strategy == "least_loaded"

        lb.set_routing_strategy("adaptive")
        assert lb.routing_strategy == "adaptive"

    def test_set_all_valid_strategies(self):
        """Test all valid routing strategies"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        valid_strategies = ["adaptive", "round_robin", "least_loaded", "lowest_latency"]

        for strategy in valid_strategies:
            lb.set_routing_strategy(strategy)
            assert lb.routing_strategy == strategy


class TestHealthScoring:
    """Test health scoring and node selection"""

    def test_health_score_initialization(self):
        """Test that nodes get initial health scores"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        assert hasattr(lb, "instance_stats")
        assert "http://localhost:11434" in lb.instance_stats
        assert "health_score" in lb.instance_stats["http://localhost:11434"]

    def test_instance_stats_structure(self):
        """Test instance stats have required fields"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        stats = lb.instance_stats["http://localhost:11434"]
        required_fields = ["requests", "errors", "total_time", "latency", "health_score"]

        for field in required_fields:
            assert field in stats, f"Missing field: {field}"


class TestPerformanceTracking:
    """Test performance tracking and statistics"""

    def test_track_request_count(self):
        """Test that request count is tracked"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        node = "http://localhost:11434"

        # After initialization, request count should be tracked
        assert "requests" in lb.instance_stats[node]
        assert lb.instance_stats[node]["requests"] == 0

    def test_track_error_count(self):
        """Test that errors are tracked"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        node = "http://localhost:11434"

        # Check that error tracking exists
        assert "errors" in lb.instance_stats[node]
        assert lb.instance_stats[node]["errors"] == 0


class TestBasicAttributes:
    """Test basic attributes and methods exist"""

    def test_has_required_attributes(self):
        """Test load balancer has required attributes"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        assert hasattr(lb, "instances")
        assert hasattr(lb, "instance_stats")
        assert hasattr(lb, "routing_strategy")
        assert hasattr(lb, "current_index")
        assert hasattr(lb, "lock")

    def test_has_required_methods(self):
        """Test load balancer has required methods"""
        lb = OllamaLoadBalancer(instances=["http://localhost:11434"], skip_init_checks=True)

        assert hasattr(lb, "add_node")
        assert hasattr(lb, "remove_node")
        assert hasattr(lb, "set_routing_strategy")
        assert hasattr(lb, "get_next_instance")
        assert hasattr(lb, "record_request")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
