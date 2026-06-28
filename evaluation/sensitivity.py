"""Sensitivity analysis: sweep a key CAS weight and watch a subgroup metric move.

Shows the policy is a tunable dial, not a fixed verdict — e.g. raising the CPRA
weight monotonically raises sensitized-patient access. Deterministic given the
waitlist + stream.
"""
from __future__ import annotations

from evaluation.metrics import summarize
from evaluation.policies import rank_cas, with_weights
from evaluation.simulate import simulate

# (label, attribute, weight values, metric key)
SWEEPS = [
    ("high-CPRA access vs CPRA weight", "sensitization_cpra", list(range(0, 41, 5)), "rate_high_cpra"),
    ("pediatric access vs pediatric weight", "pediatric", list(range(0, 31, 5)), "rate_pediatric"),
    ("median waiting (days) vs waiting-time weight", "waiting_time", list(range(0, 61, 10)), "waiting_median"),
    ("mean transplant age vs longevity weight", "longevity_epts", list(range(0, 41, 5)), "age_mean"),
]


def sweep_one(waitlist: list[dict], donors: list[dict], attr: str, value: int, key: str):
    pol = with_weights(**{attr: value})
    return summarize(simulate(waitlist, donors, rank_cas, pol), waitlist)[key]


def run_sweeps(waitlist: list[dict], donors: list[dict]) -> dict:
    out = {}
    for label, attr, values, key in SWEEPS:
        out[label] = {
            "attr": attr, "metric": key,
            "points": [(v, sweep_one(waitlist, donors, attr, v, key)) for v in values],
        }
    return out
