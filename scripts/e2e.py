"""End-to-end Phase 1 loop check: commit -> log -> recompute -> compare.

Drives the running API over HTTP (the same surface the browser uses), then
INDEPENDENTLY recomputes from the revealed records + salts using the published
deterministic engine (engine.verifier), and asserts it equals what was logged
on-chain. The revealed records are first BOUND to the on-chain Registered
commitments, so a substituted/fabricated pool is rejected (D-013).

Negative checks (otherwise "compare" would be vacuous):
  N1 — a tampered ranking hash must FAIL.
  N2 — a decision commitment that was NOT Registered on-chain must FAIL (binding).

Preconditions: Hardhat node running, AuditLedger deployed, API at API_URL.
Exit 0 = loop verified green; exit 1 = mismatch / error.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Make the repo root importable when run as `python scripts/e2e.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from engine.verifier import verify_decision

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")


def _fail(msg: str) -> None:
    print(f"  FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    print(f"e2e against {API_URL}")
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        seed = c.post("/seed").raise_for_status().json()
        print(f"  seeded donor + {len(seed['recipients'])} recipients")

        match = c.post("/match").raise_for_status().json()
        decision_id = match["decisionId"]
        print(f"  logged decision #{decision_id}: {match['rankedRecipientIds']}")

        decisions = c.get("/audit").raise_for_status().json()["decisions"]
        onchain = next((d for d in decisions if d["decisionId"] == decision_id), None)
        if onchain is None:
            _fail(f"decision #{decision_id} not found on-chain")

        revealed = c.get("/reveal").raise_for_status().json()
        rev = revealed["revealed"]
        # the on-chain Registered set the verifier binds against
        registered = c.get("/commitments").raise_for_status().json()["registered"]

    # ----- POSITIVE: independent recompute (binding -> re-rank -> hash) -----
    ok, checks = verify_decision(onchain, rev, registered)
    for ch in checks:
        print(f"    {'[OK]  ' if ch['ok'] else '[FAIL]'} {ch['name']}")
    if not ok:
        _fail("recompute does not match on-chain")
    print("  POSITIVE: recompute == on-chain  [OK]")

    # ----- N1: a tampered ranking hash must NOT verify -----
    tampered = {**onchain, "rankingHash": "0x" + "00" * 32}
    if verify_decision(tampered, rev, registered)[0]:
        _fail("tampered ranking hash still verified — compare is vacuous!")
    print("  NEGATIVE N1: tampered ranking hash rejected  [OK]")

    # ----- N2: a decision commitment NOT in the Registered set must NOT verify -----
    # Simulate the substitution attack: the verifier is given a Registered set that
    # is missing one of the decision's commitments (i.e. that record was never
    # committed on-chain). Binding must reject it.
    if not onchain["rankedRecipientCommitments"]:
        _fail("no ranked commitments to run the binding check")
    dropped = onchain["rankedRecipientCommitments"][0]
    registered_missing = [c for c in registered if c != dropped]
    if verify_decision(onchain, rev, registered_missing)[0]:
        _fail("unregistered commitment still verified — binding is vacuous!")
    print("  NEGATIVE N2: unregistered/substituted commitment rejected  [OK] (binding real)")

    print("PASS: commit -> log -> recompute -> compare is green end-to-end")


if __name__ == "__main__":
    main()
