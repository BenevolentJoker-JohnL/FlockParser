#!/usr/bin/env python3
"""
Prime SOLLOL performance stats with known node speed ratios.

This configures SOLLOL's built-in weighted distribution to give laptop
minimal work (15-20%) and desktop maximum work (80-85%).

Based on your observation: Desktop is 6x faster than laptop
- Desktop: 6.0 chunks/sec
- Laptop: 1.0 chunks/sec
- Distribution: Desktop ~85%, Laptop ~15%
"""

import sys
from pathlib import Path

# Setup logging before SOLLOL import
sys.path.insert(0, str(Path(__file__).parent))
from logging_config import setup_logging

logger = setup_logging()

# Import SOLLOL
sys.path.insert(0, str(Path.home() / "SOLLOL" / "src"))
from sollol import OllamaPool
from sollol.routing_strategy import RoutingStrategy


def prime_performance_stats(pool):
    """
    Manually set initial performance stats based on known node characteristics.

    This primes SOLLOL's weighted distribution algorithm with realistic values
    so it doesn't start with equal distribution (0.5 chunks/sec default for all).
    """

    logger.info("\n" + "=" * 70)
    logger.info("⚖️  PRIMING SOLLOL PERFORMANCE STATS")
    logger.info("=" * 70)

    # Discover nodes to identify laptop vs desktop
    logger.info("\nDiscovered nodes:")
    for i, node in enumerate(pool.nodes, 1):
        node_key = f"{node['host']}:{node['port']}"
        logger.info(f"  {i}. {node_key}")

    if len(pool.nodes) != 2:
        logger.warning(f"\n⚠️  Expected 2 nodes (laptop + desktop), found {len(pool.nodes)}")
        logger.info("Proceeding anyway...")

    # Ask user to identify which is laptop and which is desktop
    logger.info("\n" + "=" * 70)
    logger.info("Identify your nodes:")
    logger.info("=" * 70)

    from flockparsecli import visible_input

    # Show nodes again with numbers
    for i, node in enumerate(pool.nodes, 1):
        node_key = f"{node['host']}:{node['port']}"
        print(f"  {i}. {node_key}")

    # Get laptop node
    while True:
        laptop_num = visible_input("\nWhich node is the LAPTOP (slow)? Enter number: ").strip()
        try:
            laptop_idx = int(laptop_num) - 1
            if 0 <= laptop_idx < len(pool.nodes):
                break
            logger.error(f"Invalid number! Enter 1-{len(pool.nodes)}")
        except ValueError:
            logger.error("Invalid input! Enter a number")

    laptop_node = pool.nodes[laptop_idx]
    laptop_key = f"{laptop_node['host']}:{laptop_node['port']}"

    # Get desktop node
    while True:
        desktop_num = visible_input(f"\nWhich node is the DESKTOP (fast)? Enter number: ").strip()
        try:
            desktop_idx = int(desktop_num) - 1
            if 0 <= desktop_idx < len(pool.nodes) and desktop_idx != laptop_idx:
                break
            if desktop_idx == laptop_idx:
                logger.error("Can't be the same as laptop!")
            else:
                logger.error(f"Invalid number! Enter 1-{len(pool.nodes)}")
        except ValueError:
            logger.error("Invalid input! Enter a number")

    desktop_node = pool.nodes[desktop_idx]
    desktop_key = f"{desktop_node['host']}:{desktop_node['port']}"

    # Get speed ratio
    while True:
        ratio_str = visible_input(f"\nHow many times FASTER is desktop than laptop? (default: 6.0): ").strip()
        if not ratio_str:
            speed_ratio = 6.0
            break
        try:
            speed_ratio = float(ratio_str)
            if speed_ratio > 0:
                break
            logger.error("Speed ratio must be positive!")
        except ValueError:
            logger.error("Invalid number!")

    # Calculate throughputs for desired distribution
    # If desktop is 6x faster:
    # - Laptop: 1.0 chunks/sec → 14.3% of work
    # - Desktop: 6.0 chunks/sec → 85.7% of work

    laptop_throughput = 1.0
    desktop_throughput = speed_ratio

    total_throughput = laptop_throughput + desktop_throughput
    laptop_pct = (laptop_throughput / total_throughput) * 100
    desktop_pct = (desktop_throughput / total_throughput) * 100

    logger.info("\n" + "=" * 70)
    logger.info("📊 PERFORMANCE CONFIGURATION")
    logger.info("=" * 70)
    logger.info(f"\nLaptop:  {laptop_key}")
    logger.info(f"  Throughput: {laptop_throughput:.1f} chunks/sec")
    logger.info(f"  Workload:   {laptop_pct:.1f}%")
    logger.info(f"\nDesktop: {desktop_key}")
    logger.info(f"  Throughput: {desktop_throughput:.1f} chunks/sec")
    logger.info(f"  Workload:   {desktop_pct:.1f}%")

    # Set the stats
    if "node_performance" not in pool.stats:
        pool.stats["node_performance"] = {}

    # Prime laptop stats
    pool.stats["node_performance"][laptop_key] = {
        "batch_throughput": laptop_throughput,
        "avg_response_time": 1.0 / laptop_throughput,  # Inverse of throughput
        "total_requests": 10,  # Enough to trigger adaptive logic
        "successful_requests": 10,
        "failed_requests": 0,
        "latency_ms": (1.0 / laptop_throughput) * 1000,
        "available": True,
        "primed": True,  # Mark as manually configured
    }

    # Prime desktop stats
    pool.stats["node_performance"][desktop_key] = {
        "batch_throughput": desktop_throughput,
        "avg_response_time": 1.0 / desktop_throughput,
        "total_requests": 10,
        "successful_requests": 10,
        "failed_requests": 0,
        "latency_ms": (1.0 / desktop_throughput) * 1000,
        "available": True,
        "primed": True,
    }

    logger.info("\n✅ Performance stats primed successfully!")
    logger.info("\n💡 SOLLOL will now use weighted distribution:")
    logger.info(f"   - Laptop gets ~{laptop_pct:.0f}% of chunks")
    logger.info(f"   - Desktop gets ~{desktop_pct:.0f}% of chunks")
    logger.info("\n🚀 Process PDFs to see the optimized distribution in action!")
    logger.info("=" * 70 + "\n")


def main():
    """Prime SOLLOL stats and return to FlockParser."""

    # Initialize SOLLOL pool (same as flockparsecli.py)
    logger.info("🔧 Initializing SOLLOL pool...")

    pool = OllamaPool(
        nodes=None,  # Auto-discover
        routing_strategy=RoutingStrategy.ROUND_ROBIN,
        exclude_localhost=True,
        discover_all_nodes=True,
        app_name="FlockParser-Prime",
        enable_ray=False,
        enable_dask=False,
        enable_gpu_redis=False,
        register_with_dashboard=False,
    )

    if not pool.nodes:
        logger.error("❌ No nodes found! Ensure Ollama is running on your devices.")
        return 1

    # Prime the stats
    prime_performance_stats(pool)

    # Save stats to file for FlockParser to load
    import json

    stats_file = Path(__file__).parent / "sollol_primed_stats.json"

    primed_stats = {"node_performance": pool.stats.get("node_performance", {}), "priming_complete": True}

    with open(stats_file, "w") as f:
        json.dump(primed_stats, f, indent=2)

    logger.info(f"💾 Stats saved to {stats_file}")
    logger.info("\n✅ Configuration complete! Run FlockParser to use optimized distribution.")

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
