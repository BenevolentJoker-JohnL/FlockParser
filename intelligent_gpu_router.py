"""
Intelligent GPU Router for FlockParse
Makes smart decisions about which models should run on GPU vs CPU based on:
- Actual VRAM capacity
- Model sizes
- Current VRAM usage
- Performance requirements
"""

import requests
import json
import time
from typing import Dict, List, Optional, Tuple
from vram_monitor import VRAMMonitor
from gpu_controller import GPUController


class IntelligentGPURouter:
    """
    Smart GPU routing that makes decisions based on actual hardware capabilities.

    Example:
        Node with 4GB VRAM:
        - mxbai-embed-large (705MB) → GPU ✓
        - llama3.1:latest (4.7GB) → CPU ✗ (too large)
        - llama3.2:3b (1.9GB) → GPU ✓
    """

    def __init__(self, nodes: List[str]):
        self.nodes = nodes
        self.vram_monitor = VRAMMonitor()
        self.gpu_controller = GPUController()

        # Node capabilities cache
        self.node_capabilities = {}

        # Model size database (in MB)
        self.known_model_sizes = {
            'mxbai-embed-large': 705,
            'nomic-embed-text': 274,
            'all-minilm': 45,
            'llama3.1:latest': 4700,
            'llama3.1:8b': 4700,
            'llama3.1:70b': 40000,
            'llama3.2:1b': 1300,
            'llama3.2:3b': 1900,
            'qwen2.5-coder:0.5b': 500,
            'qwen2.5-coder:1.5b': 900,
            'qwen2.5-coder:3b': 1800,
            'qwen2.5-coder:7b': 4400,
            'codellama:7b': 3600,
            'codellama:13b': 6900,
        }

        # Safety margin (don't use 100% of VRAM)
        self.vram_safety_margin = 0.8  # Use max 80% of available VRAM

        # Discover node capabilities
        self._discover_capabilities()

    def _discover_capabilities(self):
        """Discover VRAM capacity and current usage for each node."""
        print("\n🔍 Discovering node capabilities...")

        for node_url in self.nodes:
            try:
                # Get VRAM info
                vram_info = self.vram_monitor.get_ollama_vram_usage(node_url)

                # Try to get actual GPU VRAM from hardware (if local)
                if 'localhost' in node_url or '127.0.0.1' in node_url:
                    local_gpu = self.vram_monitor.get_local_vram_info()
                    if local_gpu:
                        total_vram_mb = local_gpu.get('total_vram_mb', 0)
                    else:
                        total_vram_mb = 0
                else:
                    # For remote nodes, estimate from Ollama
                    total_vram_mb = self._estimate_total_vram(node_url)

                # Get currently loaded models
                current_usage_mb = vram_info.get('total_vram_mb', 0) if vram_info else 0
                has_gpu = total_vram_mb > 0 or (vram_info and vram_info.get('has_gpu_models', False))

                self.node_capabilities[node_url] = {
                    'total_vram_mb': total_vram_mb,
                    'current_usage_mb': current_usage_mb,
                    'free_vram_mb': max(0, total_vram_mb - current_usage_mb),
                    'usable_vram_mb': int(total_vram_mb * self.vram_safety_margin),
                    'has_gpu': has_gpu,
                    'loaded_models': vram_info.get('models', []) if vram_info else []
                }

                # Print discovery result
                if has_gpu:
                    print(f"   🚀 {node_url}")
                    print(f"      Total VRAM: {total_vram_mb:.0f} MB")
                    print(f"      Usable VRAM: {total_vram_mb * self.vram_safety_margin:.0f} MB (80% safety margin)")
                    print(f"      Free VRAM: {total_vram_mb - current_usage_mb:.0f} MB")
                else:
                    print(f"   🐢 {node_url} (CPU only)")

            except Exception as e:
                print(f"   ❌ {node_url}: Error - {str(e)}")
                self.node_capabilities[node_url] = {
                    'total_vram_mb': 0,
                    'has_gpu': False,
                    'error': str(e)
                }

    def _estimate_total_vram(self, node_url: str) -> int:
        """
        Estimate total VRAM by checking what models can load.
        This is a fallback when nvidia-smi isn't available remotely.
        """
        try:
            # Check if any models are currently in VRAM
            response = requests.get(f"{node_url}/api/ps", timeout=5)
            if response.status_code == 200:
                ps_data = response.json()
                models = ps_data.get("models", [])

                # If any model has size_vram > 0, estimate based on typical GPU sizes
                for model in models:
                    if model.get('size_vram', 0) > 0:
                        # Has GPU, estimate common sizes
                        # We'll return a conservative estimate
                        return 4096  # Assume 4GB as baseline

            return 0  # No GPU detected

        except:
            return 0

    def get_model_size(self, model_name: str) -> int:
        """Get model size in MB (from database or API)."""
        # Normalize model name
        normalized = model_name.lower().replace(':latest', '')

        # Check known sizes
        for known_model, size in self.known_model_sizes.items():
            if known_model in normalized or normalized in known_model:
                return size

        # Try to get from Ollama API
        for node_url in self.nodes:
            try:
                response = requests.get(f"{node_url}/api/show",
                                      json={"name": model_name},
                                      timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    # Try to get size from details
                    size_bytes = data.get('size', 0)
                    if size_bytes > 0:
                        return int(size_bytes / (1024**2))  # Convert to MB
            except:
                continue

        # Unknown size - assume large (conservative)
        print(f"   ⚠️  Unknown model size for {model_name}, assuming 5GB")
        return 5000

    def can_fit_on_gpu(self, node_url: str, model_name: str) -> Tuple[bool, str]:
        """
        Check if a model can fit on a specific node's GPU.

        Returns:
            (can_fit: bool, reason: str)
        """
        caps = self.node_capabilities.get(node_url, {})

        # Check if node has GPU
        if not caps.get('has_gpu', False):
            return False, "Node has no GPU"

        # Get model size
        model_size_mb = self.get_model_size(model_name)

        # Get usable VRAM (with safety margin)
        usable_vram_mb = caps.get('usable_vram_mb', 0)
        free_vram_mb = caps.get('free_vram_mb', 0)

        # Check if model fits in total usable VRAM
        if model_size_mb > usable_vram_mb:
            return False, f"Model too large ({model_size_mb}MB > {usable_vram_mb}MB usable VRAM)"

        # Check if enough free VRAM currently available
        if model_size_mb > free_vram_mb:
            return False, f"Not enough free VRAM ({model_size_mb}MB needed, {free_vram_mb}MB free)"

        return True, f"Fits in {usable_vram_mb}MB VRAM ({free_vram_mb}MB free)"

    def route_model(self, model_name: str) -> Dict:
        """
        Intelligently route a model to the best node.

        Returns routing decision with reasoning.
        """
        print(f"\n🎯 Routing decision for: {model_name}")
        model_size_mb = self.get_model_size(model_name)
        print(f"   Model size: {model_size_mb} MB")

        # Evaluate each node
        candidates = []

        for node_url in self.nodes:
            can_fit, reason = self.can_fit_on_gpu(node_url, model_name)
            caps = self.node_capabilities.get(node_url, {})

            if can_fit:
                # Calculate score (prefer nodes with more free VRAM)
                score = caps.get('free_vram_mb', 0)
                candidates.append({
                    'node': node_url,
                    'target': 'GPU',
                    'score': score,
                    'reason': reason
                })
                print(f"   ✅ {node_url} (GPU): {reason}")
            else:
                # CPU fallback
                candidates.append({
                    'node': node_url,
                    'target': 'CPU',
                    'score': 0,  # CPU is fallback, low score
                    'reason': reason
                })
                print(f"   ⏭️  {node_url} (CPU): {reason}")

        if not candidates:
            return {
                'model': model_name,
                'node': None,
                'target': 'CPU',
                'reason': 'No suitable nodes found'
            }

        # Pick best candidate (highest score = most free VRAM)
        best = max(candidates, key=lambda x: x['score'])

        print(f"\n   🏆 Best choice: {best['node']} ({best['target']})")
        print(f"      Reason: {best['reason']}")

        return {
            'model': model_name,
            'node': best['node'],
            'target': best['target'],
            'reason': best['reason'],
            'all_options': candidates
        }

    def optimize_cluster(self, priority_models: List[str] = None):
        """
        Optimize entire cluster with intelligent routing.

        Args:
            priority_models: Models to prioritize for GPU (default: embeddings)
        """
        if priority_models is None:
            priority_models = ['mxbai-embed-large', 'nomic-embed-text']

        print("\n🧠 Intelligent Cluster Optimization")
        print("="*70)

        # Rediscover capabilities (in case things changed)
        self._discover_capabilities()

        # Route each priority model
        routing_plan = []
        for model_name in priority_models:
            decision = self.route_model(model_name)
            routing_plan.append(decision)

        # Execute routing plan
        print("\n\n🚀 Executing Routing Plan")
        print("="*70)

        for plan in routing_plan:
            if plan['node'] and plan['target'] == 'GPU':
                print(f"\n📍 Loading {plan['model']} on GPU at {plan['node']}...")
                result = self.gpu_controller.force_gpu_load(plan['node'], plan['model'])
                print(f"   {result['message']}")
            else:
                print(f"\n📍 {plan['model']} → CPU ({plan['reason']})")

        print("\n✅ Optimization complete!")

    def print_cluster_report(self):
        """Print comprehensive cluster capabilities report."""
        print("\n" + "="*70)
        print("🌐 INTELLIGENT GPU ROUTER - CLUSTER REPORT")
        print("="*70)

        for node_url, caps in self.node_capabilities.items():
            if caps.get('has_gpu', False):
                total_vram = caps['total_vram_mb']
                usable_vram = caps['usable_vram_mb']
                free_vram = caps['free_vram_mb']

                print(f"\n🚀 GPU Node: {node_url}")
                print(f"   Total VRAM: {total_vram:.0f} MB")
                print(f"   Usable VRAM: {usable_vram:.0f} MB (80% safety)")
                print(f"   Free VRAM: {free_vram:.0f} MB")
                print(f"   Utilization: {((total_vram - free_vram) / total_vram * 100):.1f}%")

                print(f"\n   📦 Can fit these models:")
                # Check which common models fit
                for model, size in sorted(self.known_model_sizes.items(), key=lambda x: x[1]):
                    can_fit, reason = self.can_fit_on_gpu(node_url, model)
                    if can_fit:
                        print(f"      ✅ {model} ({size} MB)")
                    else:
                        print(f"      ❌ {model} ({size} MB) - {reason}")

                if caps.get('loaded_models'):
                    print(f"\n   🔄 Currently loaded:")
                    for model in caps['loaded_models']:
                        print(f"      - {model['name']} ({model['location']})")
            else:
                print(f"\n🐢 CPU-only Node: {node_url}")

        print("\n" + "="*70)


def main():
    """Example usage."""
    # Define your nodes
    nodes = [
        "http://localhost:11434",
        "http://10.9.66.124:11434",
        "http://10.9.66.154:11434"
    ]

    # Create router
    router = IntelligentGPURouter(nodes)

    # Print capabilities report
    router.print_cluster_report()

    # Test routing decisions
    print("\n\n" + "="*70)
    print("🧪 TESTING ROUTING DECISIONS")
    print("="*70)

    test_models = [
        'mxbai-embed-large',
        'llama3.2:3b',
        'llama3.1:latest',
        'codellama:13b'
    ]

    for model in test_models:
        router.route_model(model)

    # Optimize cluster
    print("\n\n")
    router.optimize_cluster(['mxbai-embed-large'])


if __name__ == "__main__":
    main()