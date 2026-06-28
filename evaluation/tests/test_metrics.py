"""Tests for the equity metrics."""
from __future__ import annotations

from evaluation.metrics import compare, summarize, to_markdown
from evaluation.waitlist import generate


def test_summarize_subgroup_rates():
    waitlist = [
        {"id": "a", "cpra": 90, "abo": "O", "age": 10},
        {"id": "b", "cpra": 0, "abo": "A", "age": 40},
        {"id": "c", "cpra": 85, "abo": "O", "age": 50},
        {"id": "d", "cpra": 0, "abo": "O", "age": 15},
    ]
    result = {
        "transplants": [
            {"recipient_id": "a", "waiting_days": 100, "age": 10, "cpra": 90},
            {"recipient_id": "b", "waiting_days": 200, "age": 40, "cpra": 0},
        ],
        "not_transplanted": [{"id": "c"}, {"id": "d"}],
        "waitlist_size": 4,
    }
    m = summarize(result, waitlist)
    assert m["n_transplants"] == 2
    assert m["rate_overall"] == 0.5
    assert m["rate_high_cpra"] == 0.5          # {a,c} eligible, a transplanted
    assert abs(m["rate_O"] - 1 / 3) < 1e-9      # {a,c,d}, a transplanted
    assert m["rate_pediatric"] == 0.5          # {a,d}, a transplanted
    assert m["waiting_median"] == 150


def test_compare_runs_three_policies_and_renders():
    w, d = generate(150, 50, seed=11)
    comp = compare(w, d)
    assert set(comp) == {"FCFS", "CAS", "CAS+longevity(25)"}
    md = to_markdown(comp)
    assert "high-CPRA" in md and "FCFS" in md and "CAS" in md
