"""
GPU Controller for FlockParse
Programmatically control GPU/CPU assignment for models on distributed nodes
"""

import requests
import json
import time
from typing import Dict, List, Optional, Tuple

class GPUController:
    """Control GPU/CPU assignment for Ollama models across distributed nodes."""

    def __init__(self):
        pass

    def get_model_status(self, node_url: str) -> Dict:
        """
        Get current model loading status (GPU vs CPU).
        Returns which models are in VRAM vs RAM.
        """
        try:
            response = requests.get(f"{node_url}/api/ps", timeout=5)
            if response.status_code != 200:
                return {"error": "Failed to connect"}

            ps_data = response.json()
            models = ps_data.get("models", [])

            status = {
                'node_url': node_url,
                'models': [],
                'gpu_count': 0,
                'cpu_count': 0
            }

            for model_info in models:
                model_name = model_info.get("name", "unknown")
                size_vram = model_info.get("size_vram", 0)
                size_total = model_info.get("size", 0)

                location = 'GPU (VRAM)' if size_vram > 0 else 'CPU (RAM)'
                if size_vram > 0:
                    status['gpu_count'] += 1
                else:
                    status['cpu_count'] += 1

                status['models'].append({
                    'name': model_name,
                    'location': location,
                    'size_mb': size_total / (1024**2),
                    'vram_mb': size_vram / (1024**2)
                })

            return status

        except Exception as e:
            return {"error": str(e)}

    def force_gpu_load(self, node_url: str, model_name: str, num_gpu_layers: int = -1) -> Dict:
        """
        Force a model to load on GPU by unloading and reloading with GPU layers.

        Args:
            node_url: Ollama node URL
            model_name: Model to load (e.g., "mxbai-embed-large")
            num_gpu_layers: Number of layers to load on GPU (-1 = all layers)

        Returns:
            Status dictionary
        """
        try:
            # Step 1: Unload the model (by setting keep_alive to 0)
            print(f"🔄 Unloading {model_name} from {node_url}...")
            unload_response = requests.post(
                f"{node_url}/api/generate",
                json={
                    "model": model_name,
                    "keep_alive": 0  # Unload immediately
                },
                timeout=10
            )

            time.sleep(2)  # Wait for unload

            # Step 2: Reload with GPU configuration
            print(f"🚀 Reloading {model_name} on GPU...")

            # For embedding models, use embed endpoint
            if 'embed' in model_name.lower():
                load_response = requests.post(
                    f"{node_url}/api/embed",
                    json={
                        "model": model_name,
                        "input": "warmup",  # Small warmup request
                        "options": {
                            "num_gpu": num_gpu_layers  # Force GPU
                        },
                        "keep_alive": "1h"  # Keep loaded
                    },
                    timeout=30
                )
            else:
                # For chat models, use generate endpoint
                load_response = requests.post(
                    f"{node_url}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": "warmup",
                        "options": {
                            "num_gpu": num_gpu_layers  # Force GPU
                        },
                        "keep_alive": "1h"
                    },
                    timeout=30
                )

            time.sleep(2)  # Wait for load

            # Step 3: Verify GPU loading
            status = self.get_model_status(node_url)

            for model in status.get('models', []):
                if model_name in model['name']:
                    if 'GPU' in model['location']:
                        return {
                            'success': True,
                            'message': f"✅ {model_name} now on GPU",
                            'location': model['location'],
                            'vram_mb': model['vram_mb']
                        }
                    else:
                        return {
                            'success': False,
                            'message': f"⚠️  {model_name} still on CPU (may need more VRAM)",
                            'location': model['location']
                        }

            return {
                'success': False,
                'message': f"⚠️  {model_name} not found after reload"
            }

        except Exception as e:
            return {
                'success': False,
                'message': f"❌ Error: {str(e)}"
            }

    def force_cpu_load(self, node_url: str, model_name: str) -> Dict:
        """
        Force a model to load on CPU (RAM) instead of GPU.

        Useful for:
        - Freeing up VRAM for larger models
        - Testing CPU performance
        - Working around GPU issues
        """
        try:
            print(f"🔄 Forcing {model_name} to CPU on {node_url}...")

            # Unload model
            requests.post(
                f"{node_url}/api/generate",
                json={"model": model_name, "keep_alive": 0},
                timeout=10
            )
            time.sleep(2)

            # Reload with CPU-only configuration
            if 'embed' in model_name.lower():
                requests.post(
                    f"{node_url}/api/embed",
                    json={
                        "model": model_name,
                        "input": "warmup",
                        "options": {
                            "num_gpu": 0  # Force CPU
                        },
                        "keep_alive": "1h"
                    },
                    timeout=30
                )
            else:
                requests.post(
                    f"{node_url}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": "warmup",
                        "options": {
                            "num_gpu": 0  # Force CPU
                        },
                        "keep_alive": "1h"
                    },
                    timeout=30
                )

            time.sleep(2)

            # Verify
            status = self.get_model_status(node_url)
            for model in status.get('models', []):
                if model_name in model['name']:
                    return {
                        'success': True,
                        'message': f"✅ {model_name} now on CPU",
                        'location': model['location']
                    }

            return {'success': False, 'message': "Model not found"}

        except Exception as e:
            return {'success': False, 'message': f"Error: {str(e)}"}

    def optimize_cluster(self, nodes: List[str], gpu_priority_models: List[str]) -> Dict:
        """
        Optimize model placement across cluster.

        Strategy:
        1. Load priority models on GPU nodes
        2. Load other models on CPU nodes
        3. Balance VRAM usage across GPU nodes

        Args:
            nodes: List of Ollama node URLs
            gpu_priority_models: Models that should prefer GPU (e.g., ["mxbai-embed-large", "llama3.1"])

        Returns:
            Optimization report
        """
        print("🔧 Optimizing cluster GPU/CPU assignment...")

        report = {
            'gpu_nodes': [],
            'cpu_nodes': [],
            'assignments': []
        }

        # Classify nodes by GPU capability
        for node in nodes:
            status = self.get_model_status(node)
            if status.get('gpu_count', 0) > 0 or 'error' not in status:
                # Has GPU or unknown
                report['gpu_nodes'].append(node)
            else:
                report['cpu_nodes'].append(node)

        # Assign priority models to GPU nodes
        for model_name in gpu_priority_models:
            for gpu_node in report['gpu_nodes']:
                result = self.force_gpu_load(gpu_node, model_name)
                report['assignments'].append({
                    'node': gpu_node,
                    'model': model_name,
                    'target': 'GPU',
                    'result': result
                })

        return report

    def print_cluster_status(self, nodes: List[str]):
        """Print formatted cluster GPU/CPU status."""
        print("\n" + "="*70)
        print("🌐 DISTRIBUTED CLUSTER GPU/CPU STATUS")
        print("="*70)

        for node_url in nodes:
            status = self.get_model_status(node_url)

            if 'error' in status:
                print(f"\n❌ {node_url}: {status['error']}")
                continue

            gpu_count = status.get('gpu_count', 0)
            cpu_count = status.get('cpu_count', 0)
            total = gpu_count + cpu_count

            if gpu_count > 0:
                node_type = f"🚀 GPU ({gpu_count}/{total} models on GPU)"
            else:
                node_type = f"🐢 CPU (all {cpu_count} models on CPU)"

            print(f"\n{node_type} {node_url}:")

            for model in status.get('models', []):
                location_emoji = "🚀" if "GPU" in model['location'] else "🐢"
                print(f"   {location_emoji} {model['name']}")
                print(f"      Location: {model['location']}")
                print(f"      Size: {model['size_mb']:.1f} MB")
                if model['vram_mb'] > 0:
                    print(f"      VRAM: {model['vram_mb']:.1f} MB")

        print("="*70 + "\n")


def main():
    """Example usage and testing."""
    controller = GPUController()

    # Test nodes
    nodes = [
        "http://localhost:11434",
        "http://10.9.66.124:11434",
        "http://10.9.66.154:11434"
    ]

    # Show current status
    print("📊 Current Cluster Status:")
    controller.print_cluster_status(nodes)

    # Example: Force embedding model to GPU on specific node
    print("\n🔧 Example: Force mxbai-embed-large to GPU on 10.9.66.124...")
    result = controller.force_gpu_load(
        "http://10.9.66.124:11434",
        "mxbai-embed-large"
    )
    print(f"Result: {result['message']}")

    # Show updated status
    print("\n📊 Updated Cluster Status:")
    controller.print_cluster_status(nodes)


if __name__ == "__main__":
    main()
