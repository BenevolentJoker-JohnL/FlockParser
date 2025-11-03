#!/usr/bin/env python3
"""
Quick test to see if basic embed_batch works without hanging.
"""

import time
import sys
from pathlib import Path
from sollol import OllamaPool
from sollol_compat import add_flockparser_methods

MODEL = "nomic-embed-text"


def main():
    print("=" * 80, file=sys.stderr, flush=True)
    print("QUICK EMBED_BATCH TEST", file=sys.stderr, flush=True)
    print("=" * 80, file=sys.stderr, flush=True)

    # Initialize pool
    print("\nInitializing pool...", file=sys.stderr, flush=True)
    pool = OllamaPool(enable_dask=False)
    pool = add_flockparser_methods(pool, Path("knowledge_base"))

    # Add nodes
    print("Adding nodes...", file=sys.stderr, flush=True)
    pool.add_node("192.168.0.166", 11434)
    pool.add_node("192.168.0.233", 11434)
    print(f"Pool ready with {len(pool.nodes)} nodes\n", file=sys.stderr, flush=True)

    # Test 1: Single embed
    print("Test 1: Single embed...", file=sys.stderr, flush=True)
    start = time.time()
    try:
        result = pool.embed(MODEL, "Test sentence", priority=7)
        print(f"  ✅ Success in {time.time()-start:.2f}s", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"  ❌ Failed: {e}", file=sys.stderr, flush=True)
        return

    # Test 2: Small batch with adaptive (5 texts)
    print("\nTest 2: Small batch (5 texts) with adaptive...", file=sys.stderr, flush=True)
    texts = [f"Test sentence {i}" for i in range(5)]
    start = time.time()
    try:
        results = pool.embed_batch(MODEL, texts, use_adaptive=True, priority=7)
        success = sum(1 for r in results if r is not None)
        print(f"  ✅ {success}/{len(texts)} in {time.time()-start:.2f}s", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"  ❌ Failed: {e}", file=sys.stderr, flush=True)
        return

    # Test 3: Medium batch with adaptive (20 texts)
    print("\nTest 3: Medium batch (20 texts) with adaptive...", file=sys.stderr, flush=True)
    texts = [f"Test sentence {i} with more content" for i in range(20)]
    start = time.time()
    try:
        results = pool.embed_batch(MODEL, texts, use_adaptive=True, priority=7)
        success = sum(1 for r in results if r is not None)
        duration = time.time() - start
        print(
            f"  ✅ {success}/{len(texts)} in {duration:.2f}s ({len(texts)/duration:.1f} emb/s)",
            file=sys.stderr,
            flush=True,
        )
    except Exception as e:
        print(f"  ❌ Failed: {e}", file=sys.stderr, flush=True)
        return

    # Test 4: Medium batch with sequential (max_workers=1)
    print("\nTest 4: Medium batch (20 texts) sequential...", file=sys.stderr, flush=True)
    start = time.time()
    try:
        results = pool.embed_batch(MODEL, texts, use_adaptive=False, max_workers=1, priority=7)
        success = sum(1 for r in results if r is not None)
        duration = time.time() - start
        print(
            f"  ✅ {success}/{len(texts)} in {duration:.2f}s ({len(texts)/duration:.1f} emb/s)",
            file=sys.stderr,
            flush=True,
        )
    except Exception as e:
        print(f"  ❌ Failed: {e}", file=sys.stderr, flush=True)
        return

    print("\n" + "=" * 80, file=sys.stderr, flush=True)
    print("✅ All tests passed!", file=sys.stderr, flush=True)
    print("=" * 80, file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
