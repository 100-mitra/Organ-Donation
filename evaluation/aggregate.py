"""Multi-seed aggregation: mean ± std per metric over many waitlist realizations,
so the headline numbers are not a single-seed artifact.

Same honest framing — "what the mechanism does" (relative trade-offs), not a proof of
fairness. The ± is the sample standard deviation ACROSS seeds (seed-to-seed spread);
the 95% CI of the mean is ~std/√n, i.e. roughly 5× tighter for n≈30.
"""
from __future__ import annotations

import statistics

from evaluation.metrics import compare
from evaluation.sensitivity import SWEEPS, sweep_one
from evaluation.waitlist import generate


def _stats(xs: list):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return {"mean": statistics.mean(xs), "std": statistics.stdev(xs) if len(xs) > 1 else 0.0, "n": len(xs)}


def aggregate_comparison(seeds, n_rec=400, n_don=150, long_w=25) -> dict:
    series: dict = {}  # policy -> metric -> [values across seeds]
    for s in seeds:
        w, d = generate(n_rec, n_don, seed=s)
        for pol, m in compare(w, d, long_w).items():
            pm = series.setdefault(pol, {})
            for k, v in m.items():
                pm.setdefault(k, []).append(v)
    return {pol: {k: _stats(vs) for k, vs in mk.items()} for pol, mk in series.items()}


def aggregate_sensitivity(seeds, n_rec=400, n_don=150) -> dict:
    coll = {label: {v: [] for v in values} for label, _a, values, _k in SWEEPS}
    for s in seeds:
        w, d = generate(n_rec, n_don, seed=s)
        for label, attr, values, key in SWEEPS:
            for v in values:
                coll[label][v].append(sweep_one(w, d, attr, v, key))
    return {
        label: {"attr": attr, "metric": key, "points": [(v, _stats(coll[label][v])) for v in values]}
        for label, attr, values, key in SWEEPS
    }


# ---- markdown renderers ----

ROWS_AGG = [
    ("transplants", "n_transplants", "int"),
    ("overall transplant rate", "rate_overall", "pct"),
    ("high-CPRA (≥80) access", "rate_high_cpra", "pct"),
    ("low-CPRA access", "rate_low_cpra", "pct"),
    ("blood-type-O access", "rate_O", "pct"),
    ("non-O access", "rate_nonO", "pct"),
    ("pediatric (<18) access", "rate_pediatric", "pct"),
    ("adult access", "rate_adult", "pct"),
    ("median waiting at transplant (days)", "waiting_median", "int"),
    ("mean age transplanted", "age_mean", "f1"),
    ("mean CPRA transplanted", "cpra_mean", "f1"),
]

DENOMS = [
    ("high-CPRA (≥80)", "n_high_cpra"), ("low-CPRA", "n_low_cpra"),
    ("blood-type-O", "n_O"), ("non-O", "n_nonO"),
    ("pediatric (<18)", "n_pediatric"), ("adult", "n_adult"),
]


def _fmt(st, kind):
    if st is None:
        return "—"
    m, s = st["mean"], st["std"]
    if kind == "pct":
        return f"{m * 100:.0f}% ± {s * 100:.0f}"
    if kind == "f1":
        return f"{m:.1f} ± {s:.1f}"
    return f"{m:.0f} ± {s:.0f}"


def comparison_md(agg) -> str:
    cols = list(agg)
    lines = ["| metric (mean ± std) | " + " | ".join(cols) + " |", "|" + "---|" * (len(cols) + 1)]
    for label, key, kind in ROWS_AGG:
        lines.append(f"| {label} | " + " | ".join(_fmt(agg[c][key], kind) for c in cols) + " |")
    return "\n".join(lines)


def denominators_md(agg, n_rec) -> str:
    pol = next(iter(agg))  # denominators are policy-independent (same waitlist)
    lines = [f"| subgroup | recipients (of {n_rec}) |", "|---|---|"]
    for label, key in DENOMS:
        st = agg[pol][key]
        lines.append(f"| {label} | {st['mean']:.0f} ± {st['std']:.0f} |")
    return "\n".join(lines)


def bullets(agg) -> list[str]:
    f, c = agg["FCFS"], agg["CAS"]
    lo = agg[next(k for k in agg if k.startswith("CAS+longevity"))]
    p = lambda st: f"{st['mean'] * 100:.0f}%"  # noqa: E731
    return [
        f"**High-CPRA (sensitized) access**: FCFS {p(f['rate_high_cpra'])} → CAS {p(c['rate_high_cpra'])} — "
        f"CAS prioritizes hard-to-match patients (cost: low-CPRA {p(f['rate_low_cpra'])} → {p(c['rate_low_cpra'])}).",
        f"**Pediatric access**: FCFS {p(f['rate_pediatric'])} → CAS {p(c['rate_pediatric'])} → +longevity "
        f"{p(lo['rate_pediatric'])} (cost: adult {p(f['rate_adult'])} → {p(c['rate_adult'])}).",
        f"**Blood-type-O disadvantage**: under CAS O {p(c['rate_O'])} vs non-O {p(c['rate_nonO'])} — PERSISTS "
        f"(an ABO-compatibility effect, not fixed by scoring; FCFS O {p(f['rate_O'])} vs {p(f['rate_nonO'])}).",
        f"**Waiting time at transplant**: FCFS median {f['waiting_median']['mean']:.0f}d (pure queue) vs CAS "
        f"{c['waiting_median']['mean']:.0f}d.",
        f"**Longevity tension**: mean transplant age CAS {c['age_mean']['mean']:.0f} → +longevity "
        f"{lo['age_mean']['mean']:.0f} — maximizing life-years disadvantages older patients (so it is weight-0 by default).",
    ]
