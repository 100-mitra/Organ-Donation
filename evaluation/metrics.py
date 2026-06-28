"""Equity metrics over a simulation's transplant log + the comparison harness.

These describe WHAT THE MECHANISM DOES (the trade-offs each policy makes) — they are
NOT a proof of real-world fairness, which synthetic data cannot establish. The
defensible signal is *relative*: how CAS shifts subgroup access vs the FCFS baseline.
"""
from __future__ import annotations

import statistics

from evaluation.policies import cas_policy, longevity_policy, rank_cas, rank_fcfs
from evaluation.simulate import simulate


def _pct(xs: list, p: float):
    if not xs:
        return None
    s = sorted(xs)
    k = (len(s) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def _rate(waitlist: list[dict], tx_ids: set, pred) -> float | None:
    elig = [r for r in waitlist if pred(r)]
    if not elig:
        return None
    return sum(1 for r in elig if r["id"] in tx_ids) / len(elig)


def summarize(result: dict, waitlist: list[dict]) -> dict:
    tx = result["transplants"]
    tx_ids = {t["recipient_id"] for t in tx}
    waits = [t["waiting_days"] for t in tx]
    ages = [t["age"] for t in tx]
    cpras = [t["cpra"] for t in tx]
    return {
        "n_transplants": len(tx),
        "rate_overall": len(tx_ids) / len(waitlist),
        "rate_high_cpra": _rate(waitlist, tx_ids, lambda r: r["cpra"] >= 80),
        "rate_low_cpra": _rate(waitlist, tx_ids, lambda r: r["cpra"] < 80),
        "rate_O": _rate(waitlist, tx_ids, lambda r: r["abo"] == "O"),
        "rate_nonO": _rate(waitlist, tx_ids, lambda r: r["abo"] != "O"),
        "rate_pediatric": _rate(waitlist, tx_ids, lambda r: r["age"] < 18),
        "rate_adult": _rate(waitlist, tx_ids, lambda r: r["age"] >= 18),
        "waiting_median": statistics.median(waits) if waits else None,
        "waiting_p90": _pct(waits, 90),
        "age_mean": statistics.mean(ages) if ages else None,
        "cpra_mean": statistics.mean(cpras) if cpras else None,
        # subgroup denominators (sizes in the waitlist) — what each % is "out of".
        "n_high_cpra": sum(1 for r in waitlist if r["cpra"] >= 80),
        "n_low_cpra": sum(1 for r in waitlist if r["cpra"] < 80),
        "n_O": sum(1 for r in waitlist if r["abo"] == "O"),
        "n_nonO": sum(1 for r in waitlist if r["abo"] != "O"),
        "n_pediatric": sum(1 for r in waitlist if r["age"] < 18),
        "n_adult": sum(1 for r in waitlist if r["age"] >= 18),
    }


def compare(waitlist: list[dict], donors: list[dict], longevity_weight: int = 25) -> dict:
    runs = {
        "FCFS": (rank_fcfs, cas_policy()),
        "CAS": (rank_cas, cas_policy()),
        f"CAS+longevity({longevity_weight})": (rank_cas, longevity_policy(longevity_weight)),
    }
    return {name: summarize(simulate(waitlist, donors, fn, pol), waitlist) for name, (fn, pol) in runs.items()}


ROWS = [
    ("transplants", "n_transplants", "{}"),
    ("overall transplant rate", "rate_overall", "{:.1%}"),
    ("high-CPRA (≥80) access", "rate_high_cpra", "{:.1%}"),
    ("low-CPRA access", "rate_low_cpra", "{:.1%}"),
    ("blood-type-O access", "rate_O", "{:.1%}"),
    ("non-O access", "rate_nonO", "{:.1%}"),
    ("pediatric (<18) access", "rate_pediatric", "{:.1%}"),
    ("adult access", "rate_adult", "{:.1%}"),
    ("median waiting at transplant (days)", "waiting_median", "{:.0f}"),
    ("p90 waiting at transplant (days)", "waiting_p90", "{:.0f}"),
    ("mean age transplanted", "age_mean", "{:.1f}"),
    ("mean CPRA transplanted", "cpra_mean", "{:.1f}"),
]


def to_markdown(comp: dict) -> str:
    cols = list(comp)
    lines = ["| metric | " + " | ".join(cols) + " |", "|" + "---|" * (len(cols) + 1)]
    for label, key, fmt in ROWS:
        cells = ["—" if comp[c][key] is None else fmt.format(comp[c][key]) for c in cols]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(lines)
