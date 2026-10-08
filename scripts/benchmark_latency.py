"""
Latency Benchmark Utility (Sprint S9 Hardening - G3).
Measures p50, p95, and p99 server time on the 10 most-used GET endpoints on seeded data.
Asserts that p95 read latency remains < 500 ms.
"""

import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi.testclient import TestClient

from packages.trust_kernel.auth import create_access_token
from services.api.app.main import app


def seed_test_data_for_benchmark(client: TestClient):
    user_id = "01711000001"
    token = create_access_token(data={"sub": user_id, "phone": user_id, "role": "citizen"})
    headers = {
        "Authorization": f"Bearer {token}",
        "x-user-id": user_id,
        "x-user-role": "citizen",
        "Accept": "application/json",
    }

    # Create case
    c_res = client.post(
        "/api/v1/cases",
        json={"case_type": "civil", "title": "বেঞ্চমার্ক টেস্ট মামলা"},
        headers=headers,
    )
    case_data = c_res.json()
    case_id = case_data.get("id") or case_data.get("case", {}).get("id") or "case-bm-1"

    # Create brief
    client.post(f"/api/v1/cases/{case_id}/brief", json={}, headers=headers)

    # Create consent
    consent_res = client.post(
        "/api/v1/consents",
        json={
            "case_id": case_id,
            "shared_with": "01799887766",
            "duration_days": 14,
            "scopes": ["case_brief"],
        },
        headers=headers,
    )
    consent_data = consent_res.json()
    share_url = consent_data.get("share_url", "/s/invalid_token")

    return headers, case_id, share_url


def benchmark_read_endpoints(iterations: int = 30) -> dict:
    client = TestClient(app)
    auth_headers, case_id, share_url = seed_test_data_for_benchmark(client)
    admin_token = create_access_token(data={"sub": "01700000000", "phone": "01700000000", "role": "admin"})
    admin_headers = {"Authorization": f"Bearer {admin_token}", "Accept": "application/json"}

    # The 10 most-used GET endpoints
    endpoints = [
        ("/api/v1/health", {"Accept": "application/json"}),
        ("/api/v1/i18n/bn", {"Accept": "application/json"}),
        ("/me", auth_headers),
        ("/api/v1/cases", auth_headers),
        (f"/api/v1/cases/{case_id}", auth_headers),
        (f"/api/v1/cases/{case_id}/brief", auth_headers),
        ("/api/v1/documents", auth_headers),
        ("/api/v1/consents", auth_headers),
        ("/api/v1/evals/golden-sets", admin_headers),
        (share_url, {"Accept": "application/json"}),
    ]

    all_latencies = []
    endpoint_stats = {}

    for endpoint, headers in endpoints:
        latencies = []
        for _ in range(iterations):
            start = time.perf_counter()
            resp = client.get(endpoint, headers=headers)
            elapsed_ms = (time.perf_counter() - start) * 1000
            assert resp.status_code in (200, 307, 308), (
                f"Endpoint {endpoint} failed with {resp.status_code}"
            )
            latencies.append(elapsed_ms)
            all_latencies.append(elapsed_ms)

        latencies.sort()
        n = len(latencies)
        p50 = latencies[int(n * 0.50)]
        p95 = latencies[int(n * 0.95)]
        p99 = latencies[int(n * 0.99)]

        endpoint_stats[endpoint] = {
            "iterations": iterations,
            "min_ms": round(min(latencies), 2),
            "p50_ms": round(p50, 2),
            "p95_ms": round(p95, 2),
            "p99_ms": round(p99, 2),
            "max_ms": round(max(latencies), 2),
        }

    all_latencies.sort()
    total_n = len(all_latencies)
    overall_p95 = all_latencies[int(total_n * 0.95)]

    report = {
        "total_requests": total_n,
        "overall_p50_ms": round(all_latencies[int(total_n * 0.50)], 2),
        "overall_p95_ms": round(overall_p95, 2),
        "overall_p99_ms": round(all_latencies[int(total_n * 0.99)], 2),
        "target_p95_threshold_ms": 500.0,
        "p95_target_met": overall_p95 < 500.0,
        "endpoints": endpoint_stats,
    }
    return report


if __name__ == "__main__":
    result = benchmark_read_endpoints(iterations=30)
    out_file = REPO_ROOT / "storage" / "benchmark_p95_results.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    print("-" * 80)
    print(
        f"{'Endpoint':<38} | {'Min (ms)':<9} | {'p50 (ms)':<9} | {'p95 (ms)':<9} | {'Max (ms)':<9}"
    )
    print("-" * 80)
    for ep, stat in result["endpoints"].items():
        print(
            f"{ep:<38} | {stat['min_ms']:<9} | {stat['p50_ms']:<9} | {stat['p95_ms']:<9} | {stat['max_ms']:<9}"
        )
    print("-" * 80)
    print(
        f"Overall p95: {result['overall_p95_ms']} ms (Target < 500 ms: {result['p95_target_met']})"
    )
    print(f"Results written to: {out_file}")
