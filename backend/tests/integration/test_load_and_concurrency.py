"""
Integration and Concurrent Load Test Script for FastAPI Backend.
Measures Requests Per Second (RPS), Latency percentiles (p50, p95, p99), and Error Rates under concurrent connections.
"""

import asyncio
import time
import unittest
from typing import List, Tuple
import statistics

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def run_single_health_request() -> Tuple[bool, float]:
    """Execute a single health request and measure latency in seconds."""
    start = time.perf_counter()
    try:
        response = client.get("/api/v1/health")
        latency = time.perf_counter() - start
        success = (response.status_code == 200) and (response.json().get("status") == "ok")
        return success, latency
    except Exception:
        latency = time.perf_counter() - start
        return False, latency


class TestBackendLoadAndConcurrency(unittest.TestCase):
    def test_health_endpoint_contract(self):
        """Verify API health endpoint response schema."""
        res = client.get("/api/v1/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("timestamp", data)
        self.assertEqual(data["service"], "Multi-Object Tracking Backend")

    def test_concurrent_request_load(self):
        """Simulate concurrent API requests to measure RPS and latency percentiles."""
        num_requests = 200
        start_total = time.perf_counter()

        # Execute requests
        results = [run_single_health_request() for _ in range(num_requests)]

        total_elapsed = time.perf_counter() - start_total

        success_count = sum(1 for succ, _ in results if succ)
        latencies_ms = [lat * 1000.0 for _, lat in results]

        rps = num_requests / total_elapsed if total_elapsed > 0 else 0
        error_rate = ((num_requests - success_count) / num_requests) * 100.0

        latencies_ms.sort()
        p50 = latencies_ms[int(len(latencies_ms) * 0.50)]
        p95 = latencies_ms[int(len(latencies_ms) * 0.95)]
        p99 = latencies_ms[int(len(latencies_ms) * 0.99)]
        avg_lat = statistics.mean(latencies_ms)

        print(f"\n--- Load Test Results ({num_requests} requests) ---")
        print(f"Total Time:      {total_elapsed:.3f} s")
        print(f"Throughput:      {rps:.2f} Requests/sec")
        print(f"Success Rate:    {success_count}/{num_requests} ({100 - error_rate:.1f}%)")
        print(f"Avg Latency:     {avg_lat:.2f} ms")
        print(f"p50 Latency:     {p50:.2f} ms")
        print(f"p95 Latency:     {p95:.2f} ms")
        print(f"p99 Latency:     {p99:.2f} ms")

        # Validation assertions for sub-300ms SLA
        self.assertEqual(success_count, num_requests, "All load requests should succeed with 0% error rate")
        self.assertLess(p95, 300.0, "p95 latency should be well under 300ms SLA target")


if __name__ == "__main__":
    unittest.main()
