"""
Adaptive Parallelism Strategy
Automatically chooses between sequential and parallel processing
based on cluster performance characteristics.
"""

import time
from typing import List, Tuple, Dict


class AdaptiveParallelismStrategy:
    """
    Intelligently decides whether to use parallel or sequential processing
    based on real-time performance metrics.

    Key Decision Factors:
    1. GPU Performance Gap - If one node is 10x faster, sequential is better
    2. Node Count - More similar nodes = better parallelism
    3. Network Latency - High latency favors fewer nodes
    4. Batch Size - Small batches favor sequential (less overhead)
    """

    def __init__(self, load_balancer):
        self.load_balancer = load_balancer
        self.performance_history = []  # Track decisions and results

    def should_parallelize(self, batch_size: int) -> Tuple[bool, Dict]:
        """
        Decide whether to parallelize based on cluster state.

        Returns:
            (should_parallelize: bool, reasoning: Dict)
        """
        nodes = self.load_balancer.instances
        stats = self.load_balancer.instance_stats

        # Get available nodes
        available_nodes = self.load_balancer.get_available_instances()

        # Always use registered nodes for decision (don't rely on availability cache)
        # The embed_batch will handle offline nodes gracefully
        if len(self.load_balancer.instances) <= 1:
            return False, {
                "reason": "single_node",
                "detail": "Only one node available, sequential is optimal"
            }

        # Use all registered nodes for speed calculation
        available_nodes = self.load_balancer.instances

        # Calculate performance metrics
        node_speeds = []
        for node in available_nodes:
            node_stat = stats.get(node, {})

            # Estimate speed based on health score and GPU
            has_gpu = node_stat.get("has_gpu")
            is_gpu_loaded = node_stat.get("is_gpu_loaded", False)
            requests = node_stat.get("requests", 0)

            if requests > 0:
                avg_time = node_stat.get("total_time", 0) / requests
                speed_score = 1.0 / max(avg_time, 0.01)  # Higher = faster
            else:
                # Estimate based on GPU
                if has_gpu and is_gpu_loaded:
                    speed_score = 100  # Very fast (GPU)
                else:
                    speed_score = 10   # Slower (CPU)

            node_speeds.append({
                "node": node,
                "speed_score": speed_score,
                "has_gpu": has_gpu and is_gpu_loaded
            })

        # Sort by speed
        node_speeds.sort(key=lambda x: x["speed_score"], reverse=True)

        fastest_node = node_speeds[0]
        slowest_node = node_speeds[-1]

        # Calculate speed ratio
        speed_ratio = fastest_node["speed_score"] / max(slowest_node["speed_score"], 1)

        # Decision logic
        reasoning = {
            "available_nodes": len(available_nodes),
            "batch_size": batch_size,
            "fastest_node": fastest_node["node"],
            "fastest_speed": fastest_node["speed_score"],
            "speed_ratio": speed_ratio,
        }

        # CASE 1: One GPU node is 5x+ faster than others
        if speed_ratio >= 5.0:
            # Sequential on fastest node is better
            return False, {
                **reasoning,
                "reason": "dominant_node",
                "detail": f"Fastest node is {speed_ratio:.1f}x faster - sequential wins",
                "recommended_node": fastest_node["node"]
            }

        # CASE 2: Small batch (<20 items)
        if batch_size < 20:
            # Overhead of parallelism not worth it
            return False, {
                **reasoning,
                "reason": "small_batch",
                "detail": f"Batch size {batch_size} too small for parallel overhead",
                "recommended_node": fastest_node["node"]
            }

        # CASE 3: Multiple similar-speed nodes
        if speed_ratio < 3.0:
            # Nodes are similar speed, parallelize!
            return True, {
                **reasoning,
                "reason": "balanced_cluster",
                "detail": f"Speed ratio {speed_ratio:.1f}x - parallel is efficient",
                "parallel_workers": len(available_nodes) * 2
            }

        # CASE 4: Medium speed difference (3-5x)
        # Use fastest 2-3 nodes in parallel
        if speed_ratio < 5.0 and len(available_nodes) >= 3:
            return True, {
                **reasoning,
                "reason": "hybrid_parallel",
                "detail": f"Using top {min(3, len(available_nodes))} nodes in parallel",
                "parallel_workers": min(3, len(available_nodes)) * 2
            }

        # Default: Sequential on fastest
        return False, {
            **reasoning,
            "reason": "default_sequential",
            "detail": "Defaulting to sequential on fastest node",
            "recommended_node": fastest_node["node"]
        }

    def get_optimal_workers(self, batch_size: int) -> int:
        """Calculate optimal number of parallel workers."""
        available_nodes = self.load_balancer.get_available_instances()

        # Base workers on number of nodes
        base_workers = len(available_nodes) * 2

        # Adjust for batch size
        if batch_size < 50:
            workers = min(base_workers, batch_size)
        elif batch_size < 200:
            workers = base_workers
        else:
            # Large batch, can use more workers
            workers = min(base_workers * 2, batch_size)

        return max(1, workers)

    def estimate_completion_time(self, batch_size: int) -> Dict:
        """
        Estimate completion time for sequential vs parallel.

        Returns dict with estimates and recommendation.
        """
        nodes = self.load_balancer.instances
        stats = self.load_balancer.instance_stats
        available_nodes = self.load_balancer.get_available_instances()

        if not available_nodes:
            return {
                "error": "No nodes available"
            }

        # Get fastest node stats
        fastest_time = float('inf')
        fastest_node = None

        for node in available_nodes:
            node_stat = stats.get(node, {})
            requests = node_stat.get("requests", 0)

            if requests > 0:
                avg_time = node_stat.get("total_time", 0) / requests
                if avg_time < fastest_time:
                    fastest_time = avg_time
                    fastest_node = node
            else:
                # Estimate
                has_gpu = node_stat.get("has_gpu") and node_stat.get("is_gpu_loaded")
                estimated_time = 0.02 if has_gpu else 0.1  # 20ms GPU, 100ms CPU
                if estimated_time < fastest_time:
                    fastest_time = estimated_time
                    fastest_node = node

        # Sequential time estimate
        sequential_time = fastest_time * batch_size

        # Parallel time estimate
        # Assumes work distributed evenly across nodes
        workers = self.get_optimal_workers(batch_size)
        parallel_overhead = 0.5  # 500ms startup overhead
        items_per_worker = batch_size / workers
        parallel_time = (fastest_time * items_per_worker) + parallel_overhead

        # Recommendation
        if sequential_time < parallel_time:
            recommendation = "sequential"
            savings = parallel_time - sequential_time
        else:
            recommendation = "parallel"
            savings = sequential_time - parallel_time

        return {
            "batch_size": batch_size,
            "sequential_estimate": f"{sequential_time:.1f}s",
            "parallel_estimate": f"{parallel_time:.1f}s",
            "recommendation": recommendation,
            "time_saved": f"{savings:.1f}s",
            "fastest_node": fastest_node,
            "workers": workers if recommendation == "parallel" else 1
        }


def print_parallelism_report(load_balancer):
    """Print a report on optimal parallelism strategy."""
    strategy = AdaptiveParallelismStrategy(load_balancer)

    print("\n" + "=" * 70)
    print("🔀 ADAPTIVE PARALLELISM ANALYSIS")
    print("=" * 70)

    # Test scenarios
    scenarios = [10, 50, 100, 200, 500]

    for batch_size in scenarios:
        should_parallel, reasoning = strategy.should_parallelize(batch_size)
        estimate = strategy.estimate_completion_time(batch_size)

        print(f"\n📊 Batch Size: {batch_size} items")
        print(f"   Mode: {'🔀 PARALLEL' if should_parallel else '➡️  SEQUENTIAL'}")
        print(f"   Reason: {reasoning.get('reason', 'unknown')}")
        print(f"   Detail: {reasoning.get('detail', 'N/A')}")

        if 'sequential_estimate' in estimate:
            print(f"   Sequential: {estimate['sequential_estimate']}")
            print(f"   Parallel: {estimate['parallel_estimate']}")
            print(f"   Recommendation: {estimate['recommendation'].upper()}")
            print(f"   Time saved: {estimate['time_saved']}")

    print("\n" + "=" * 70)
