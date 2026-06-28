"""Systems metrics — throughput + per-match latency of the off-chain engine.

ILLUSTRATIVE only (one machine, synthetic data, single-process Python). On-chain
gas/op is measured separately by contracts/scripts/gas.js.
"""
from __future__ import annotations

import time

from evaluation.policies import cas_policy, rank_cas
from evaluation.simulate import simulate


def measure(waitlist: list[dict], donors: list[dict]) -> dict:
    pol = cas_policy()

    t0 = time.perf_counter()
    res = simulate(waitlist, donors, rank_cas, pol)
    sim_s = time.perf_counter() - t0
    n = len(res["transplants"])

    # single-match latency: rank the full waitlist once for one donor (averaged).
    seed = "0x" + "00" * 32
    reps = 5
    t1 = time.perf_counter()
    for _ in range(reps):
        rank_cas(donors[0], waitlist, pol, seed)
    match_ms = (time.perf_counter() - t1) / reps * 1000

    return {
        "waitlist_size": len(waitlist),
        "donors": len(donors),
        "allocations": n,
        "sim_seconds": round(sim_s, 4),
        "throughput_allocs_per_s": round(n / sim_s, 1) if sim_s else None,
        "single_match_ms": round(match_ms, 2),
    }
