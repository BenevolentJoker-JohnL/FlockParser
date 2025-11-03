#!/usr/bin/env python3
"""
Profile FlockParser PDF processing to identify performance bottlenecks.
"""

import time
import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def profile_pdf_processing(pdf_path):
    """Profile a PDF processing workflow."""
    logger.info("=" * 80)
    logger.info("FlockParser PDF Processing Profiler")
    logger.info("=" * 80)
    logger.info(f"\nPDF: {pdf_path}\n")

    # Profile the full process
    logger.info("=" * 80)
    logger.info("Starting PDF Processing")
    logger.info("=" * 80)

    total_start = time.time()

    # Stage 1: Text extraction
    logger.info("\n📄 Stage 1: Text Extraction")
    stage1_start = time.time()

    import pdfplumber

    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = "\n\n".join([page.extract_text() or "" for page in pdf.pages])
            num_pages = len(pdf.pages)
    except Exception as e:
        logger.error(f"Failed to extract text: {e}")
        return

    stage1_time = time.time() - stage1_start
    logger.info(f"✅ Extracted {len(text)} chars from {num_pages} pages in {stage1_time:.2f}s")

    # Stage 2: Chunking
    logger.info("\n✂️  Stage 2: Text Chunking")
    stage2_start = time.time()

    from flockparsecli import chunk_text

    chunks = chunk_text(text)

    stage2_time = time.time() - stage2_start
    logger.info(f"✅ Created {len(chunks)} chunks in {stage2_time:.2f}s")

    # Stage 3: Embedding with cache
    logger.info("\n🧠 Stage 3: Embedding Generation (with cache)")
    stage3_start = time.time()

    from flockparsecli import setup_load_balancer, EMBEDDING_MODEL, load_embedding_cache, save_embedding_cache
    import hashlib

    # Initialize load_balancer
    logger.info("Initializing SOLLOL load balancer...")
    load_balancer = setup_load_balancer()

    cache = load_embedding_cache()
    logger.info(f"📦 Loaded cache with {len(cache)} entries")

    # Check which chunks need embedding
    uncached_chunks = []
    cached_count = 0
    for chunk in chunks:
        text_hash = hashlib.md5(chunk.encode()).hexdigest()
        if text_hash not in cache:
            uncached_chunks.append(chunk)
        else:
            cached_count += 1

    logger.info(f"✅ {cached_count} chunks in cache, {len(uncached_chunks)} need embedding")

    # Embed uncached chunks in batches
    if uncached_chunks:
        batch_size = 100
        embed_total_time = 0

        for i in range(0, len(uncached_chunks), batch_size):
            batch = uncached_chunks[i : i + batch_size]
            logger.info(f"\n   Batch {i//batch_size + 1}: {len(batch)} chunks")

            # Time the embedding call
            embed_start = time.time()
            batch_results = load_balancer.embed_batch(EMBEDDING_MODEL, batch)
            embed_elapsed = time.time() - embed_start
            embed_total_time += embed_elapsed

            logger.info(f"   ⏱️  embed_batch: {embed_elapsed:.2f}s ({len(batch)/embed_elapsed:.1f} chunks/s)")

            # Cache results
            for chunk, result in zip(batch, batch_results):
                if result:
                    text_hash = hashlib.md5(chunk.encode()).hexdigest()
                    embeddings = result.get("embeddings", [])
                    embedding = embeddings[0] if embeddings else []
                    cache[text_hash] = embedding

            # Time the cache save
            save_start = time.time()
            save_embedding_cache(cache)
            save_elapsed = time.time() - save_start
            logger.info(f"   ⏱️  save_cache: {save_elapsed:.2f}s")

        logger.info(f"\n📊 Embedding stats:")
        logger.info(f"   Total embedding time: {embed_total_time:.2f}s")
        logger.info(f"   Throughput: {len(uncached_chunks)/embed_total_time:.1f} chunks/s")

    stage3_time = time.time() - stage3_start
    logger.info(f"\n✅ Stage 3 total: {stage3_time:.2f}s")

    # Stage 4: File I/O (writing chunk JSON files)
    logger.info("\n💾 Stage 4: Writing Chunk Files")
    stage4_start = time.time()

    from flockparsecli import KB_DIR
    import json

    chunk_files_written = 0
    for i, chunk in enumerate(chunks[:10]):  # Only write first 10 for profiling
        text_hash = hashlib.md5(chunk.encode()).hexdigest()
        embedding = cache.get(text_hash, [])

        chunk_file = KB_DIR / f"profile_test_chunk_{i}.json"
        chunk_data = {"text": chunk, "embedding": embedding}

        with open(chunk_file, "w") as f:
            json.dump(chunk_data, f)
        chunk_files_written += 1

    stage4_time = time.time() - stage4_start
    logger.info(f"✅ Wrote {chunk_files_written} chunk files in {stage4_time:.2f}s")
    logger.info(f"   Projected time for all {len(chunks)} chunks: {(stage4_time/chunk_files_written)*len(chunks):.2f}s")

    # Summary
    total_time = time.time() - total_start

    logger.info("\n" + "=" * 80)
    logger.info("⏱️  PERFORMANCE SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Stage 1 (Text Extraction): {stage1_time:.2f}s ({stage1_time/total_time*100:.1f}%)")
    logger.info(f"Stage 2 (Chunking):        {stage2_time:.2f}s ({stage2_time/total_time*100:.1f}%)")
    logger.info(f"Stage 3 (Embedding):       {stage3_time:.2f}s ({stage3_time/total_time*100:.1f}%)")
    logger.info(f"Stage 4 (File I/O sample): {stage4_time:.2f}s")
    logger.info(f"\nTotal time: {total_time:.2f}s")
    logger.info("=" * 80)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python profile_pdf_processing.py <pdf_file>")
        print("\nExample:")
        print("  python profile_pdf_processing.py testpdfs/sample.pdf")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)

    profile_pdf_processing(pdf_path)
