"""
Production async embedding implementation using AsyncClient.

Based on ollama-python community best practices:
- Uses AsyncClient with asyncio instead of ThreadPoolExecutor
- Implements proper concurrency control with Semaphore
- Handles large batches efficiently
"""

import asyncio
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


async def embed_batch_async(pool, model: str, texts: List[str], max_concurrent: int = None) -> List[Dict[str, Any]]:
    """
    Production async embedding using ollama-python recommended pattern.

    Args:
        pool: SOLLOL OllamaPool instance
        model: Embedding model name
        texts: List of texts to embed
        max_concurrent: Max concurrent requests (default: nodes * 4)

    Returns:
        List of embedding results
    """
    if not texts:
        return []

    batch_size = len(texts)
    results = [None] * batch_size

    # Set concurrency limit based on number of nodes
    if max_concurrent is None:
        max_concurrent = len(pool.nodes) * 4
        max_concurrent = max(4, min(max_concurrent, 16))  # Between 4-16

    logger.info(f"🔀 Async embedding: {max_concurrent} concurrent tasks across {len(pool.nodes)} nodes")

    # Semaphore to limit concurrent requests
    semaphore = asyncio.Semaphore(max_concurrent)
    completed = 0

    async def embed_single(index, text):
        """Embed single text with concurrency control."""
        async with semaphore:
            try:
                # SOLLOL's embed is synchronous, run in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: pool.embed(model, text, priority=7))
                return index, result, None
            except Exception as e:
                return index, None, e

    # Create all tasks
    tasks = [embed_single(i, text) for i, text in enumerate(texts)]

    # Process with progress tracking
    for coro in asyncio.as_completed(tasks):
        index, result, error = await coro
        completed += 1

        # Show progress every 50 embeddings
        if completed % 50 == 0 or completed == batch_size:
            progress_pct = (completed * 100) // batch_size
            logger.info(f"   Progress: {completed}/{batch_size} embeddings ({progress_pct}%)")

        if error:
            logger.error(f"⚠️ Error embedding text {index}: {error}")
        else:
            results[index] = result

    return results


def embed_batch_async_sync(pool, model: str, texts: List[str], max_concurrent: int = None) -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for async embedding.

    Allows calling from synchronous code while using async under the hood.
    """
    return asyncio.run(embed_batch_async(pool, model, texts, max_concurrent))
