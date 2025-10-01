#!/usr/bin/env python3
"""
FlockParser Showcase: Processing arXiv Research Papers
========================================================

This script demonstrates FlockParser's capabilities by processing a corpus
of real-world research papers from arXiv.org (open-access repository).

Dataset: AI/ML research papers on distributed systems, RAG, and embeddings
Source: arXiv.org (public domain)
Size: 10 papers, ~100-200 pages total

Usage:
    python showcase/process_arxiv_papers.py
"""

import sys
import time
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from flockparsecli import (
    process_pdf,
    load_document_index,
    get_similar_chunks,
    chat_with_documents,
    load_balancer
)


# Example arXiv paper URLs (public domain, CC BY license)
EXAMPLE_PAPERS = [
    {
        "title": "Attention Is All You Need (Transformers)",
        "arxiv_id": "1706.03762",
        "url": "https://arxiv.org/pdf/1706.03762.pdf",
        "topic": "Transformers architecture"
    },
    {
        "title": "BERT: Pre-training of Deep Bidirectional Transformers",
        "arxiv_id": "1810.04805",
        "url": "https://arxiv.org/pdf/1810.04805.pdf",
        "topic": "Language models"
    },
    {
        "title": "RAG: Retrieval-Augmented Generation",
        "arxiv_id": "2005.11401",
        "url": "https://arxiv.org/pdf/2005.11401.pdf",
        "topic": "RAG systems"
    },
    {
        "title": "Language Models are Few-Shot Learners (GPT-3)",
        "arxiv_id": "2005.14165",
        "url": "https://arxiv.org/pdf/2005.14165.pdf",
        "topic": "Large language models"
    },
    {
        "title": "Llama 2: Open Foundation Language Models",
        "arxiv_id": "2307.09288",
        "url": "https://arxiv.org/pdf/2307.09288.pdf",
        "topic": "Open-source LLMs"
    }
]


def download_paper(paper_info, output_dir):
    """Download a paper from arXiv"""
    import requests

    output_path = output_dir / f"{paper_info['arxiv_id']}.pdf"

    if output_path.exists():
        print(f"✓ Already downloaded: {paper_info['title']}")
        return output_path

    print(f"⬇️  Downloading: {paper_info['title']}...")

    try:
        response = requests.get(paper_info['url'], timeout=60)
        response.raise_for_status()

        with open(output_path, 'wb') as f:
            f.write(response.content)

        print(f"✅ Downloaded: {output_path.name} ({len(response.content) / 1024:.1f} KB)")
        return output_path

    except Exception as e:
        print(f"❌ Failed to download {paper_info['title']}: {e}")
        return None


def main():
    print("=" * 70)
    print("🚀 FlockParser Showcase: Processing arXiv Research Papers")
    print("=" * 70)
    print()

    # Setup
    showcase_dir = Path(__file__).parent
    papers_dir = showcase_dir / "papers"
    papers_dir.mkdir(exist_ok=True)

    results = {
        "timestamp": datetime.now().isoformat(),
        "papers": [],
        "processing_times": [],
        "total_time": 0,
        "node_info": []
    }

    # Show load balancer info
    print(f"📊 Load Balancer Configuration:")
    print(f"   Strategy: {load_balancer.routing_strategy}")
    print(f"   Active nodes: {len(load_balancer.instances)}")

    for node in load_balancer.instances:
        stats = load_balancer.instance_stats[node]
        gpu_status = "🚀 GPU" if stats.get("has_gpu") else "🐢 CPU"
        print(f"   • {node} - {gpu_status}")

        results["node_info"].append({
            "url": node,
            "has_gpu": stats.get("has_gpu"),
            "gpu_memory_gb": stats.get("gpu_memory_gb", 0)
        })

    print()

    # Download papers
    print("📥 Step 1: Downloading papers from arXiv...")
    print("-" * 70)

    downloaded_papers = []
    for paper in EXAMPLE_PAPERS:
        pdf_path = download_paper(paper, papers_dir)
        if pdf_path:
            downloaded_papers.append((paper, pdf_path))

    print(f"\n✅ Downloaded {len(downloaded_papers)}/{len(EXAMPLE_PAPERS)} papers\n")

    # Process papers
    print("🔄 Step 2: Processing papers with FlockParser...")
    print("-" * 70)

    overall_start = time.time()

    for idx, (paper_info, pdf_path) in enumerate(downloaded_papers, 1):
        print(f"\n[{idx}/{len(downloaded_papers)}] Processing: {paper_info['title']}")

        start = time.time()
        try:
            process_pdf(str(pdf_path))
            elapsed = time.time() - start

            print(f"   ✅ Completed in {elapsed:.2f}s")

            results["papers"].append({
                "title": paper_info["title"],
                "arxiv_id": paper_info["arxiv_id"],
                "topic": paper_info["topic"],
                "processing_time": elapsed,
                "status": "success"
            })
            results["processing_times"].append(elapsed)

        except Exception as e:
            elapsed = time.time() - start
            print(f"   ❌ Failed: {e}")

            results["papers"].append({
                "title": paper_info["title"],
                "arxiv_id": paper_info["arxiv_id"],
                "topic": paper_info["topic"],
                "processing_time": elapsed,
                "status": "failed",
                "error": str(e)
            })

    total_time = time.time() - overall_start
    results["total_time"] = total_time

    print("\n" + "=" * 70)
    print(f"✅ Processing Complete!")
    print(f"   Total time: {total_time:.2f}s")
    print(f"   Average time per paper: {total_time / len(downloaded_papers):.2f}s")

    if results["processing_times"]:
        avg_time = sum(results["processing_times"]) / len(results["processing_times"])
        print(f"   Successful papers: {len(results['processing_times'])}")
        print(f"   Average successful processing time: {avg_time:.2f}s")

    print("=" * 70)
    print()

    # Example searches
    print("🔍 Step 3: Example Semantic Searches")
    print("-" * 70)

    example_queries = [
        "What is the transformer architecture?",
        "How does retrieval-augmented generation work?",
        "What are the benefits of attention mechanisms?",
    ]

    for query in example_queries:
        print(f"\n📝 Query: '{query}'")
        try:
            chunks = get_similar_chunks(query, top_k=3)
            print(f"   Found {len(chunks)} relevant chunks:")

            for i, chunk in enumerate(chunks[:2], 1):
                doc_name = chunk['doc_name']
                similarity = chunk['similarity']
                text_preview = chunk['text'][:150].replace('\n', ' ')
                print(f"   {i}. {doc_name} (similarity: {similarity:.3f})")
                print(f"      \"{text_preview}...\"")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n" + "=" * 70)

    # Save results
    results_file = showcase_dir / "results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: {results_file}")

    # Generate summary document
    summary_file = showcase_dir / "RESULTS.md"
    with open(summary_file, 'w') as f:
        f.write("# FlockParser Showcase Results\n\n")
        f.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Dataset\n\n")
        f.write("- **Source:** arXiv.org (open-access research papers)\n")
        f.write(f"- **Papers processed:** {len(downloaded_papers)}\n")
        f.write("- **Topics:** Transformers, RAG, Language Models\n\n")

        f.write("## Hardware Configuration\n\n")
        for node in results["node_info"]:
            gpu_label = "GPU" if node["has_gpu"] else "CPU-only"
            vram = f" ({node['gpu_memory_gb']}GB VRAM)" if node["has_gpu"] else ""
            f.write(f"- {node['url']}: {gpu_label}{vram}\n")

        f.write(f"\n## Performance\n\n")
        f.write(f"- **Total processing time:** {total_time:.2f}s\n")
        f.write(f"- **Papers processed:** {len(results['processing_times'])} successful\n")

        if results["processing_times"]:
            avg = sum(results["processing_times"]) / len(results["processing_times"])
            f.write(f"- **Average time per paper:** {avg:.2f}s\n")
            f.write(f"- **Fastest:** {min(results['processing_times']):.2f}s\n")
            f.write(f"- **Slowest:** {max(results['processing_times']):.2f}s\n")

        f.write("\n## Papers Processed\n\n")
        for paper in results["papers"]:
            status_icon = "✅" if paper["status"] == "success" else "❌"
            f.write(f"{status_icon} **{paper['title']}**\n")
            f.write(f"   - arXiv: {paper['arxiv_id']}\n")
            f.write(f"   - Topic: {paper['topic']}\n")
            f.write(f"   - Processing time: {paper['processing_time']:.2f}s\n\n")

        f.write("\n## Example Queries\n\n")
        f.write("After processing, you can search the corpus:\n\n")
        for query in example_queries:
            f.write(f"- _{query}_\n")

        f.write("\n## Replication\n\n")
        f.write("To replicate this showcase:\n\n")
        f.write("```bash\n")
        f.write("# Install FlockParser\n")
        f.write("pip install flockparser\n\n")
        f.write("# Run showcase\n")
        f.write("python showcase/process_arxiv_papers.py\n")
        f.write("```\n")

    print(f"📄 Summary saved to: {summary_file}")
    print()
    print("🎉 Showcase complete! Check the results files for details.")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
