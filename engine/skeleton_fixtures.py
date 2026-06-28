"""Hardcoded fixtures for the Phase 1 WALKING SKELETON only.

These are NOT the Phase 2 synthetic generator (`data_gen.py`, India distributions).
They exist solely to drive the thin end-to-end loop with a fixed, deterministic
candidate pool. Records are canon-v1 compatible (integer-only values).

The pool deliberately includes a waiting-time TIE (R2 and R4 both 1800) so the
deterministic tie-break is exercised by the trivial ranking.
"""
from __future__ import annotations

# One trivial donor. The Phase 1 ranking ignores donor compatibility entirely
# (ABO + crossmatch gates are Phase 2); the donor is still committed + logged so
# the audit trail is shaped like the real one.
DONOR = {"id": "D1", "abo": "O", "region": "TN"}

# Five recipients. The ONLY factor that matters to the trivial ranking is
# `waiting_days`. Everything else is flavour, carried into the commitment.
RECIPIENTS = [
    {"id": "R1", "abo": "O", "region": "TN", "waiting_days": 1200},
    {"id": "R2", "abo": "A", "region": "DL", "waiting_days": 1800},
    {"id": "R3", "abo": "O", "region": "KA", "waiting_days": 600},
    {"id": "R4", "abo": "B", "region": "TN", "waiting_days": 1800},
    {"id": "R5", "abo": "AB", "region": "MH", "waiting_days": 300},
]
