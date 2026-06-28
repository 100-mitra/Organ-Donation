"""Allocation-policy variants compared in the evaluation.

  - CAS              : kidney_v1 as shipped (longevity weight 0).
  - CAS + longevity  : kidney_v1 with the longevity_epts weight turned on.
  - FCFS             : SAME hard gates, but ranked purely by waiting time (the
                       first-come-first-served queue baseline — no weighted score).
  - with_weights     : kidney_v1 with arbitrary weight overrides (sensitivity sweep).

Every `rank_*` returns (ranked_eligible, evaluated) so the simulator treats them
interchangeably; ranked[0] is the recipient the kidney goes to.
"""
from __future__ import annotations

import copy

from engine.compatibility import eligibility
from engine.policy import load_policy
from engine.scoring import rank as cas_rank


def cas_policy() -> dict:
    return load_policy("kidney_v1")


def longevity_policy(weight: int = 25) -> dict:
    p = copy.deepcopy(load_policy("kidney_v1"))
    p["attributes"]["longevity_epts"]["weight"] = weight
    return p


def with_weights(**overrides: int) -> dict:
    p = copy.deepcopy(load_policy("kidney_v1"))
    for attr, w in overrides.items():
        p["attributes"][attr]["weight"] = w
    return p


def rank_cas(donor, recipients, policy, seed):
    return cas_rank(donor, recipients, policy, seed)


def rank_fcfs(donor, recipients, policy, seed):
    """First-come-first-served: gates, then longest waiting time first."""
    evaluated = []
    for r in recipients:
        ok, _gates = eligibility(donor, r, policy)
        if ok:
            wd = max(0, donor["recovered_at_epoch_day"] - r["dialysis_start_epoch_day"])
            evaluated.append({"id": r["id"], "eligible": True, "waiting_days": wd})
    ranked = sorted(evaluated, key=lambda e: (-e["waiting_days"], e["id"]))
    return ranked, evaluated
