"""Tests for the sensitivity sweep + systems metrics."""
from __future__ import annotations

from evaluation.sensitivity import run_sweeps, sweep_one
from evaluation.systems import measure
from evaluation.waitlist import generate


def test_cpra_weight_increases_sensitized_access():
    w, d = generate(300, 100, seed=7)
    lo = sweep_one(w, d, "sensitization_cpra", 0, "rate_high_cpra")
    hi = sweep_one(w, d, "sensitization_cpra", 40, "rate_high_cpra")
    assert hi >= lo  # more CPRA weight -> at least as much sensitized-patient access


def test_run_sweeps_shape():
    w, d = generate(150, 50, seed=8)
    s = run_sweeps(w, d)
    assert len(s) == 4
    for v in s.values():
        assert len(v["points"]) >= 2
        assert all(isinstance(p[0], int) for p in v["points"])


def test_systems_metrics_are_positive():
    w, d = generate(200, 60, seed=9)
    m = measure(w, d)
    assert m["throughput_allocs_per_s"] > 0
    assert m["single_match_ms"] > 0
    assert m["allocations"] <= 60
