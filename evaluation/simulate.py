"""Time-stepped deceased-donor allocation simulation.

A fixed waitlist + a donor stream. For each donor (in arrival order), rank the
remaining waitlist under the given policy/ranker; the kidney goes to rank #1, who
leaves the waitlist. Deterministic given the inputs (no RNG in the sim). Produces a
transplant log + the not-transplanted remainder — the raw material for the equity
metrics.
"""
from __future__ import annotations


def _donor_seed(i: int) -> str:
    return "0x" + f"{i:064x}"  # deterministic 32-byte tie-break seed per donor


def simulate(waitlist: list[dict], donors: list[dict], rank_fn, policy: dict) -> dict:
    remaining = {r["id"]: r for r in waitlist}
    order = [r["id"] for r in waitlist]  # stable iteration
    transplants = []

    for i, donor in enumerate(donors):
        pool = [remaining[rid] for rid in order if rid in remaining]
        if not pool:
            break
        ranked, _ = rank_fn(donor, pool, policy, _donor_seed(i))
        if not ranked:
            continue  # no eligible recipient for this donor (e.g. ABO/crossmatch)
        r = remaining.pop(ranked[0]["id"])
        transplants.append({
            "donor_id": donor["id"], "recipient_id": r["id"],
            "abo": r["abo"], "cpra": r["cpra"], "age": r["age"],
            "prior_living_donor": r["prior_living_donor"],
            "waiting_days": max(0, donor["recovered_at_epoch_day"] - r["dialysis_start_epoch_day"]),
        })

    not_transplanted = [remaining[rid] for rid in order if rid in remaining]
    return {"transplants": transplants, "not_transplanted": not_transplanted, "waitlist_size": len(waitlist)}
