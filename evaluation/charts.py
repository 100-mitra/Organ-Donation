"""Matplotlib charts for the evaluation (headless Agg backend -> PNGs).

Consume the multi-seed AGGREGATES (mean ± std) so bars/curves carry error bars."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

SUBGROUPS = [
    ("high-CPRA", "rate_high_cpra"), ("low-CPRA", "rate_low_cpra"),
    ("O", "rate_O"), ("non-O", "rate_nonO"),
    ("pediatric", "rate_pediatric"), ("adult", "rate_adult"),
]


def equity_access(agg: dict, path) -> None:
    policies = list(agg)
    x = np.arange(len(SUBGROUPS))
    w = 0.8 / len(policies)
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    for i, p in enumerate(policies):
        means = [agg[p][k]["mean"] * 100 for _, k in SUBGROUPS]
        stds = [agg[p][k]["std"] * 100 for _, k in SUBGROUPS]
        ax.bar(x + i * w, means, w, yerr=stds, capsize=3, label=p)
    ax.set_xticks(x + w * (len(policies) - 1) / 2)
    ax.set_xticklabels([s for s, _ in SUBGROUPS])
    ax.set_ylabel("transplant access (%)")
    ax.set_title("Subgroup transplant access by policy (mean ± std over seeds)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def waiting_hist(cas_waits: list, fcfs_waits: list, path) -> None:
    hi = max([1, *cas_waits, *fcfs_waits])
    bins = np.linspace(0, hi, 25)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(fcfs_waits, bins, alpha=0.6, label="FCFS")
    ax.hist(cas_waits, bins, alpha=0.6, label="CAS")
    ax.set_xlabel("waiting days at transplant")
    ax.set_ylabel("# transplants (pooled across seeds)")
    ax.set_title("Waiting time at transplant: FCFS vs CAS")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def sensitivity_grid(sweeps: dict, path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for ax, (label, data) in zip(axes.flat, sweeps.items()):
        xs = [v for v, _ in data["points"]]
        ys = [st["mean"] for _, st in data["points"]]
        es = [st["std"] for _, st in data["points"]]
        ax.errorbar(xs, ys, yerr=es, marker="o", capsize=3)
        ax.set_title(label, fontsize=10)
        ax.set_xlabel(f"{data['attr']} weight")
        ax.grid(alpha=0.3)
    fig.suptitle("Sensitivity: sweeping key CAS weights (mean ± std over seeds)", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
