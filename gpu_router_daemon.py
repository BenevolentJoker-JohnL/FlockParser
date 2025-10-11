#!/usr/bin/env python3
"""
GPU Router Daemon - Standalone Service
Intelligent GPU resource management and routing for distributed Ollama clusters.

This daemon runs independently and continuously monitors your cluster,
making intelligent routing decisions based on actual VRAM capacity.
"""

import sys
import time
import signal
import logging
from pathlib import Path
from typing import Dict, List
import yaml
from datetime import datetime

from sollol.intelligent_gpu_router import IntelligentGPURouter


class GPURouterDaemon:
    """Standalone daemon for intelligent GPU routing."""

    def __init__(self, config_path: str = "./gpu_router_config.yaml"):
        self.config_path = Path(config_path)
        self.running = False
        self.router = None

        # Setup logging
        self._setup_logging()

        # Load configuration
        self.config = self._load_config()

        # Initialize router
        self._initialize_router()

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.logger.info("🚀 GPU Router Daemon initialized")

    def _setup_logging(self):
        """Setup logging to file and console."""
        log_dir = Path("./logs")
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "gpu_router_daemon.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger("GPURouterDaemon")

    def _load_config(self) -> Dict:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            self.logger.error(f"❌ Configuration file not found: {self.config_path}")
            self.logger.info("💡 Creating default configuration...")
            self._create_default_config()

        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            self.logger.info(f"✅ Configuration loaded from {self.config_path}")
            return config
        except Exception as e:
            self.logger.error(f"❌ Error loading configuration: {e}")
            sys.exit(1)

    def _create_default_config(self):
        """Create default configuration file."""
        default_config = {
            'nodes': [
                'http://localhost:11434',
            ],
            'priority_models': [
                'mxbai-embed-large',
                'nomic-embed-text',
            ],
            'check_interval': 300,  # 5 minutes
            'vram_safety_margin': 0.8,
            'auto_optimize': True,
            'log_level': 'INFO'
        }

        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)

        self.logger.info(f"✅ Default configuration created at {self.config_path}")
        self.logger.info("📝 Please edit the configuration and restart the daemon")

    def _initialize_router(self):
        """Initialize the intelligent GPU router."""
        nodes = self.config.get('nodes', [])
        if not nodes:
            self.logger.error("❌ No nodes configured")
            sys.exit(1)

        self.logger.info(f"🔧 Initializing router for {len(nodes)} nodes...")
        self.router = IntelligentGPURouter(nodes)

        # Update safety margin if configured
        safety_margin = self.config.get('vram_safety_margin', 0.8)
        self.router.vram_safety_margin = safety_margin

        self.logger.info(f"✅ Router initialized with {safety_margin*100:.0f}% VRAM safety margin")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        signal_name = signal.Signals(signum).name
        self.logger.info(f"🛑 Received {signal_name}, shutting down...")
        self.stop()
        sys.exit(0)

    def start(self):
        """Start the daemon main loop."""
        self.running = True
        check_interval = self.config.get('check_interval', 300)
        auto_optimize = self.config.get('auto_optimize', True)
        priority_models = self.config.get('priority_models', [])

        self.logger.info("=" * 70)
        self.logger.info("🚀 GPU Router Daemon Starting")
        self.logger.info("=" * 70)
        self.logger.info(f"📍 Nodes: {len(self.config['nodes'])}")
        self.logger.info(f"🎯 Priority models: {len(priority_models)}")
        self.logger.info(f"⏱️  Check interval: {check_interval}s")
        self.logger.info(f"🤖 Auto-optimize: {auto_optimize}")
        self.logger.info("=" * 70)

        # Initial cluster report
        self.logger.info("\n📊 Initial Cluster Capabilities:")
        self.router.print_cluster_report()

        iteration = 0
        while self.running:
            try:
                iteration += 1
                self.logger.info(f"\n🔄 Optimization cycle #{iteration} ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")

                if auto_optimize and priority_models:
                    # Run optimization
                    self.logger.info(f"🧠 Optimizing {len(priority_models)} priority models...")
                    self.router.optimize_cluster(priority_models)
                else:
                    self.logger.info("ℹ️  Auto-optimize disabled, monitoring only")
                    # Just print status
                    self.router.print_cluster_report()

                # Wait for next cycle
                self.logger.info(f"⏳ Next check in {check_interval}s...")
                time.sleep(check_interval)

            except Exception as e:
                self.logger.error(f"❌ Error in main loop: {e}")
                self.logger.exception(e)
                self.logger.info("🔄 Continuing after error...")
                time.sleep(60)  # Wait 1 minute after error

    def stop(self):
        """Stop the daemon."""
        self.logger.info("🛑 Stopping GPU Router Daemon...")
        self.running = False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="GPU Router Daemon - Intelligent GPU management for Ollama clusters"
    )
    parser.add_argument(
        '--config',
        default='./gpu_router_config.yaml',
        help='Path to configuration file (default: ./gpu_router_config.yaml)'
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Print cluster report and exit (no daemon mode)'
    )

    args = parser.parse_args()

    # Create daemon
    daemon = GPURouterDaemon(config_path=args.config)

    if args.report_only:
        # Just print report and exit
        print("\n" + "=" * 70)
        print("📊 CLUSTER CAPABILITIES REPORT")
        print("=" * 70)
        daemon.router.print_cluster_report()
        sys.exit(0)

    # Start daemon
    try:
        daemon.start()
    except KeyboardInterrupt:
        daemon.logger.info("\n🛑 Interrupted by user")
        daemon.stop()
    except Exception as e:
        daemon.logger.error(f"❌ Fatal error: {e}")
        daemon.logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()