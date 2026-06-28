"""End-to-end Phase 3 loop check: commit -> log -> recompute -> compare.

Drives the running API over HTTP, then INDEPENDENTLY recomputes from the revealed
records using engine.verifier — binding to on-chain registrations (D-013) AND
reconstructing the active recipient set to confirm pool completeness (D-015).

Negative checks:
  N1 — a tampered ranking hash must FAIL.
  N2 — a decision commitment never Registered must FAIL (binding).
  N3 — the CONTRACT must reject an incomplete candidate pool (subset-drop blocked
       on-chain).

Preconditions: Hardhat node running, AuditLedger deployed, API at API_URL.
Exit 0 = loop verified green; exit 1 = mismatch / error.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from api.chain import Chain
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

        rev = c.get("/reveal").raise_for_status().json()["revealed"]
        registered = c.get("/commitments").raise_for_status().json()["registered"]
        reg = c.get("/registrations").raise_for_status().json()

    def verify(oc, rv=rev, cs=registered):
        return verify_decision(oc, rv, cs, None, reg["registrations"], reg["erasures"])

    # ----- POSITIVE -----
    ok, checks = verify(onchain)
    for ch in checks:
        print(f"    {'[OK]  ' if ch['ok'] else '[FAIL]'} {ch['name']}")
    if not ok:
        _fail("recompute does not match on-chain")
    print("  POSITIVE: recompute == on-chain  [OK]")

    # ----- N1: tampered ranking hash -----
    if verify({**onchain, "rankingHash": "0x" + "00" * 32})[0]:
        _fail("tampered ranking hash still verified — compare is vacuous!")
    print("  NEGATIVE N1: tampered ranking hash rejected  [OK]")

    # ----- N2: a commitment never Registered (binding) -----
    dropped = onchain["rankedRecipientCommitments"][0]
    if verify(onchain, cs=[c for c in registered if c != dropped])[0]:
        _fail("unregistered commitment still verified — binding is vacuous!")
    print("  NEGATIVE N2: unregistered/substituted commitment rejected  [OK] (binding real)")

    # ----- N3: the CONTRACT blocks an incomplete pool (subset-drop on-chain) -----
    chain = Chain()
    incomplete = onchain["candidatePool"][1:]  # drop one -> length != activeRecipientCount
    blocked = False
    try:
        chain.log_decision(
            onchain["donorCommitment"], incomplete, incomplete,
            onchain["rankingHash"], onchain["policyVersion"],
        )
    except Exception:
        blocked = True
    if not blocked:
        _fail("contract accepted an incomplete pool — subset-drop NOT blocked!")
    print("  NEGATIVE N3: contract rejected an incomplete pool  [OK] (subset-drop blocked on-chain, D-015)")

    print("PASS: commit -> log -> recompute -> compare is green end-to-end")


if __name__ == "__main__":
    main()
