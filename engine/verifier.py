"""Auditor-side recompute-and-compare (pure, deterministic — no HTTP, no chain).

Given an on-chain decision, the revealed records+salts, and the on-chain set of
Registered commitments, independently confirm the logged allocation faithfully
executed the published policy (CLAUDE.md §8, §10).

The order matters and is part of the spec: BIND the revealed records to the
on-chain registrations FIRST (each revealed record must open to a commitment that
was actually Registered on the ledger), THEN re-rank. Without the binding the
verifier would recompute from whatever set the server chose to reveal, which is
the vacuous-pass defect closed here (D-013).

Used live by scripts/e2e.py; unit-tested in api/tests/test_verifier.py. The
JavaScript twin is web/src/verify.js — both must stay in lock-step.
"""
from __future__ import annotations

from engine.commitments import commit
from engine.decision import ranking_hash
from engine.scoring import rank_recipients


def verify_decision(
    onchain: dict,
    revealed: dict,
    registered_commitments: list[str],
) -> tuple[bool, list[dict]]:
    """Return (all_ok, checks). `registered_commitments` is the on-chain set from
    the AuditLedger `Registered` events."""
    registered = set(registered_commitments)
    checks: list[dict] = []

    # 1. BINDING (before re-ranking): each revealed record must (a) open to its
    #    stored commitment and (b) that commitment must have been Registered
    #    on-chain. A fabricated/substituted record fails (b).
    for rid, e in revealed.items():
        opens = commit(e["record"], e["salt"]) == e["commitment"]
        is_registered = e["commitment"] in registered
        checks.append(
            {
                "name": f"revealed {rid}: opens + registered on-chain",
                "ok": opens and is_registered,
            }
        )

    # 2. independent re-rank of the (now bound) revealed recipients
    recips = [e for e in revealed.values() if e["kind"] == "recipient"]
    ranked = rank_recipients([e["record"] for e in recips])
    by_id = {e["record"]["id"]: e for e in recips}
    recomputed = [by_id[r["id"]]["commitment"] for r in ranked]
    checks.append(
        {
            "name": "recomputed ranking == on-chain ranked commitments",
            "ok": recomputed == onchain["rankedRecipientCommitments"],
        }
    )

    # 3. donor commitment + ranking hash
    donor = next((e for e in revealed.values() if e["kind"] == "donor"), None)
    checks.append(
        {
            "name": "donor commitment == on-chain",
            "ok": donor is not None and donor["commitment"] == onchain["donorCommitment"],
        }
    )
    recomputed_hash = ranking_hash(
        onchain["donorCommitment"], recomputed, onchain["policyVersion"]
    )
    checks.append(
        {
            "name": "recomputed ranking hash == on-chain",
            "ok": recomputed_hash == onchain["rankingHash"],
        }
    )

    return all(c["ok"] for c in checks), checks
