#!/usr/bin/env python3
"""
Benchmark test comparing different embed_batch approaches:
1. SOLLOL's embed_batch with adaptive parallelism (use_adaptive=True)
2. SOLLOL's embed_batch with forced parallel (use_adaptive=False, max_workers=4)
3. SOLLOL's embed_batch with forced sequential (max_workers=1)
4. Legacy parallel_embedder.embed_batch_parallel

Goal: Determine which approach gives best performance without hanging.
"""

import time
import sys
from pathlib import Path
from sollol import OllamaPool
from sollol_compat import add_flockparser_methods
from parallel_embedder import embed_batch_parallel

# Test configuration
MODEL = "nomic-embed-text"
TEST_SIZES = [10, 50, 100, 200]  # Different batch sizes to test


def generate_test_texts(count):
    """Generate test texts of varying lengths."""
    return [
        f"This is test sentence {i} with some content to embed. "
        f"It contains multiple words to make it realistic. "
        f"Sentence number {i} out of {count} total sentences."
        for i in range(count)
    ]


def benchmark_approach(pool, approach_name, test_func, texts):
    """
    Benchmark a specific approach.

    Returns: (success: bool, duration: float, error: str)
    """
    print(f"\n  Testing {approach_name}...", file=sys.stderr, flush=True)

    start_time = time.time()
    try:
        results = test_func(texts)
        duration = time.time() - start_time

        # Verify results
        success_count = sum(1 for r in results if r is not None)
        success = success_count == len(texts)

        if success:
            print(f"    ✅ Success: {duration:.2f}s ({len(texts)/duration:.1f} emb/sec)", file=sys.stderr, flush=True)
            return True, duration, None
        else:
            print(f"    ⚠️  Partial: {success_count}/{len(texts)} in {duration:.2f}s", file=sys.stderr, flush=True)
            return False, duration, f"Only {success_count}/{len(texts)} succeeded"

    except Exception as e:
        duration = time.time() - start_time
        print(f"    ❌ Failed: {e}", file=sys.stderr, flush=True)
        return False, duration, str(e)


def main():
    print("=" * 80, file=sys.stderr, flush=True)
    print("EMBED_BATCH BENCHMARK COMPARISON", file=sys.stderr, flush=True)
    print("=" * 80, file=sys.stderr, flush=True)

    # Initialize pool
    print("\nInitializing SOLLOL pool...", file=sys.stderr, flush=True)
    pool = OllamaPool(enable_dask=False)
    pool = add_flockparser_methods(pool, Path("knowledge_base"))

    # Add nodes (adjust these IPs to your setup)
    print("Adding nodes...", file=sys.stderr, flush=True)
    pool.add_node("192.168.0.166", 11434)
    pool.add_node("192.168.0.233", 11434)

    print(f"✅ Pool ready with {len(pool.nodes)} nodes\n", file=sys.stderr, flush=True)

    # Results tracking
    all_results = {}

    # Test each batch size
    for batch_size in TEST_SIZES:
        print(f"\n{'='*80}", file=sys.stderr, flush=True)
        print(f"BATCH SIZE: {batch_size} texts", file=sys.stderr, flush=True)
        print(f"{'='*80}", file=sys.stderr, flush=True)

        texts = generate_test_texts(batch_size)
        results = {}

        # Approach 1: SOLLOL adaptive (RECOMMENDED)
        results["adaptive"] = benchmark_approach(
            pool,
            "SOLLOL embed_batch (adaptive)",
            lambda t: pool.embed_batch(MODEL, t, use_adaptive=True, priority=7),
            texts,
        )

        # Approach 2: SOLLOL forced parallel (4 workers)
        results["parallel_4"] = benchmark_approach(
            pool,
            "SOLLOL embed_batch (parallel, 4 workers)",
            lambda t: pool.embed_batch(MODEL, t, use_adaptive=False, max_workers=4, priority=7),
            texts,
        )

        # Approach 3: SOLLOL forced parallel (2 workers - conservative)
        results["parallel_2"] = benchmark_approach(
            pool,
            "SOLLOL embed_batch (parallel, 2 workers)",
            lambda t: pool.embed_batch(MODEL, t, use_adaptive=False, max_workers=2, priority=7),
            texts,
        )

        # Approach 4: SOLLOL sequential (1 worker)
        results["sequential"] = benchmark_approach(
            pool,
            "SOLLOL embed_batch (sequential, 1 worker)",
            lambda t: pool.embed_batch(MODEL, t, use_adaptive=False, max_workers=1, priority=7),
            texts,
        )

        # Approach 5: Legacy parallel_embedder
        results["legacy"] = benchmark_approach(
            pool, "Legacy embed_batch_parallel", lambda t: embed_batch_parallel(pool, MODEL, t, max_workers=4), texts
        )

        all_results[batch_size] = results

        # Print summary for this batch size
        print(f"\n  📊 Summary for batch_size={batch_size}:", file=sys.stderr, flush=True)
        successful = [(name, dur) for name, (success, dur, err) in results.items() if success]
        if successful:
            successful.sort(key=lambda x: x[1])  # Sort by duration
            fastest_name, fastest_time = successful[0]
            print(
                f"    🏆 Fastest: {fastest_name} = {fastest_time:.2f}s ({batch_size/fastest_time:.1f} emb/sec)",
                file=sys.stderr,
                flush=True,
            )

            # Show speedup comparison
            for name, dur in successful[1:]:
                speedup = dur / fastest_time
                print(f"       vs {name}: {speedup:.2f}x slower ({dur:.2f}s)", file=sys.stderr, flush=True)
        else:
            print(f"    ❌ All approaches failed!", file=sys.stderr, flush=True)

    # Final summary
    print(f"\n\n{'='*80}", file=sys.stderr, flush=True)
    print("FINAL SUMMARY", file=sys.stderr, flush=True)
    print(f"{'='*80}", file=sys.stderr, flush=True)

    # Find best approach across all batch sizes
    approach_scores = {}
    for batch_size, results in all_results.items():
        for approach_name, (success, duration, error) in results.items():
            if success:
                if approach_name not in approach_scores:
                    approach_scores[approach_name] = []
                approach_scores[approach_name].append((batch_size, duration))

    print("\nApproach Performance by Batch Size:", file=sys.stderr, flush=True)
    print(f"{'Approach':<40} {'Avg Speed':<15} {'Success Rate'}", file=sys.stderr, flush=True)
    print("-" * 80, file=sys.stderr, flush=True)

    for approach_name in ["adaptive", "parallel_4", "parallel_2", "sequential", "legacy"]:
        if approach_name in approach_scores:
            scores = approach_scores[approach_name]
            total_texts = sum(bs for bs, _ in scores)
            total_time = sum(dur for _, dur in scores)
            avg_speed = total_texts / total_time if total_time > 0 else 0
            success_rate = len(scores) / len(TEST_SIZES) * 100

            print(f"{approach_name:<40} {avg_speed:>8.1f} emb/s   {success_rate:>5.0f}%", file=sys.stderr, flush=True)
        else:
            print(f"{approach_name:<40} {'FAILED':<15} 0%", file=sys.stderr, flush=True)

    print(f"\n{'='*80}", file=sys.stderr, flush=True)
    print("✅ Benchmark complete!", file=sys.stderr, flush=True)
    print(f"{'='*80}\n", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
