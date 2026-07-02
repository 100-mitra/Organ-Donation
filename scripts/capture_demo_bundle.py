"""Capture a REAL allocation as the static demo fixture (Phase 7, D-026).

Drives the running stack (Hardhat + API) through one honest seed -> match, then
serializes the exact payloads the browser Verify flow fetches — /audit, /reveal,
/commitments, /registrations, /policy — plus the /match response (for the
read-only Allocate view) into web/src/demo/bundle.json.

The bundle is genuine system output, not hand-authored: before writing, this
script re-verifies it with engine.verifier (the Python lockstep verifier) and
requires the positive check to PASS and a tampered variant to FAIL.

Preconditions: Hardhat node running, AuditLedger deployed, API at API_URL.
Exit 0 = bundle captured + self-verified; exit 1 = capture refused.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from engine.verifier import verify_decision

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8010")
OUT = Path(__file__).resolve().parents[1] / "web" / "src" / "demo" / "bundle.json"


def _fail(msg: str) -> None:
    print(f"  FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    print(f"capturing demo bundle from {API_URL}")
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        seed = c.post("/seed").raise_for_status().json()
        print(f"  seeded donor {seed['donor']['id']} + {len(seed['recipients'])} recipients")

        match = c.post("/match").raise_for_status().json()
        print(f"  logged decision #{match['decisionId']}: {match['rankedRecipientIds']}")

        audit = c.get("/audit").raise_for_status().json()
        reveal = c.get("/reveal").raise_for_status().json()
        commitments = c.get("/commitments").raise_for_status().json()
        registrations = c.get("/registrations").raise_for_status().json()
        policy = c.get("/policy").raise_for_status().json()

    latest = audit["decisions"][-1]
    if latest["decisionId"] != match["decisionId"]:
        _fail("latest on-chain decision is not the one just matched")

    # Self-check 1: the captured bundle must verify (same call the browser makes).
    ok, checks = verify_decision(
        latest, reveal["revealed"], commitments["registered"], policy,
        registrations["registrations"], registrations["erasures"],
    )
    for ch in checks:
        print(f"    {'[OK]  ' if ch['ok'] else '[FAIL]'} {ch['name']}")
    if not ok:
        _fail("captured bundle does not verify — refusing to write a broken fixture")

    # Self-check 2: a tampered variant (backdated dialysis start — the same edit
    # the browser tamper demo makes) must FAIL, or the demo would be vacuous.
    tampered = copy.deepcopy(reveal["revealed"])
    rid = next(k for k, v in tampered.items() if v["kind"] == "recipient")
    tampered[rid]["record"]["dialysis_start_epoch_day"] -= 2000
    if verify_decision(latest, tampered, commitments["registered"], policy,
                       registrations["registrations"], registrations["erasures"])[0]:
        _fail("tampered bundle still verifies — the demo would be vacuous")
    print("  self-check: honest PASSES, tampered FAILS  [OK]")

    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=False,
    ).stdout.strip() or "unknown"

    bundle = {
        "_meta": {
            "note": (
                "Pre-captured snapshot of one REAL allocation produced by the full local "
                "stack (Hardhat chain + API + CAS engine) on synthetic data. These are the "
                "verbatim responses of the live endpoints; a live deployment would read "
                "them from the chain/API instead. Captured by scripts/capture_demo_bundle.py."
            ),
            "captured_at_commit": commit,
            "policy_version": latest["policyVersion"],
            "decision_id": latest["decisionId"],
        },
        "audit": audit,
        "reveal": reveal,
        "commitments": commitments,
        "registrations": registrations,
        "policy": policy,
        "match": match,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(bundle, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"  wrote {OUT.relative_to(Path.cwd()) if OUT.is_relative_to(Path.cwd()) else OUT}")
    print("CAPTURE OK")


if __name__ == "__main__":
    main()
