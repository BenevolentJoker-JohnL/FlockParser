"""
Minimal compatibility layer for FlockParser-specific methods.
Extends SOLLOL's OllamaPool with FlockParser's expected API.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any
from sollol import OllamaPool
from sollol.discovery import discover_ollama_nodes

logger = logging.getLogger(__name__)


def add_flockparser_methods(pool: OllamaPool, kb_dir: Path):
    """
    Add FlockParser-specific methods to SOLLOL's OllamaPool instance.

    Args:
        pool: SOLLOL OllamaPool instance
        kb_dir: FlockParser's knowledge base directory (for saving nodes)
    """

    # Store KB_DIR for node persistence
    pool._kb_dir = kb_dir
    pool._nodes_file = kb_dir / "ollama_nodes.json"

    def _convert_nodes_to_urls(nodes):
        """Convert SOLLOL nodes to FlockParser URL format."""
        return [f"http://{node['host']}:{node['port']}" for node in nodes]

    def _convert_url_to_node(url):
        """Convert FlockParser URL to SOLLOL node dict."""
        url_clean = url.replace("http://", "").replace("https://", "")
        if ":" in url_clean:
            host, port = url_clean.split(":", 1)
        else:
            host, port = url_clean, "11434"
        return {"host": host, "port": int(port)}

    # Add 'instances' property (compatibility with FlockParser code)
    @property
    def instances(self):
        """Get nodes in FlockParser URL format."""
        return _convert_nodes_to_urls(self.nodes)

    pool.__class__.instances = instances

    # Add discover_nodes method
    def discover_nodes(self, require_embedding_model=True, remove_stale=False):
        """
        Discover Ollama nodes on network (FlockParser-compatible).

        Args:
            require_embedding_model: Ignored (kept for compatibility)
            remove_stale: If True, remove nodes that are no longer found on network
        """
        logger.info("🔍 Re-scanning network for Ollama nodes...")
        discovered = discover_ollama_nodes(timeout=2.0)

        # Get discovered nodes (excluding localhost)
        discovered_keys = set()
        logger.info(f"📡 Found {len(discovered)} Ollama node(s) on network:")
        for node_dict in discovered:
            if node_dict['host'] not in ['localhost', '127.0.0.1']:
                node_key = f"{node_dict['host']}:{node_dict['port']}"
                discovered_keys.add(node_key)
                logger.info(f"   • http://{node_key}")
            else:
                logger.info(f"   • http://{node_dict['host']}:{node_dict['port']} (localhost - using real IP)")

        # Get currently configured nodes
        existing_keys = set(f"{n['host']}:{n['port']}" for n in self.nodes)

        # Find new nodes
        new_nodes = discovered_keys - existing_keys

        # Find stale nodes (configured but not found)
        stale_nodes = existing_keys - discovered_keys

        added_count = 0
        removed_count = 0

        # Add new nodes
        if new_nodes:
            logger.info(f"\n➕ Adding {len(new_nodes)} new node(s):")
            for node_key in new_nodes:
                host, port = node_key.split(":")
                self.add_node(host, int(port))
                added_count += 1
                logger.info(f"   ✅ Added: {node_key}")

        # Handle stale nodes
        if stale_nodes:
            if remove_stale:
                logger.info(f"\n➖ Removing {len(stale_nodes)} stale node(s):")
                for node_key in stale_nodes:
                    host, port = node_key.split(":")
                    self.remove_node(host, int(port))
                    removed_count += 1
                    logger.info(f"   🗑️  Removed: {node_key}")
            else:
                logger.warning(f"\n⚠️  Found {len(stale_nodes)} node(s) not detected on network:")
                for node_key in stale_nodes:
                    logger.warning(f"   • {node_key} (still configured, use 'remove_node' to remove)")

        # Summary
        logger.info(f"\n📊 Discovery Summary:")
        logger.info(f"   Discovered: {len(discovered_keys)} nodes")
        logger.info(f"   Added: {added_count} new nodes")
        if remove_stale:
            logger.info(f"   Removed: {removed_count} stale nodes")
        logger.info(f"   Total configured: {len(self.nodes)} nodes")

        if len(self.nodes) > 0:
            logger.info(f"\n🌐 Active Nodes:")
            for node in self.nodes:
                logger.info(f"   • http://{node['host']}:{node['port']}")
        else:
            logger.warning("⚠️  No nodes configured! SOLLOL cannot route requests.")

        self._save_nodes()
        return discovered

    pool.discover_nodes = discover_nodes.__get__(pool)

    # Add list_nodes method
    def list_nodes(self):
        """List all configured nodes (FlockParser-compatible)."""
        return self.instances

    pool.list_nodes = list_nodes.__get__(pool)

    # Add print_stats method
    def print_stats(self):
        """Print load balancer statistics (FlockParser-compatible)."""
        stats = self.get_stats()

        logger.info("\n" + "=" * 70)
        logger.info("📊 SOLLOL LOAD BALANCER STATISTICS")
        logger.info("=" * 70)
        logger.info(f"Total Requests: {stats.get('total_requests', 0)}")
        logger.info(f"Successful: {stats.get('successful_requests', 0)}")
        logger.info(f"Failed: {stats.get('failed_requests', 0)}")
        logger.info(f"Intelligent Routing: {'Enabled' if stats.get('intelligent_routing_enabled') else 'Disabled'}")
        logger.info(f"\nConfigured Nodes: {len(self.nodes)}")

        for i, node_url in enumerate(self.instances, 1):
            logger.info(f"  {i}. {node_url}")

        # Node performance metrics
        if "node_performance" in stats:
            logger.info("\n📈 Node Performance:")
            for node_key, perf in stats["node_performance"].items():
                logger.info(f"\n  {node_key}:")
                logger.info(f"    Requests: {perf.get('total_requests', 0)}")
                logger.info(f"    Success Rate: {perf.get('success_rate', 0) * 100:.1f}%")
                logger.info(f"    Avg Latency: {perf.get('latency_ms', 0):.1f}ms")

        logger.info("=" * 70)

    pool.print_stats = print_stats.__get__(pool)

    # Add embed_batch method with intelligent parallelization
    def embed_batch(self, model, texts, max_workers=None, force_mode=None):
        """
        Batch embed with SOLLOL's intelligent parallelization.
        Automatically determines optimal execution strategy based on:
        - Number of available nodes
        - Batch size
        - Node performance characteristics
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        if not texts:
            return []

        batch_size = len(texts)
        num_nodes = len(self.nodes)

        # Determine optimal number of workers
        if max_workers:
            workers = max_workers
        else:
            # Use number of nodes as workers (each node can handle one request at a time)
            workers = min(num_nodes, batch_size)

        # For single node or small batches, use sequential processing
        if workers <= 1 or batch_size <= 2:
            logger.debug(f"🔄 Sequential batch embedding: {batch_size} texts on {num_nodes} node(s)")
            results = []
            for text in texts:
                try:
                    result = self.embed(model, text, priority=7)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Batch embed failed for text: {e}")
                    results.append(None)
            return results

        # Parallel processing for multiple nodes and larger batches
        logger.info(f"⚡ Parallel batch embedding: {batch_size} texts using {workers} workers across {num_nodes} nodes")

        results = [None] * len(texts)  # Pre-allocate results list

        def embed_single(idx_text):
            idx, text = idx_text
            try:
                result = self.embed(model, text, priority=7)
                return (idx, result)
            except Exception as e:
                logger.error(f"Batch embed failed for text {idx}: {e}")
                return (idx, None)

        # Execute in parallel with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all tasks with their indices
            futures = {executor.submit(embed_single, (i, text)): i
                      for i, text in enumerate(texts)}

            # Collect results as they complete
            for future in as_completed(futures):
                idx, result = future.result()
                results[idx] = result

        logger.debug(f"✅ Batch embedding complete: {sum(1 for r in results if r is not None)}/{batch_size} successful")
        return results

    pool.embed_batch = embed_batch.__get__(pool)

    # Add stub methods for legacy features
    def set_routing_strategy(self, strategy):
        """Set routing strategy (SOLLOL always uses intelligent routing)."""
        logger.info(f"ℹ️  SOLLOL uses intelligent routing by default ('{strategy}' ignored)")

    pool.set_routing_strategy = set_routing_strategy.__get__(pool)

    def verify_models_on_nodes(self):
        """Verify models on nodes (handled by SOLLOL)."""
        logger.info("ℹ️  Model verification handled by SOLLOL's intelligent routing")

    pool.verify_models_on_nodes = verify_models_on_nodes.__get__(pool)

    def force_gpu_all_nodes(self, model):
        """Force GPU for model (handled by SOLLOL routing)."""
        logger.info(f"ℹ️  SOLLOL's intelligent routing handles GPU allocation for {model}")

    pool.force_gpu_all_nodes = force_gpu_all_nodes.__get__(pool)

    # Save nodes helper
    def _save_nodes(self):
        """Save nodes to FlockParser's nodes file."""
        import json
        try:
            with open(self._nodes_file, 'w') as f:
                json.dump(self.instances, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save nodes: {e}")

    pool._save_nodes = _save_nodes.__get__(pool)

    # Override add_node to save
    original_add_node = pool.add_node
    def add_node_with_save(self, host, port=11434):
        original_add_node(host, port)
        pool._save_nodes()
        logger.info(f"✅ Added node: http://{host}:{port}")

    pool.add_node = add_node_with_save.__get__(pool)

    # Override remove_node to save
    original_remove_node = pool.remove_node
    def remove_node_with_save(self, host, port=11434):
        original_remove_node(host, port)
        pool._save_nodes()
        logger.info(f"✅ Removed node: http://{host}:{port}")

    pool.remove_node = remove_node_with_save.__get__(pool)

    logger.debug("✅ FlockParser compatibility methods added to SOLLOL pool")

    return pool
