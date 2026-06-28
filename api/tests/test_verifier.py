"""Chain-free unit tests for engine.verifier under Phase 3 (pool completeness)."""
from __future__ import annotations

from engine.commitments import commit
from engine.decision import ranking_hash
from engine.policy import load_policy
from engine.scoring import rank
from engine.verifier import active_recipient_set, verify_decision

P = load_policy()
VERSION = "kidney_v1"
SALT = "00" * 16

DONOR = {
    "id": "D1", "abo": "O", "hla": {"A": [1, 2], "B": [7, 8], "DR": [4, 15]},
    "age": 35, "region": "TN", "recovered_at_epoch_day": 20000,
}


def _recip(rid, **kw):
    base = {
        "id": rid, "abo": "O", "hla": {"A": [1, 2], "B": [7, 8], "DR": [4, 15]}, "age": 45,
        "unacceptable_antigens": [], "cpra": 0, "dialysis_start_epoch_day": 16000,
        "prior_living_donor": False, "region": "TN", "urgent": False,
    }
    base.update(kw)
    return base


# R1..R3 eligible, R4 gated (crossmatch on B7), R5 gated (sanity age).
RECIPS = [
    _recip("R1", cpra=10, dialysis_start_epoch_day=13000),
    _recip("R2", abo="A", age=12, dialysis_start_epoch_day=18500),
    _recip("R3", abo="B", cpra=98, prior_living_donor=True, dialysis_start_epoch_day=17000),
    _recip("R4", unacceptable_antigens=[7]),
    _recip("R5", age=95),
]


def _build():
    donor_entry = {"record": DONOR, "salt": SALT, "commitment": commit(DONOR, SALT), "kind": "donor"}
    revealed = {"D1": donor_entry}
    by_id = {}
    for r in RECIPS:
        c = commit(r, SALT)
        revealed[r["id"]] = {"record": r, "salt": SALT, "commitment": c, "kind": "recipient"}
        by_id[r["id"]] = revealed[r["id"]]
    pool = sorted([by_id[r["id"]]["commitment"] for r in RECIPS], key=lambda c: int(c, 16))
    seed = donor_entry["commitment"]
    ranked_eligible, _ = rank(DONOR, RECIPS, P, seed)
    ranked = [by_id[e["id"]]["commitment"] for e in ranked_eligible]
    onchain = {
        "donorCommitment": donor_entry["commitment"], "policyVersion": VERSION,
        "candidatePool": pool, "rankedRecipientCommitments": ranked,
        "rankingHash": ranking_hash(donor_entry["commitment"], pool, ranked, VERSION),
        "block": 10,
    }
    registrations = [{"commitment": by_id[r["id"]]["commitment"], "kind": 1, "block": i + 1}
                     for i, r in enumerate(RECIPS)]
    registrations.append({"commitment": donor_entry["commitment"], "kind": 2, "block": 6})
    registered = [e["commitment"] for e in revealed.values()]
    return onchain, revealed, registered, registrations, []


def test_active_recipient_set_is_block_aware():
    regs = [{"commitment": "0xaa", "kind": 1, "block": 1},
            {"commitment": "0xbb", "kind": 1, "block": 2},
            {"commitment": "0xdd", "kind": 2, "block": 3}]  # donor (kind 2) excluded
    eras = [{"commitment": "0xaa", "block": 5}]
    assert active_recipient_set(regs, eras, 1) == {"0xaa"}
    assert active_recipient_set(regs, eras, 4) == {"0xaa", "0xbb"}
    assert active_recipient_set(regs, eras, 5) == {"0xbb"}  # 0xaa erased


def test_accepts_a_faithful_phase3_decision():
    onchain, revealed, registered, regs, eras = _build()
    ok, checks = verify_decision(onchain, revealed, registered, P, regs, eras)
    assert ok, [c["name"] for c in checks if not c["ok"]]


def test_gated_recipients_excluded_from_ranking():
    onchain, *_ = _build()
    # ranked has only the 3 eligible; pool has all 5
    assert len(onchain["rankedRecipientCommitments"]) == 3
    assert len(onchain["candidatePool"]) == 5


def test_subset_drop_rejected_drop_a_registered_recipient_everywhere():
    # THE D-015 attack: a registered recipient (R1) is dropped from the pool, the
    # ranking, AND /reveal — but it is still in the on-chain registration log, so the
    # reconstructed active set != pool. Completeness must catch it.
    onchain, revealed, registered, regs, eras = _build()
    r1c = revealed["R1"]["commitment"]
    del revealed["R1"]
    onchain["candidatePool"] = [c for c in onchain["candidatePool"] if c != r1c]
    onchain["rankedRecipientCommitments"] = [c for c in onchain["rankedRecipientCommitments"] if c != r1c]
    onchain["rankingHash"] = ranking_hash(
        onchain["donorCommitment"], onchain["candidatePool"], onchain["rankedRecipientCommitments"], VERSION
    )
    ok, checks = verify_decision(onchain, revealed, registered, P, regs, eras)
    assert ok is False
    assert next(c for c in checks if "completeness" in c["name"])["ok"] is False


def test_erased_before_decision_is_legitimately_absent():
    # If R5 was erased BEFORE the decision, the pool/reveal exclude it and the active
    # set (block-aware) also excludes it -> still complete and faithful.
    onchain, revealed, registered, regs, eras = _build()
    r5c = revealed["R5"]["commitment"]
    del revealed["R5"]
    eras = [{"commitment": r5c, "block": 7}]  # erased before decision block 10
    pool = [c for c in onchain["candidatePool"] if c != r5c]
    # ranking is unchanged (R5 was gated/ineligible anyway), recompute hash over new pool
    onchain["candidatePool"] = pool
    onchain["rankingHash"] = ranking_hash(
        onchain["donorCommitment"], pool, onchain["rankedRecipientCommitments"], VERSION
    )
    ok, checks = verify_decision(onchain, revealed, registered, P, regs, eras)
    assert ok, [c["name"] for c in checks if not c["ok"]]


def test_rejects_revealing_a_set_different_from_the_pool():
    onchain, revealed, registered, regs, eras = _build()
    del revealed["R2"]  # hide a pool member from reveal (but keep it in the pool)
    ok, checks = verify_decision(onchain, revealed, registered, P, regs, eras)
    assert ok is False
    assert next(c for c in checks if "revealed recipients == candidate pool" in c["name"])["ok"] is False


def test_rejects_an_unregistered_record():
    onchain, revealed, registered, regs, eras = _build()
    missing = [c for c in registered if c != onchain["rankedRecipientCommitments"][0]]
    ok, _ = verify_decision(onchain, revealed, missing, P, regs, eras)
    assert ok is False


def test_rejects_a_reordered_ranking():
    onchain, revealed, registered, regs, eras = _build()
    rc = list(onchain["rankedRecipientCommitments"])
    rc[0], rc[1] = rc[1], rc[0]
    onchain["rankedRecipientCommitments"] = rc
    onchain["rankingHash"] = ranking_hash(onchain["donorCommitment"], onchain["candidatePool"], rc, VERSION)
    ok, _ = verify_decision(onchain, revealed, registered, P, regs, eras)
    assert ok is False


def test_policy_none_fails_recompute_matching_js_no_disk_fallback():
    # No silent disk fallback — a None policy fails the recompute identically in
    # Python and JS (parity, D-021).
    onchain, revealed, registered, regs, eras = _build()
    ok, checks = verify_decision(onchain, revealed, registered, None, regs, eras)
    assert ok is False
    assert next(c for c in checks if c["name"].startswith("recomputed CAS ranking"))["ok"] is False
