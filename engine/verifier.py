"""Auditor-side recompute-and-compare (pure, deterministic — no HTTP, no chain).

Given an on-chain decision, the revealed records+salts, and the on-chain set of
Registered commitments, independently confirm the logged allocation faithfully
executed the published policy (CLAUDE.md §8, §10).

Phase 2: the recompute is the full Composite Allocation Score (gates + integer
scoring + deterministic tie-breaks), interpreting the versioned policy. Because the
gates EXCLUDE candidates, the ranked set is the set of ELIGIBLE recipients — the
coverage check is updated accordingly (every eligible recipient ranked; no extras).

The JavaScript twin is web/src/verify.js — both must stay byte-for-byte in lockstep
(frozen vectors in engine/tests/vectors/cas_ranking_vectors.json).
"""
from __future__ import annotations

from engine.commitments import commit
from engine.decision import ranking_hash
from engine.policy import load_policy
from engine.scoring import rank

# A revealed record may only be one of these (D-015 kind-mislabel).
KNOWN_KINDS = ("recipient", "donor")


def verify_decision(
    onchain: dict,
    revealed: dict,
    registered_commitments: list[str],
) -> tuple[bool, list[dict]]:
    """Return (all_ok, checks). `registered_commitments` is the on-chain Registered set."""
    registered = set(registered_commitments)
    checks: list[dict] = []

    # 1. BINDING (before re-ranking): each revealed record opens + was Registered.
    for rid, e in revealed.items():
        opens = commit(e["record"], e["salt"]) == e["commitment"]
        is_registered = e["commitment"] in registered
        checks.append(
            {"name": f"revealed {rid}: opens + registered on-chain", "ok": opens and is_registered}
        )

    # 2. KNOWN KINDS (D-015).
    unknown = [rid for rid, e in revealed.items() if e["kind"] not in KNOWN_KINDS]
    checks.append({"name": "all revealed kinds are recognized", "ok": not unknown})

    # 3. exactly ONE donor matching the on-chain donor commitment (D-015).
    donors = [e for e in revealed.values() if e["kind"] == "donor"]
    one_donor = len(donors) == 1 and donors[0]["commitment"] == onchain["donorCommitment"]
    checks.append({"name": "exactly one donor, matching on-chain", "ok": one_donor})

    # 4. recompute the CAS ranking (gates + integer scoring + tie-break) and compare.
    recips = [e for e in revealed.values() if e["kind"] == "recipient"]
    recomputed: list[str] = []
    ranked_ok = False
    coverage_ok = False
    if one_donor:
        try:
            policy = load_policy(onchain["policyVersion"])
            donor_record = donors[0]["record"]
            decision_seed = onchain["donorCommitment"]  # tie-break seed (on-chain)
            by_id = {e["record"]["id"]: e for e in recips}
            ranked_eligible, _ = rank(
                donor_record, [e["record"] for e in recips], policy, decision_seed
            )
            recomputed = [by_id[e["id"]]["commitment"] for e in ranked_eligible]
            ranked_ok = recomputed == onchain["rankedRecipientCommitments"]
            eligible_set = {by_id[e["id"]]["commitment"] for e in ranked_eligible}
            coverage_ok = eligible_set == set(onchain["rankedRecipientCommitments"])
        except Exception:
            ranked_ok = coverage_ok = False  # unknown policy / malformed -> fail, don't crash

    checks.append({"name": "recomputed CAS ranking == on-chain ranked commitments", "ok": ranked_ok})
    checks.append(
        {"name": "ranked set == eligible revealed recipients (coverage)", "ok": coverage_ok}
    )

    # 5. ranking hash.
    recomputed_hash = ranking_hash(
        onchain["donorCommitment"], recomputed, onchain["policyVersion"]
    )
    checks.append(
        {"name": "recomputed ranking hash == on-chain", "ok": recomputed_hash == onchain["rankingHash"]}
    )

    return all(c["ok"] for c in checks), checks
