"""Tests for multi-seed aggregation (mean ± std + denominators)."""
from __future__ import annotations

from evaluation.aggregate import (
    _stats, aggregate_comparison, aggregate_sensitivity, comparison_md, denominators_md,
)


def test_stats_mean_std_and_none():
    s = _stats([1.0, 2.0, 3.0])
    assert abs(s["mean"] - 2.0) < 1e-9 and s["n"] == 3 and s["std"] > 0
    assert _stats([None, None]) is None


def test_aggregate_comparison_has_stats_and_denominators():
    agg = aggregate_comparison(range(4), n_rec=120, n_don=40)
    assert set(agg) == {"FCFS", "CAS", "CAS+longevity(25)"}
    for pol in agg:
        assert agg[pol]["rate_high_cpra"]["n"] == 4  # aggregated over 4 seeds
        assert agg[pol]["n_pediatric"]["mean"] > 0   # subgroup denominator present
    assert "±" in comparison_md(agg) and "high-CPRA" in comparison_md(agg)
    assert "pediatric" in denominators_md(agg, 120)


def test_aggregate_sensitivity_aggregates_each_point():
    sw = aggregate_sensitivity(range(3), n_rec=120, n_don=40)
    assert len(sw) == 4
    for v in sw.values():
        assert all(st["n"] == 3 for _w, st in v["points"])
