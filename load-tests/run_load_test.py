"""
Controlled scalability experiment for MediConnect booking service.
Tests GET /slots/available at 10, 50, and 200 concurrent virtual users.

Usage (services must be running):
    python load-tests/run_load_test.py

Outputs:
    load-tests/results/raw_results.json
    load-tests/results/latency_vs_load.png
    load-tests/results/throughput_vs_load.png
"""
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

import httpx
import matplotlib.pyplot as plt

BOOKING_URL = "http://127.0.0.1:8000"
LOAD_LEVELS = [10, 50, 200]
REQUESTS_PER_USER = 5
RESULTS_DIR = Path(__file__).parent / "results"


async def login(client: httpx.AsyncClient) -> str:
    r = await client.post(
        f"{BOOKING_URL}/auth/login",
        json={"username": "dr.smith", "password": "clinician1"},
    )
    r.raise_for_status()
    return r.json()["access_token"]


async def single_request(client: httpx.AsyncClient, token: str) -> tuple[float, bool]:
    start = time.perf_counter()
    try:
        r = await client.get(
            f"{BOOKING_URL}/slots/available",
            headers={"Authorization": f"Bearer {token}"},
            params={"clinic_id": "CLINIC-SYD"},
            timeout=15.0,
        )
        ok = r.status_code == 200
    except httpx.HTTPError:
        ok = False
    elapsed_ms = (time.perf_counter() - start) * 1000
    return elapsed_ms, ok


async def user_worker(client: httpx.AsyncClient, token: str, count: int) -> tuple[list[float], int]:
    latencies = []
    errors = 0
    for _ in range(count):
        ms, ok = await single_request(client, token)
        latencies.append(ms)
        if not ok:
            errors += 1
    return latencies, errors


async def run_level(concurrency: int, token: str) -> dict:
    latencies = []
    errors = 0
    total_requests = concurrency * REQUESTS_PER_USER
    start_wall = time.perf_counter()

    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(limits=limits, timeout=15.0) as client:
        tasks = [user_worker(client, token, REQUESTS_PER_USER) for _ in range(concurrency)]
        results = await asyncio.gather(*tasks)
        for lats, errs in results:
            latencies.extend(lats)
            errors += errs

    duration = time.perf_counter() - start_wall
    latencies.sort()
    p95_idx = max(0, int(len(latencies) * 0.95) - 1)

    return {
        "concurrent_users": concurrency,
        "total_requests": total_requests,
        "duration_seconds": round(duration, 2),
        "throughput_rps": round(total_requests / duration, 2),
        "latency_mean_ms": round(statistics.mean(latencies), 2),
        "latency_p95_ms": round(latencies[p95_idx], 2),
        "error_rate_pct": round(100 * errors / total_requests, 2),
        "errors": errors,
    }


def generate_charts(results: list[dict]):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    users = [r["concurrent_users"] for r in results]
    mean_lat = [r["latency_mean_ms"] for r in results]
    p95_lat = [r["latency_p95_ms"] for r in results]
    throughput = [r["throughput_rps"] for r in results]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(users, mean_lat, "o-", label="Mean latency (ms)", color="#2563eb")
    ax.plot(users, p95_lat, "s-", label="95th percentile (ms)", color="#dc2626")
    ax.axhline(y=2000, color="gray", linestyle="--", label="2s target (95th pct)")
    ax.set_xlabel("Concurrent virtual users")
    ax.set_ylabel("Latency (ms)")
    ax.set_title("MediConnect Booking — Latency vs Load")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "latency_vs_load.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar([str(u) for u in users], throughput, color="#16a34a", alpha=0.8)
    ax.set_xlabel("Concurrent virtual users")
    ax.set_ylabel("Throughput (requests/sec)")
    ax.set_title("MediConnect Booking — Throughput vs Load")
    for bar, val in zip(bars, throughput):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                f"{val}", ha="center", fontsize=10)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(RESULTS_DIR / "throughput_vs_load.png", dpi=150)
    plt.close(fig)


async def main_async():
    print("MediConnect load test — ensure both services are running on 8000/8001", flush=True)
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            token = await login(client)
        except httpx.HTTPError:
            print("ERROR: Cannot reach booking-service. Start services first.", flush=True)
            sys.exit(1)

    results = []
    for level in LOAD_LEVELS:
        print(f"\nRunning load level: {level} concurrent users...", flush=True)
        result = await run_level(level, token)
        results.append(result)
        print(f"  Mean latency: {result['latency_mean_ms']} ms", flush=True)
        print(f"  P95 latency:  {result['latency_p95_ms']} ms", flush=True)
        print(f"  Throughput:   {result['throughput_rps']} req/s", flush=True)
        print(f"  Error rate:   {result['error_rate_pct']}%", flush=True)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_file = RESULTS_DIR / "raw_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)

    generate_charts(results)
    print(f"\nResults saved to {RESULTS_DIR}", flush=True)
    print("Charts: latency_vs_load.png, throughput_vs_load.png", flush=True)


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
