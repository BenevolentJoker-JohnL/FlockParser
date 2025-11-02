"""
Minimal compatibility layer for FlockParser-specific methods.
Extends SOLLOL's OllamaPool with FlockParser's expected API.
"""

import atexit
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from sollol import OllamaPool
from sollol.discovery import discover_ollama_nodes
from sollol.network_observer import log_ollama_error, log_ollama_request, log_ollama_response

logger = logging.getLogger(__name__)

if not getattr(logging.Logger, "_sollol_diag_installed", False):
    from sollol.network_observer import get_observer

    def _diag_log_observer(label: str):
        obs = get_observer()
        logging.getLogger("flockparser").warning(
            "[diag:%s] redis_client=%s sampling=%s sample_rate=%.2f batch=%d queue=%d",
            label,
            bool(obs.redis_client),
            obs.enable_sampling,
            obs.sample_rate,
            len(getattr(obs, "dashboard_batch", [])),
            obs.event_queue.qsize(),
        )

    logging.Logger._sollol_diag_installed = True
else:
    def _diag_log_observer(label: str):
        pass

# Thread-local storage for parallelism context
_thread_local = threading.local()


def _try_import_numpy():
    """Import numpy lazily (optional dependency)."""
    try:
        import numpy as np  # type: ignore

        return np
    except Exception:
        return None


_NUMPY = _try_import_numpy()


def _percentile(values: List[float], pct: float) -> float:
    """Compute percentile without requiring numpy."""
    if not values:
        return 0.0

    if _NUMPY is not None:
        try:
            return float(_NUMPY.percentile(values, pct))
        except Exception:
            pass

    sorted_values = sorted(values)
    k = (len(sorted_values) - 1) * (pct / 100.0)
    lower = int(k)
    upper = min(lower + 1, len(sorted_values) - 1)
    if lower == upper:
        return float(sorted_values[lower])

    fraction = k - lower
    return float(sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction)


def _create_redis_client() -> Optional["redis.Redis"]:
    """Create Redis client using SOLLOL environment defaults."""
    try:
        import redis  # type: ignore
    except Exception:
        logger.warning("Redis client not available - SOLLOL observability disabled")
        return None

    redis_url = os.getenv("SOLLOL_REDIS_URL")

    try:
        if redis_url:
            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return client

        host = os.getenv("SOLLOL_REDIS_HOST", "localhost")
        port = int(os.getenv("SOLLOL_REDIS_PORT", "6379"))
        client = redis.Redis(host=host, port=port, decode_responses=True, socket_timeout=2)
        client.ping()
        return client
    except Exception as exc:
        logger.warning("Unable to connect to Redis for observability: %s", exc)
        return None


def _format_node_stats(pool: OllamaPool, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert SOLLOL node stats into dashboard-friendly structure."""
    node_perf = stats.get("node_performance", {})
    formatted = []

    for node in stats.get("nodes", []):
        perf = node_perf.get(node, {})
        formatted.append(
            {
                "url": node if node.startswith("http") else f"http://{node}",
                "available": perf.get("available", True),
                "latency_ms": perf.get("latency_ms", 0.0),
                "success_rate": perf.get("success_rate", 1.0),
                "total_requests": perf.get("total_requests", 0),
                "failed_requests": perf.get("failed_requests", 0),
                "gpu_free_mem": perf.get("gpu_free_mem", 0),
                "active_requests": perf.get("active_requests", 0),
                "priority": perf.get("priority", 0),
            }
        )

    if not formatted and pool.nodes:
        for node_dict in pool.nodes:
            url = f"{node_dict['host']}:{node_dict['port']}"
            perf = node_perf.get(url, {})
            formatted.append(
                {
                    "url": f"http://{url}",
                    "available": perf.get("available", True),
                    "latency_ms": perf.get("latency_ms", 0.0),
                    "success_rate": perf.get("success_rate", 1.0),
                    "total_requests": perf.get("total_requests", 0),
                    "failed_requests": perf.get("failed_requests", 0),
                    "gpu_free_mem": perf.get("gpu_free_mem", 0),
                    "active_requests": perf.get("active_requests", 0),
                    "priority": perf.get("priority", 0),
                }
            )

    return formatted


def _normalize_operation_name(operation: str) -> str:
    """Normalize Ollama operation names for observability."""
    op = operation.lower()
    if op in {"generate", "chat"}:
        return "chat"
    if op in {"embeddings", "embed"}:
        return "embed"
    if op.endswith("_batch"):
        return op
    return op


def _make_request_with_metadata(
    self, endpoint: str, data: Dict[str, Any], priority: int = 5, timeout: float = 300.0
) -> Any:
    """
    Override OllamaPool request handling to track last model/operation metadata.
    """
    cache_key = None
    if self.cache.enabled and not data.get("stream", False):
        cache_key = self.cache.get_cache_key(endpoint, data)
        cached_response = self.cache.get(cache_key)
        if cached_response is not None:
            logger.debug(f"Cache hit for {endpoint} (key={cache_key[:16]}...)")
            return cached_response

    with self._lock:
        self.stats["total_requests"] += 1

    errors = []
    routing_decision = None
    operation = _normalize_operation_name(endpoint.split("/")[-1])

    for attempt in range(len(self.nodes)):
        _diag_log_observer("request")
        node, decision = self._select_node(payload=data, priority=priority)
        if decision:
            routing_decision = decision

        node_key = f"{node['host']}:{node['port']}"
        url = f"http://{node['host']}:{node['port']}{endpoint}"
        requested_model = data.get("model")
        existing_meta_map = getattr(self, "_flockparser_last_metadata", None)
        existing_meta = existing_meta_map.get(node_key, {}) if existing_meta_map else {}

        with self._lock:
            self.stats.setdefault("node_performance", {})
            perf = self.stats["node_performance"].setdefault(
                node_key,
                {
                    "total_requests": 0,
                    "failed_requests": 0,
                    "latency_ms": 0.0,
                    "success_rate": 1.0,
                    "available": True,
                    "active_requests": 0,
                },
            )
            perf["active_requests"] = perf.get("active_requests", 0) + 1

            if requested_model:
                perf["last_model"] = requested_model
            perf["last_operation"] = operation

            # Maintain compatibility metadata map (mirrors SynapticLlamas payloads)
            meta = getattr(self, "_flockparser_last_metadata", None)
            if meta is None:
                meta = {}
                self._flockparser_last_metadata = meta
            # Only update metadata if we have a real model (don't persist "unknown")
            tracked_model = requested_model or perf.get("last_model") or existing_meta.get("model")
            if tracked_model:  # Only write if we have a real model value
                meta[node_key] = {"model": tracked_model, "operation": operation}

        start_time = time.time()

        log_ollama_request(
            backend=node_key, model=tracked_model, operation=operation, priority=priority
        )

        try:
            logger.debug(f"Request to {url}")
            response = self.session.post(url, json=data, timeout=timeout)
            latency_ms = (time.time() - start_time) * 1000
            self._latency_buffer.append(latency_ms)

            vram_exhausted = self.health_monitor.detect_vram_exhaustion(node_key, latency_ms)
            if vram_exhausted:
                with self._lock:
                    if node_key in self.stats["node_performance"]:
                        self.stats["node_performance"][node_key]["vram_exhausted"] = True

            self.health_monitor.update_baseline(node_key, latency_ms)

            if response.status_code == 200:
                with self._lock:
                    self.stats["successful_requests"] += 1
                    self.stats["nodes_used"][node_key] = (
                        self.stats["nodes_used"].get(node_key, 0) + 1
                    )

                    self.stats.setdefault("node_performance", {})
                    perf = self.stats["node_performance"].setdefault(
                        node_key,
                        {
                            "total_requests": 0,
                            "failed_requests": 0,
                            "latency_ms": 0.0,
                            "success_rate": 1.0,
                            "available": True,
                            "active_requests": 0,
                        },
                    )
                    perf["total_requests"] += 1

                    if perf["total_requests"] == 1:
                        perf["latency_ms"] = latency_ms
                    else:
                        perf["latency_ms"] = (
                            perf["latency_ms"] * (perf["total_requests"] - 1) + latency_ms
                        ) / perf["total_requests"]

                    perf["success_rate"] = (
                        perf["total_requests"] - perf["failed_requests"]
                    ) / perf["total_requests"]
                    if requested_model:
                        perf["last_model"] = requested_model
                    # Only persist real model values (don't write "unknown")
                    last_model_value = perf.get("last_model") or existing_meta.get("model")
                    perf["last_operation"] = operation

                    meta = getattr(self, "_flockparser_last_metadata", None)
                    if meta is not None and last_model_value:  # Only write if we have a real model
                        meta[node_key] = {"model": last_model_value, "operation": operation}

                logger.info(
                    f"✅ Request succeeded: {node_key} "
                    f"(latency: {latency_ms:.1f}ms, "
                    f"avg: {self.stats['node_performance'][node_key]['latency_ms']:.1f}ms)"
                )

                log_ollama_response(
                    backend=node_key,
                    model=requested_model or perf.get("last_model", "unknown"),
                    latency_ms=latency_ms,
                    status_code=response.status_code,
                )

                if self.router and "model" in data:
                    task_type = (
                        routing_decision.get("task_type", "generation") if routing_decision else "generation"
                    )
                    self.router.record_performance(
                        task_type=task_type, model=data["model"], actual_duration_ms=latency_ms
                    )

                response_data = response.json()
                if cache_key is not None:
                    self.cache.set(cache_key, response_data)

                return response_data

            errors.append(f"{url}: HTTP {response.status_code}")
            self._record_failure(node_key, latency_ms)
            log_ollama_error(
                backend=node_key,
                model=requested_model or existing_meta.get("model", "unknown"),
                error=f"HTTP {response.status_code}",
                latency_ms=latency_ms,
            )

        except Exception as exc:
            latency_ms = (time.time() - start_time) * 1000
            errors.append(f"{url}: {exc}")
            logger.debug(f"Request failed: {exc}")
            self._record_failure(node_key, latency_ms)
            log_ollama_error(
                backend=node_key,
                model=requested_model or existing_meta.get("model", "unknown"),
                error=str(exc),
                latency_ms=latency_ms,
            )

        finally:
            with self._lock:
                if node_key in self.stats["node_performance"]:
                    perf = self.stats["node_performance"][node_key]
                    perf["active_requests"] = max(0, perf.get("active_requests", 1) - 1)

    with self._lock:
        self.stats["failed_requests"] += 1

    raise RuntimeError(f"All Ollama nodes failed. Errors: {'; '.join(errors)}")


def _embed_batch_sequential_with_metadata(
    self, model: str, inputs: List[str], node_key: str, priority: int = 5, **kwargs
) -> List[Dict[str, Any]]:
    """
    Wrap sequential batch embedding to record last model/operation metadata.
    """
    import ollama

    batch_size = len(inputs)
    if batch_size == 0:
        return []

    if ":" in node_key:
        host, port = node_key.rsplit(":", 1)
    else:
        logger.error(f"Invalid node_key format: {node_key}, expected 'host:port'")
        return [None] * batch_size

    node_url = f"http://{host}:{port}"
    logger.info(
        f"➡️  Sequential mode: Processing {batch_size} embeddings on {node_key} with connection reuse"
    )

    client = ollama.Client(host=node_url)

    results = []
    start_time = time.time()
    completed = 0
    errors = 0

    for i, text in enumerate(inputs):
        _diag_log_observer("embed")

        try:
            log_ollama_request(
                backend=node_key, model=model, operation="embed", priority=priority
            )

            embed_start = time.time()
            result = client.embed(model=model, input=text, **kwargs)
            embed_latency_ms = (time.time() - embed_start) * 1000

            results.append(result)
            completed += 1

            with self._lock:
                self.stats.setdefault("node_performance", {})
                perf = self.stats["node_performance"].setdefault(
                    node_key,
                    {
                        "total_requests": 0,
                        "failed_requests": 0,
                        "latency_ms": 0.0,
                        "success_rate": 1.0,
                        "available": True,
                        "active_requests": 0,
                    },
                )
                if model:
                    perf["last_model"] = model
                perf["last_operation"] = "embed"

                # Update metadata map with real model (model is always passed to this function)
                meta = getattr(self, "_flockparser_last_metadata", None)
                if meta is None:
                    meta = {}
                    self._flockparser_last_metadata = meta
                if model:  # Only persist if we have a real model
                    meta[node_key] = {"model": model, "operation": "embed"}

            log_ollama_response(
                backend=node_key,
                model=model,
                latency_ms=embed_latency_ms,
                status_code=200,
            )

            if (i + 1) % 50 == 0 or (i + 1) == batch_size:
                progress_pct = ((i + 1) * 100) // batch_size
                logger.info(f"   Progress: {i + 1}/{batch_size} embeddings ({progress_pct}%)")
        except Exception as exc:
            embed_latency_ms = (
                (time.time() - embed_start) * 1000 if "embed_start" in locals() else 0
            )
            logger.error(f"Error embedding text {i}: {exc}")

            log_ollama_error(
                backend=node_key, model=model, error=str(exc), latency_ms=embed_latency_ms
            )

            results.append(None)
            errors += 1

    total_time = time.time() - start_time
    with self._lock:
        self.stats["successful_requests"] += completed
        self.stats["failed_requests"] += errors
        self.stats["nodes_used"][node_key] = self.stats["nodes_used"].get(node_key, 0) + batch_size

        self.stats.setdefault("node_performance", {})
        perf = self.stats["node_performance"].setdefault(
            node_key,
            {
                "total_requests": 0,
                "failed_requests": 0,
                "latency_ms": 0.0,
                "success_rate": 1.0,
                "available": True,
                "active_requests": 0,
            },
        )
        perf["total_requests"] += batch_size
        perf["failed_requests"] += errors
        if model:
            perf["last_model"] = model
        perf["last_operation"] = "embed_batch"

        # Update metadata map with real model (model is always passed to this function)
        meta = getattr(self, "_flockparser_last_metadata", None)
        if meta is None:
            meta = {}
            self._flockparser_last_metadata = meta
        if model:  # Only persist if we have a real model
            meta[node_key] = {"model": model, "operation": "embed_batch"}

    avg_time_per_embedding = (total_time / batch_size * 1000) if batch_size > 0 else 0
    logger.info(
        f"✅ Sequential batch complete: {completed}/{batch_size} embeddings successful "
        f"in {total_time:.2f}s ({avg_time_per_embedding:.1f}ms/embedding) on {node_key}"
    )

    return results


def _make_streaming_request_with_metadata(
    self, endpoint: str, data: Dict[str, Any], priority: int = 5, timeout: float = 300.0, node: Optional[Dict[str, Any]] = None
):
    """
    Override OllamaPool streaming request handling to track last model/operation metadata.

    This is critical for FlockParser's chat operations which default to stream=True.
    Without this wrapper, all streaming requests use "unknown" as the model, causing
    the dashboard to discard events from the observability bridge.
    """
    from sollol.pool import OllamaPool as _BaseOllamaPool

    # Get the operation name
    operation = _normalize_operation_name(endpoint.split("/")[-1])

    # Select or use specified node
    if node is None:
        node, routing_decision = self._select_node(payload=data, priority=priority)
    else:
        routing_decision = None

    node_key = f"{node['host']}:{node['port']}"
    requested_model = data.get("model")
    existing_meta_map = getattr(self, "_flockparser_last_metadata", None)
    existing_meta = existing_meta_map.get(node_key, {}) if existing_meta_map else {}

    # Update node performance tracking with model metadata BEFORE the streaming request
    with self._lock:
        self.stats.setdefault("node_performance", {})
        perf = self.stats["node_performance"].setdefault(
            node_key,
            {
                "total_requests": 0,
                "failed_requests": 0,
                "latency_ms": 0.0,
                "success_rate": 1.0,
                "available": True,
                "active_requests": 0,
            },
        )

        # Record model if provided in request
        if requested_model:
            perf["last_model"] = requested_model
        perf["last_operation"] = operation

        # Update metadata map (mirrors SynapticLlamas payloads)
        meta = getattr(self, "_flockparser_last_metadata", None)
        if meta is None:
            meta = {}
            self._flockparser_last_metadata = meta

        # Only update metadata if we have a real model (don't persist "unknown")
        tracked_model = requested_model or perf.get("last_model") or existing_meta.get("model")
        if tracked_model:  # Only write if we have a real model value
            meta[node_key] = {"model": tracked_model, "operation": operation}

    # Call the original streaming request method
    # Use the unbound method from the base class
    original_method = _BaseOllamaPool._make_streaming_request
    _diag_log_observer("stream")
    for chunk in original_method(self, endpoint, data, priority, timeout, node):
        yield chunk

    # After streaming completes, ensure metadata is updated with final values
    with self._lock:
        perf = self.stats["node_performance"].get(node_key)
        if perf:
            # Only persist real model values (don't write "unknown")
            last_model_value = perf.get("last_model") or existing_meta.get("model")
            perf["last_operation"] = operation

            meta = getattr(self, "_flockparser_last_metadata", None)
            if meta is not None and last_model_value:  # Only write if we have a real model
                meta[node_key] = {"model": last_model_value, "operation": operation}


OllamaPool._make_request = _make_request_with_metadata
OllamaPool._make_streaming_request = _make_streaming_request_with_metadata
OllamaPool._embed_batch_sequential = _embed_batch_sequential_with_metadata


def _start_observability_bridge(pool: OllamaPool):
    """
    Bridge SOLLOL observability for FlockParser without altering routing logic.

    Mirrors SynapticLlamas payload structure so the unified dashboard receives
    the same latency percentiles, routing stats, and node updates.
    """
    # If SOLLOL already has an active Redis metrics client, rely on native publisher
    existing_thread = getattr(pool, "_flockparser_metrics_thread", None)
    if existing_thread:
        logger.debug(f"Observability bridge already running (thread={existing_thread})")
        return  # Already running

    redis_client = _create_redis_client()
    if not redis_client:
        logger.error("❌ FlockParser observability bridge: Redis connection failed, metrics will NOT be published to dashboard")
        return

    logger.info("✅ FlockParser observability bridge: Redis connected, starting metrics publisher")

    stop_event = threading.Event()
    # IMPORTANT: FlockParser MUST publish metrics even if SOLLOL has native publisher
    # because we need FlockParser-specific analytics format for the dashboard
    publish_metrics = True  # Always publish FlockParser metrics
    previous_node_totals: Dict[str, int] = {}
    previous_nodes_used: Dict[str, int] = {}

    def publish_loop():
        while not stop_event.is_set():
            try:
                stats = pool.get_stats()

                with pool._lock:  # noqa: SLF001 - internal synchronization
                    latencies = list(getattr(pool, "_latency_buffer", []))

                total_requests = stats.get("total_requests", 0)
                successful_requests = stats.get("successful_requests", 0)
                success_rate = (
                    successful_requests / total_requests if total_requests else 1.0
                )
                avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

                analytics = {
                    "p50_latency_ms": _percentile(latencies, 50),
                    "p95_latency_ms": _percentile(latencies, 95),
                    "p99_latency_ms": _percentile(latencies, 99),
                    "success_rate": success_rate,
                    "avg_duration_ms": avg_latency,
                    "total_requests": total_requests,
                    "successful_requests": successful_requests,
                }

                metrics_payload = {
                    "analytics": analytics,
                    "flockparser": {
                        "routing_strategy": stats.get("routing_strategy"),
                        "intelligent_routing": stats.get("intelligent_routing_enabled", False),
                        "nodes_configured": stats.get("nodes_configured", 0),
                        "http2_enabled": stats.get("http2_enabled", False),
                        "dask_enabled": stats.get("dask", {}).get("enabled", False),
                        "cache": stats.get("cache", {}),
                    },
                    "total_pools": len(pool.nodes),
                }

                app_name = os.getenv("SOLLOL_APP_NAME", "FlockParser")
                if publish_metrics:
                    payload = {
                        "source": "flockparser",
                        "metrics": metrics_payload,
                        "nodes": _format_node_stats(pool, stats),
                        "applications": [
                            {
                                "app_id": app_name,
                                "name": app_name,
                                "version": "unknown",
                                "last_heartbeat": time.time(),
                            }
                        ],
                        "timestamp": time.time(),
                    }

                    redis_client.setex("sollol:router:metadata", 30, json.dumps(payload))
                    logger.debug(
                        "Published SOLLOL observability metrics (requests=%s, nodes=%s)",
                        total_requests,
                        len(pool.nodes),
                    )

                # Publish synthetic Ollama activity deltas for dashboard feed
                node_performance = stats.get("node_performance", {})
                for node_key, perf in node_performance.items():
                    total = perf.get("total_requests", 0)
                    previous_total = previous_node_totals.get(node_key, 0)
                    delta = total - previous_total
                    if delta <= 0:
                        continue

                    latency_ms = perf.get("latency_ms", 0.0)
                    success_rate = perf.get("success_rate", 1.0)
                    metadata_map = getattr(pool, "_flockparser_last_metadata", {})
                    last_meta = metadata_map.get(node_key, {})
                    # Prioritize real model values (not "unknown")
                    model = perf.get("last_model") or last_meta.get("model")
                    operation_name = perf.get("last_operation") or last_meta.get("operation", "embed")

                    # Guard: Skip publishing if model or backend is missing/invalid
                    if not model or model == "unknown":
                        logger.debug(
                            "Skipping Ollama activity publish for %s: model is '%s' (no valid model tracked yet)",
                            node_key,
                            model or "None",
                        )
                        continue

                    if not node_key:
                        logger.debug("Skipping Ollama activity publish: backend is empty")
                        continue

                    logger.debug(
                        "FlockParser observability: node=%s model=%s operation=%s delta=%s",
                        node_key,
                        model,
                        operation_name,
                        delta,
                    )
                    message = {
                        "timestamp": time.time(),
                        "backend": node_key,
                        "event_type": "ollama_response",
                        "type": "ollama_response",
                        "severity": "info",
                        "details": {
                            "requests": delta,
                            "latency_ms": latency_ms,
                            "success_rate": success_rate,
                            "model": model,
                            "operation": operation_name,
                        },
                        "message": (
                            f"← RESPONSE from {node_key}: {model} [{operation_name}] "
                            f"({latency_ms:.0f}ms / {latency_ms/1000:.2f}s, {delta} request(s))"
                        ),
                    }
                    redis_client.publish("sollol:dashboard:ollama:activity", json.dumps(message))
                    previous_node_totals[node_key] = total

                # Publish synthetic routing decisions
                nodes_used = stats.get("nodes_used", {})
                for node_key, total in nodes_used.items():
                    previous = previous_nodes_used.get(node_key, 0)
                    delta = total - previous
                    if delta <= 0:
                        continue

                    perf = node_performance.get(node_key, {})
                    metadata_map = getattr(pool, "_flockparser_last_metadata", {})
                    last_meta = metadata_map.get(node_key, {})
                    # Prioritize real model values (not "unknown")
                    last_model = perf.get("last_model") or last_meta.get("model")
                    last_operation = perf.get("last_operation") or last_meta.get("operation", "embed")

                    # Guard: Skip publishing if model or backend is missing/invalid
                    if not last_model or last_model == "unknown":
                        logger.debug(
                            "Skipping routing event publish for %s: model is '%s' (no valid model tracked yet)",
                            node_key,
                            last_model or "None",
                        )
                        continue

                    if not node_key:
                        logger.debug("Skipping routing event publish: backend is empty")
                        continue

                    routing_event = {
                        "timestamp": time.time(),
                        "instance_id": "flockparser",
                        "event_type": "OLLAMA_NODE_SELECTED",
                        "model": last_model,
                        "backend": node_key,
                        "node_url": node_key,
                        "reason": f"Processed {delta} request(s) (ROUND_ROBIN)",
                        "priority": 0,
                        "message": f"[ROUND_ROBIN] {node_key} handled {delta} request(s)",
                        "type": "routing_event",
                    }
                    redis_client.publish("sollol:routing_events", json.dumps(routing_event))
                    previous_nodes_used[node_key] = total
            except Exception as exc:
                logger.debug("Observability bridge publish error: %s", exc)
            finally:
                stop_event.wait(5)

    thread = threading.Thread(
        target=publish_loop,
        daemon=True,
        name="FlockParserObservabilityPublisher",
    )
    thread.start()

    pool._flockparser_metrics_thread = thread
    pool._flockparser_metrics_stop_event = stop_event
    pool._flockparser_metrics_client = redis_client

    logger.info(f"✅ FlockParser observability bridge thread started (alive={thread.is_alive()}, will publish every 5s)")

    def _shutdown():
        stop = getattr(pool, "_flockparser_metrics_stop_event", None)
        thread_obj = getattr(pool, "_flockparser_metrics_thread", None)
        client = getattr(pool, "_flockparser_metrics_client", None)

        if stop:
            stop.set()
        if thread_obj and thread_obj.is_alive():
            thread_obj.join(timeout=2)
        if client:
            try:
                client.close()
            except Exception:
                pass

    atexit.register(_shutdown)


def add_flockparser_methods(pool: OllamaPool, kb_dir: Path):
    """
    Add FlockParser-specific methods to SOLLOL's OllamaPool instance.

    Args:
        pool: SOLLOL OllamaPool instance
        kb_dir: FlockParser's knowledge base directory (for saving nodes)
    """
    # Store KB_DIR for node persistence
    pool._kb_dir = kb_dir
    pool._nodes_file = kb_dir / "ollama_nodes.json"
    if not hasattr(pool, "_flockparser_last_metadata"):
        pool._flockparser_last_metadata = {}

    def _convert_nodes_to_urls(nodes):
        """Convert SOLLOL nodes to FlockParser URL format."""
        return [f"http://{node['host']}:{node['port']}" for node in nodes]

    def _convert_url_to_node(url):
        """Convert FlockParser URL to SOLLOL node dict."""
        url_clean = url.replace("http://", "").replace("https://", "")
        if ":" in url_clean:
            host, port = url_clean.split(":", 1)
        else:
            host, port = url_clean, "11434"
        return {"host": host, "port": int(port)}

    # Add 'instances' property (compatibility with FlockParser code)
    @property
    def instances(self):
        """Get nodes in FlockParser URL format."""
        return _convert_nodes_to_urls(self.nodes)

    pool.__class__.instances = instances

    # Save original SOLLOL embed_batch method before overriding
    _original_embed_batch = pool.embed_batch

    # Add discover_nodes method
    def discover_nodes(self, require_embedding_model=True, remove_stale=False):
        """
        Discover Ollama nodes on network (FlockParser-compatible).

        Args:
            require_embedding_model: Ignored (kept for compatibility)
            remove_stale: If True, remove nodes that are no longer found on network
        """
        logger.info("🔍 Re-scanning network for Ollama nodes...")
        discovered = discover_ollama_nodes(timeout=2.0)

        # Get discovered nodes (excluding localhost)
        discovered_keys = set()
        logger.info(f"📡 Found {len(discovered)} Ollama node(s) on network:")
        for node_dict in discovered:
            if node_dict['host'] not in ['localhost', '127.0.0.1']:
                node_key = f"{node_dict['host']}:{node_dict['port']}"
                discovered_keys.add(node_key)
                logger.info(f"   • http://{node_key}")
            else:
                logger.info(f"   • http://{node_dict['host']}:{node_dict['port']} (localhost - using real IP)")

        # Get currently configured nodes
        existing_keys = set(f"{n['host']}:{n['port']}" for n in self.nodes)

        # Find new nodes
        new_nodes = discovered_keys - existing_keys

        # Find stale nodes (configured but not found)
        stale_nodes = existing_keys - discovered_keys

        added_count = 0
        removed_count = 0

        # Add new nodes
        if new_nodes:
            logger.info(f"\n➕ Adding {len(new_nodes)} new node(s):")
            for node_key in new_nodes:
                host, port = node_key.split(":")
                self.add_node(host, int(port))
                added_count += 1
                logger.info(f"   ✅ Added: {node_key}")

        # Handle stale nodes
        if stale_nodes:
            if remove_stale:
                logger.info(f"\n➖ Removing {len(stale_nodes)} stale node(s):")
                for node_key in stale_nodes:
                    host, port = node_key.split(":")
                    self.remove_node(host, int(port))
                    removed_count += 1
                    logger.info(f"   🗑️  Removed: {node_key}")
            else:
                logger.warning(f"\n⚠️  Found {len(stale_nodes)} node(s) not detected on network:")
                for node_key in stale_nodes:
                    logger.warning(f"   • {node_key} (still configured, use 'remove_node' to remove)")

        # Summary
        logger.info(f"\n📊 Discovery Summary:")
        logger.info(f"   Discovered: {len(discovered_keys)} nodes")
        logger.info(f"   Added: {added_count} new nodes")
        if remove_stale:
            logger.info(f"   Removed: {removed_count} stale nodes")
        logger.info(f"   Total configured: {len(self.nodes)} nodes")

        if len(self.nodes) > 0:
            logger.info(f"\n🌐 Active Nodes:")
            for node in self.nodes:
                logger.info(f"   • http://{node['host']}:{node['port']}")
        else:
            logger.warning("⚠️  No nodes configured! SOLLOL cannot route requests.")

        self._save_nodes()
        return discovered

    pool.discover_nodes = discover_nodes.__get__(pool)

    # Add list_nodes method
    def list_nodes(self):
        """List all configured nodes (FlockParser-compatible)."""
        return self.instances

    pool.list_nodes = list_nodes.__get__(pool)

    # Add print_stats method
    def print_stats(self):
        """Print load balancer statistics (FlockParser-compatible)."""
        stats = self.get_stats()

        logger.info("\n" + "=" * 70)
        logger.info("📊 SOLLOL LOAD BALANCER STATISTICS")
        logger.info("=" * 70)
        logger.info(f"Total Requests: {stats.get('total_requests', 0)}")
        logger.info(f"Successful: {stats.get('successful_requests', 0)}")
        logger.info(f"Failed: {stats.get('failed_requests', 0)}")
        logger.info(f"Intelligent Routing: {'Enabled' if stats.get('intelligent_routing_enabled') else 'Disabled'}")
        logger.info(f"\nConfigured Nodes: {len(self.nodes)}")

        for i, node_url in enumerate(self.instances, 1):
            logger.info(f"  {i}. {node_url}")

        # Node performance metrics
        if "node_performance" in stats:
            logger.info("\n📈 Node Performance:")
            for node_key, perf in stats["node_performance"].items():
                logger.info(f"\n  {node_key}:")
                logger.info(f"    Requests: {perf.get('total_requests', 0)}")
                logger.info(f"    Success Rate: {perf.get('success_rate', 0) * 100:.1f}%")
                logger.info(f"    Avg Latency: {perf.get('latency_ms', 0):.1f}ms")

        logger.info("=" * 70)

    pool.print_stats = print_stats.__get__(pool)

    # Add embed_batch method - uses Legacy FlockParser's proven parallel approach
    def embed_batch(self, model, texts, max_workers=None, force_mode=None, use_adaptive=False, **kwargs):
        """
        Batch embedding using Legacy FlockParser's proven parallel approach.

        Uses ThreadPoolExecutor with multiple workers making individual embed()
        calls to SOLLOL, which naturally distributes load across nodes.

        This approach achieved 2.26x speedup with 3 CPU nodes in Legacy.

        Args:
            model: Embedding model name
            texts: List of texts to embed
            max_workers: Number of parallel workers (default: nodes * 2)
            force_mode: Ignored (kept for compatibility)
            use_adaptive: Ignored (kept for compatibility)
            **kwargs: Additional parameters (ignored)

        Returns:
            List of embedding results
        """
        import sys
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # Direct print to ensure visibility
        print(f"🔍 CUSTOM embed_batch() CALLED with {len(texts) if texts else 0} texts", file=sys.stderr, flush=True)

        if not texts:
            return []

        batch_size = len(texts)
        results = [None] * batch_size

        # Use Legacy's proven worker count: 2x number of nodes
        if max_workers is None:
            max_workers = len(self.nodes) * 2
            max_workers = max(2, min(max_workers, 8))  # Between 2-8 workers

        logger.info(f"🔀 Parallel embedding: {max_workers} workers across {len(self.nodes)} nodes")

        completed = 0

        def embed_single(index, text):
            """Embed single text using SOLLOL's routing."""
            try:
                # Call SOLLOL's single embed (it handles node selection)
                result = self.embed(model, text, priority=7)
                return index, result, None
            except Exception as e:
                return index, None, e

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(embed_single, i, text): i for i, text in enumerate(texts)}

            for future in as_completed(futures):
                index, result, error = future.result()
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

    # DISABLED: Use SOLLOL's built-in embed_batch with use_adaptive=False instead
    # pool.embed_batch = embed_batch.__get__(pool)

    # Add stub methods for legacy features
    def set_routing_strategy(self, strategy):
        """Set routing strategy (SOLLOL always uses intelligent routing)."""
        logger.info(f"ℹ️  SOLLOL uses intelligent routing by default ('{strategy}' ignored)")

    pool.set_routing_strategy = set_routing_strategy.__get__(pool)

    def verify_models_on_nodes(self):
        """Verify models on nodes (handled by SOLLOL)."""
        logger.info("ℹ️  Model verification handled by SOLLOL's intelligent routing")

    pool.verify_models_on_nodes = verify_models_on_nodes.__get__(pool)

    def force_gpu_all_nodes(self, model):
        """Force GPU for model (handled by SOLLOL routing)."""
        logger.info(f"ℹ️  SOLLOL's intelligent routing handles GPU allocation for {model}")

    pool.force_gpu_all_nodes = force_gpu_all_nodes.__get__(pool)

    # Save nodes helper
    def _save_nodes(self):
        """Save nodes to FlockParser's nodes file."""
        import json
        try:
            with open(self._nodes_file, 'w') as f:
                json.dump(self.instances, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save nodes: {e}")

    pool._save_nodes = _save_nodes.__get__(pool)

    # Override add_node to save
    original_add_node = pool.add_node
    def add_node_with_save(self, host, port=11434):
        original_add_node(host, port)
        pool._save_nodes()
        logger.info(f"✅ Added node: http://{host}:{port}")

    pool.add_node = add_node_with_save.__get__(pool)

    # Override remove_node to save
    original_remove_node = pool.remove_node
    def remove_node_with_save(self, host, port=11434):
        original_remove_node(host, port)
        pool._save_nodes()
        logger.info(f"✅ Removed node: http://{host}:{port}")

    pool.remove_node = remove_node_with_save.__get__(pool)

    # Add Legacy FlockParser's proven parallel embedding method
    # Store reference to pool for closure
    _pool_ref = pool

    def embed_batch_parallel(model, texts, max_workers=None):
        """
        Legacy FlockParser's proven parallel embedding approach.

        Uses ThreadPoolExecutor with individual embed() calls distributed
        across nodes via round-robin. This achieved 2.26x speedup with 3 CPU nodes.

        Args:
            model: Embedding model name
            texts: List of texts to embed
            max_workers: Number of parallel workers (default: nodes * 2)

        Returns:
            List of embedding results
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        if not texts:
            return []

        batch_size = len(texts)
        results = [None] * batch_size

        # Use Legacy's proven worker count: 2x number of nodes
        if max_workers is None:
            max_workers = len(_pool_ref.nodes) * 2
            max_workers = max(2, min(max_workers, 8))  # Between 2-8 workers

        logger.info(f"🔀 Legacy parallel: {max_workers} workers across {len(_pool_ref.nodes)} nodes")

        completed = 0

        def embed_single(index, text):
            """Embed single text using SOLLOL's routing."""
            try:
                # Call SOLLOL's single embed (it handles node selection)
                result = _pool_ref.embed(model, text, priority=7)
                return index, result, None
            except Exception as e:
                return index, None, e

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(embed_single, i, text): i for i, text in enumerate(texts)}

            for future in as_completed(futures):
                index, result, error = future.result()
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

    pool.embed_batch_parallel = embed_batch_parallel

    # Start observability bridge (keeps SOLLOL dashboard in sync without changing routing)
    _start_observability_bridge(pool)

    logger.debug("✅ FlockParser compatibility methods added to SOLLOL pool")

    return pool
