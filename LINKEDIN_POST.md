# LinkedIn Post Draft

## Version 1: Technical Focus

I built a distributed document RAG system that automatically routes work across GPU/CPU clusters - taking processing time from 6 minutes down to 6 seconds.

**The interesting part isn't just "use a GPU"** - it's the automatic routing intelligence:

🔍 Auto-discovers nodes on the network
📊 Detects GPU vs CPU performance via VRAM monitoring
🎯 Decides sequential vs parallel routing based on speed ratios
⚡ Routes work to prevent slow nodes from bottlenecking

**Real demo results** (unedited timing shown on screen):
• Single CPU node: 372.76s
• Parallel multi-node: 159.79s (2.3x faster)
• GPU auto-routing: 6.04s (61.7x faster)

The system handles heterogeneous hardware automatically - no manual configuration needed. Built with Python, Ollama, ChromaDB, and implements the Model Context Protocol (MCP) for AI assistant integration.

76-second demo video: [LINK]
Open source (MIT): [GITHUB LINK]

#distributedsystems #machinelearning #opensource #python #rag

---

## Version 2: Problem/Solution Focus

**Problem:** Processing large document collections is slow. Adding more servers doesn't help if you can't route work intelligently across heterogeneous hardware.

**What I built:** A distributed document RAG system with automatic GPU detection and adaptive load balancing.

**Results:**
✅ 372 seconds → 6 seconds (61.7x speedup)
✅ Auto-discovers cluster nodes
✅ Adapts routing based on real-time performance
✅ 100% local processing (privacy-first)

**Tech:** Python, Ollama, ChromaDB, MCP protocol
**Demo:** 76 seconds showing it in action [LINK]
**Code:** Open source on GitHub [LINK]

The routing intelligence is the interesting part - it detects a GPU node is 60x faster and automatically routes accordingly, preventing slow nodes from becoming bottlenecks.

#softwareengineering #distributedsystems #ai #opensource

---

## Version 3: Career/Portfolio Angle

What I learned building a distributed document RAG system:

🎯 **Systems engineering matters more than AI features**
The 60x speedup came from intelligent routing, not just "adding a GPU." The system auto-discovers nodes, detects performance differences, and makes adaptive routing decisions.

📊 **Observability is critical**
Health scoring, VRAM monitoring, and performance tracking made debugging possible. Without it, you're flying blind.

🔒 **Privacy requirements drive architecture**
Built 4 interfaces (CLI, Web UI, REST API, MCP) with different privacy levels. CLI/Web UI are 100% local - no external API calls.

**Real results:**
• 372s → 6s processing time (demo video shows unedited timing)
• Handles GPU/CPU heterogeneous clusters automatically
• Production-ready with proper error handling, timeouts, failover

Open source on GitHub, built with Python/Ollama/ChromaDB.
76-second demo: [LINK]

Looking for mid/senior backend or distributed systems roles. DMs open.

#jobsearch #softwareengineering #python #distributedsystems #opensource

---

## Instructions for Posting

1. **Choose version** based on your goal:
   - Version 1: Showing off technical skills to engineers
   - Version 2: Broader audience (recruiters + engineers)
   - Version 3: Actively job searching

2. **Upload video** to YouTube first, get link

3. **Update links** in post:
   - Replace [LINK] with YouTube video URL
   - Replace [GITHUB LINK] with your repo URL

4. **Best time to post:**
   - Tuesday-Thursday, 8-10 AM (your timezone)
   - Avoid Monday mornings and Friday afternoons

5. **Engagement tips:**
   - Reply to every comment in first 2 hours
   - Ask a question at the end to drive comments
   - Share in relevant groups (Python, ML, Distributed Systems)

6. **Don't:**
   - Post and ghost (kills algorithm)
   - Over-hashtag (3-5 max)
   - Make it sound like an ad
