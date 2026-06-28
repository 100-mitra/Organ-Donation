"""Auditor-side recompute-and-compare (pure, deterministic — no HTTP, no chain).

Phase 3: the verifier independently confirms the decision considered EVERY active
registered recipient (no silent exclusion — D-015). It reconstructs the active
recipient set from the on-chain registration/erasure events (block-aware), checks
the decision's candidate pool equals that set and that the revealed recipients equal
the pool, then recomputes the full CAS ranking. It does not trust the contract's own
enforcement — it re-derives the active set from the raw event log.

The JavaScript twin is web/src/verify.js — both must stay byte-for-byte in lockstep.
"""
from __future__ import annotations

from engine.commitments import commit
from engine.decision import ranking_hash
from engine.scoring import rank

KNOWN_KINDS = ("recipient", "donor")
KIND_RECIPIENT = 1  # matches AuditLedger.KIND_RECIPIENT


def active_recipient_set(registrations: list[dict], erasures: list[dict], as_of_block: int) -> set:
    """Reconstruct the active recipient commitment set as of `as_of_block`."""
    active = set()
    for r in registrations:
        if r["kind"] == KIND_RECIPIENT and r["block"] <= as_of_block:
            active.add(r["commitment"])
    for e in erasures:
        if e["block"] <= as_of_block:
            active.discard(e["commitment"])
    return active


def verify_decision(
    onchain: dict,
    revealed: dict,
    registered_commitments: list[str],
    policy: dict | None = None,
    registrations: list[dict] | None = None,
    erasures: list[dict] | None = None,
) -> tuple[bool, list[dict]]:
    """Return (all_ok, checks).

    `policy` is REQUIRED to recompute — the caller fetches the versioned policy (as
    the browser does over /policy) and passes it, so both ports prove the SAME policy
    bytes were used. A None policy fails the recompute identically in Python and JS
    (no silent disk fallback — that would break lockstep, D-021)."""
    registered = set(registered_commitments)
    pool = onchain.get("candidatePool", [])
    checks: list[dict] = []

    # 1. BINDING: each revealed record opens + was Registered on-chain (D-013).
    for rid, e in revealed.items():
        opens = commit(e["record"], e["salt"]) == e["commitment"]
        checks.append({"name": f"revealed {rid}: opens + registered on-chain",
                       "ok": opens and e["commitment"] in registered})

    # 2. KNOWN KINDS + 3. exactly one donor (D-015).
    unknown = [rid for rid, e in revealed.items() if e["kind"] not in KNOWN_KINDS]
    checks.append({"name": "all revealed kinds are recognized", "ok": not unknown})
    donors = [e for e in revealed.values() if e["kind"] == "donor"]
    one_donor = len(donors) == 1 and donors[0]["commitment"] == onchain["donorCommitment"]
    checks.append({"name": "exactly one donor, matching on-chain", "ok": one_donor})

    # 4. POOL COMPLETENESS: the logged pool equals the active registered recipient
    #    set reconstructed from the event log (closes subset-drop, D-015).
    pool_complete = False
    if registrations is not None and erasures is not None:
        active = active_recipient_set(registrations, erasures, onchain["block"])
        pool_complete = set(pool) == active and len(pool) == len(set(pool))
    checks.append({"name": "candidate pool == active registered recipients (completeness, D-015)",
                   "ok": pool_complete})

    # 5. the revealed recipients are EXACTLY the candidate pool (nothing hidden/added).
    recips = [e for e in revealed.values() if e["kind"] == "recipient"]
    revealed_set = {e["commitment"] for e in recips}
    checks.append({"name": "revealed recipients == candidate pool", "ok": revealed_set == set(pool)})

    # 6. recompute the CAS ranking over the revealed pool and compare.
    recomputed: list[str] = []
    ranked_ok = coverage_ok = False
    if one_donor and policy is not None:  # matches web/src/verify.js (oneDonor && policy)
        try:
            by_id = {e["record"]["id"]: e for e in recips}
            ranked_eligible, _ = rank(
                donors[0]["record"], [e["record"] for e in recips], policy, onchain["donorCommitment"]
            )
            recomputed = [by_id[e["id"]]["commitment"] for e in ranked_eligible]
            ranked_ok = recomputed == onchain["rankedRecipientCommitments"]
            coverage_ok = {by_id[e["id"]]["commitment"] for e in ranked_eligible} == set(
                onchain["rankedRecipientCommitments"]
            )
        except Exception:
            ranked_ok = coverage_ok = False
    checks.append({"name": "recomputed CAS ranking == on-chain ranked commitments", "ok": ranked_ok})
    checks.append({"name": "ranked set == eligible revealed recipients (coverage)", "ok": coverage_ok})

    # 7. ranking hash (binds donor + policy + pool + ranking).
    recomputed_hash = ranking_hash(
        onchain["donorCommitment"], pool, recomputed, onchain["policyVersion"]
    )
    checks.append({"name": "recomputed ranking hash == on-chain", "ok": recomputed_hash == onchain["rankingHash"]})

    return all(c["ok"] for c in checks), checks
