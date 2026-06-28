"""Matplotlib charts for the evaluation (headless Agg backend -> PNGs)."""
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


def equity_access(comp: dict, path) -> None:
    policies = list(comp)
    x = np.arange(len(SUBGROUPS))
    w = 0.8 / len(policies)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for i, p in enumerate(policies):
        ax.bar(x + i * w, [comp[p][k] * 100 for _, k in SUBGROUPS], w, label=p)
    ax.set_xticks(x + w * (len(policies) - 1) / 2)
    ax.set_xticklabels([s for s, _ in SUBGROUPS])
    ax.set_ylabel("transplant access (%)")
    ax.set_title("Subgroup transplant access by policy (what the mechanism does)")
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
    ax.set_ylabel("# transplants")
    ax.set_title("Waiting time at transplant: FCFS vs CAS")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def sensitivity_grid(sweeps: dict, path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    for ax, (label, data) in zip(axes.flat, sweeps.items()):
        xs = [v for v, _ in data["points"]]
        ys = [m for _, m in data["points"]]
        ax.plot(xs, ys, marker="o")
        ax.set_title(label, fontsize=10)
        ax.set_xlabel(f"{data['attr']} weight")
        ax.grid(alpha=0.3)
    fig.suptitle("Sensitivity: sweeping key CAS weights", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
