"""Phase 1 TRIVIAL ranking — one factor only (waiting time).

This is the walking skeleton's stand-in for the real Composite Allocation Score.
It is intentionally trivial: rank by waiting time, longest first. The full
integer CAS (gates + weighted buckets) is Phase 2 and will replace `rank_recipients`
behind the same interface.

Determinism (sacred, CLAUDE.md §10): no floats, no wall-clock, no RNG. Ordering is
fully determined by (waiting_days desc, id asc).
"""
from __future__ import annotations

# The "policy" this trivial ranker implements. Deliberately NOT "kidney_v1":
# logging kidney_v1 would falsely claim the real CAS policy was applied. The
# contract logs THIS string so a verifier knows the trivial rule was used.
POLICY_VERSION = "skeleton-waiting-time-v0"


def rank_recipients(recipients: list[dict]) -> list[dict]:
    """Return recipients ordered by the trivial policy (highest priority first).

    Sort key: more waiting_days first; ties broken by ascending id (deterministic).
    """
    return sorted(recipients, key=lambda r: (-r["waiting_days"], r["id"]))


def ranked_ids(recipients: list[dict]) -> list[str]:
    """Convenience: just the ordered ids."""
    return [r["id"] for r in rank_recipients(recipients)]
