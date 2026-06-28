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

# A revealed record may only be one of these. An UNRECOGNIZED kind must fail
# verification (not be silently skipped), else a recipient can hide from the
# ranking under a bogus label (D-015 kind-mislabel).
KNOWN_KINDS = ("recipient", "donor")


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

    # 2. KNOWN KINDS: an unrecognized kind is a hard failure (D-015 kind-mislabel)
    #    — otherwise a recipient could hide from the ranking under a bogus label.
    unknown = [rid for rid, e in revealed.items() if e["kind"] not in KNOWN_KINDS]
    checks.append({"name": "all revealed kinds are recognized", "ok": not unknown})

    # 3. exactly ONE donor, matching the on-chain donor commitment (blocks
    #    relabelling a recipient as a second donor to hide it).
    donors = [e for e in revealed.values() if e["kind"] == "donor"]
    checks.append(
        {
            "name": "exactly one donor, matching on-chain",
            "ok": len(donors) == 1 and donors[0]["commitment"] == onchain["donorCommitment"],
        }
    )

    # 4. independent re-rank of the (now bound) revealed recipients
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

    # 5. COVERAGE: the ranking must cover EXACTLY the revealed recipients (every
    #    revealed recipient present, no extras) — closes kind-mislabel omission.
    checks.append(
        {
            "name": "ranked set == revealed recipient set (coverage)",
            "ok": {e["commitment"] for e in recips} == set(onchain["rankedRecipientCommitments"]),
        }
    )

    # 6. ranking hash
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
