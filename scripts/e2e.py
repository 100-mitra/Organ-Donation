"""End-to-end Phase 1 loop check: commit -> log -> recompute -> compare.

Drives the running API over HTTP (the same surface the browser uses), then
INDEPENDENTLY recomputes the ranking from revealed records + salts using the
published deterministic engine, and asserts it equals what was logged on-chain.

Includes a NEGATIVE check: a tampered ranking must FAIL recompute — otherwise the
"compare" step would be vacuous.

Preconditions: a Hardhat node is running, AuditLedger is deployed
(deployments/localhost.json exists), and the API is serving at API_URL.

Exit 0 = loop verified green; exit 1 = mismatch / error.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Make the repo root importable when run as `python scripts/e2e.py`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from engine.commitments import commit
from engine.decision import ranking_hash
from engine.scoring import rank_recipients

API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")


def _fail(msg: str) -> None:
    print(f"  FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    print(f"e2e against {API_URL}")
    with httpx.Client(base_url=API_URL, timeout=30.0) as c:
        # 1. register (commit on-chain)
        seed = c.post("/seed").raise_for_status().json()
        print(f"  seeded donor + {len(seed['recipients'])} recipients")

        # 2. match (rank + log decision on-chain)
        match = c.post("/match").raise_for_status().json()
        decision_id = match["decisionId"]
        print(f"  logged decision #{decision_id}: {match['rankedRecipientIds']}")

        # 3. read the decision back from the chain (audit)
        decisions = c.get("/audit").raise_for_status().json()["decisions"]
        onchain = next((d for d in decisions if d["decisionId"] == decision_id), None)
        if onchain is None:
            _fail(f"decision #{decision_id} not found on-chain")

        # 4. fetch revealed records + salts (what an auditor recomputes from)
        revealed = c.get("/reveal").raise_for_status().json()
        rev = revealed["revealed"]
        policy = revealed["policyVersion"]

    # ----- INDEPENDENT RECOMPUTE (using the published deterministic engine) -----
    if onchain["policyVersion"] != policy:
        _fail(f"policy mismatch: on-chain {onchain['policyVersion']} vs {policy}")

    # 4a. every revealed record's commitment must match what it opens to
    for rid, entry in rev.items():
        recomputed = commit(entry["record"], entry["salt"])
        if recomputed != entry["commitment"]:
            _fail(f"{rid} commitment does not open: {recomputed} != {entry['commitment']}")

    # 4b. independently re-rank the revealed recipients and rebuild the ordered list
    recip_entries = [e for e in rev.values() if e["kind"] == "recipient"]
    ranked_records = rank_recipients([e["record"] for e in recip_entries])
    by_id = {e["record"]["id"]: e for e in recip_entries}
    recomputed_ranked = [by_id[r["id"]]["commitment"] for r in ranked_records]

    if recomputed_ranked != onchain["rankedRecipientCommitments"]:
        _fail("recomputed ranking != on-chain ranked commitments")

    # 4c. donor commitment + ranking hash
    donor_entry = next(e for e in rev.values() if e["kind"] == "donor")
    if donor_entry["commitment"] != onchain["donorCommitment"]:
        _fail("donor commitment mismatch")

    recomputed_hash = ranking_hash(
        onchain["donorCommitment"], recomputed_ranked, onchain["policyVersion"]
    )
    if recomputed_hash != onchain["rankingHash"]:
        _fail(f"ranking hash mismatch: {recomputed_hash} != {onchain['rankingHash']}")

    print("  POSITIVE: recompute == on-chain  [OK]")

    # ----- NEGATIVE CHECK: a tampered ranking must NOT verify -----
    if len(recomputed_ranked) < 2:
        _fail("need >=2 recipients to run the tamper check")
    tampered = list(recomputed_ranked)
    tampered[0], tampered[1] = tampered[1], tampered[0]  # swap top two
    tampered_hash = ranking_hash(
        onchain["donorCommitment"], tampered, onchain["policyVersion"]
    )
    if tampered_hash == onchain["rankingHash"]:
        _fail("tampered ranking produced the SAME hash — compare is vacuous!")
    print("  NEGATIVE: tampered ranking != on-chain hash  [OK] (compare is real)")

    print("PASS: commit -> log -> recompute -> compare is green end-to-end")


if __name__ == "__main__":
    main()
