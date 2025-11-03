"""
Legacy FlockParser's proven parallel embedding implementation.

Standalone function to avoid method binding issues with SOLLOL pool.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def embed_batch_parallel(
    pool, model: str, texts: List[str], max_workers: int = None, batch_size: int = 100
) -> List[Dict[str, Any]]:
    """
    Batch embedding using Legacy FlockParser's proven parallel approach.

    Processes texts in smaller batches to avoid overwhelming the system.
    Uses ThreadPoolExecutor with individual embed() calls distributed
    across nodes via SOLLOL's routing.

    Args:
        pool: SOLLOL OllamaPool instance
        model: Embedding model name
        texts: List of texts to embed
        max_workers: Number of parallel workers (default: nodes * 2)
        batch_size: Number of texts to process in each sub-batch (default: 100)

    Returns:
        List of embedding results
    """
    import sys

    print(f"DEBUG: embed_batch_parallel called with {len(texts) if texts else 0} texts", file=sys.stderr, flush=True)

    if not texts:
        return []

    print(f"DEBUG: Calculating total_texts...", file=sys.stderr, flush=True)
    total_texts = len(texts)
    print(f"DEBUG: total_texts = {total_texts}", file=sys.stderr, flush=True)

    print(f"DEBUG: Creating results list...", file=sys.stderr, flush=True)
    all_results = [None] * total_texts
    print(f"DEBUG: Results list created", file=sys.stderr, flush=True)

    # Use Legacy's proven worker count: 2x number of nodes
    print(f"DEBUG: Checking max_workers...", file=sys.stderr, flush=True)
    if max_workers is None:
        print(f"DEBUG: Accessing pool.nodes...", file=sys.stderr, flush=True)
        max_workers = len(pool.nodes) * 2
        print(f"DEBUG: pool.nodes accessed, max_workers = {max_workers}", file=sys.stderr, flush=True)
        max_workers = max(2, min(max_workers, 8))  # Between 2-8 workers
        print(f"DEBUG: max_workers clamped to {max_workers}", file=sys.stderr, flush=True)

    print(f"DEBUG: About to log info messages...", file=sys.stderr, flush=True)
    # TEMP: Bypass logger to avoid potential deadlock
    print(f"🔀 Processing {total_texts} texts in batches of {batch_size}", file=sys.stderr, flush=True)
    print(f"   Using {max_workers} workers across {len(pool.nodes)} nodes", file=sys.stderr, flush=True)

    # Process in batches
    for batch_start in range(0, total_texts, batch_size):
        batch_end = min(batch_start + batch_size, total_texts)
        batch_texts = texts[batch_start:batch_end]
        batch_count = len(batch_texts)

        print(
            f"📦 Processing batch {batch_start//batch_size + 1}/{(total_texts + batch_size - 1)//batch_size} ({batch_count} texts)",
            file=sys.stderr,
            flush=True,
        )

        def embed_single(local_index, text):
            """Embed single text using SOLLOL's routing."""
            try:
                result = pool.embed(model, text, priority=7)
                return local_index, result, None
            except Exception as e:
                return local_index, None, e

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(embed_single, i, text): i for i, text in enumerate(batch_texts)}

            completed_in_batch = 0
            for future in as_completed(futures):
                local_index, result, error = future.result()
                global_index = batch_start + local_index
                completed_in_batch += 1

                # Show progress every 25 embeddings within batch
                if completed_in_batch % 25 == 0 or completed_in_batch == batch_count:
                    batch_pct = (completed_in_batch * 100) // batch_count
                    total_pct = ((batch_start + completed_in_batch) * 100) // total_texts
                    print(
                        f"   Batch progress: {completed_in_batch}/{batch_count} ({batch_pct}%) | Total: {total_pct}%",
                        file=sys.stderr,
                        flush=True,
                    )

                if error:
                    print(f"⚠️ Error embedding text {global_index}: {error}", file=sys.stderr, flush=True)
                else:
                    all_results[global_index] = result

    print(f"✅ Completed all {total_texts} embeddings", file=sys.stderr, flush=True)
    return all_results
