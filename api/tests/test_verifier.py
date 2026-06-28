"""Chain-free unit tests for engine.verifier under the Phase 2 CAS recompute."""
from __future__ import annotations

from engine.commitments import commit
from engine.decision import ranking_hash
from engine.policy import load_policy
from engine.scoring import rank
from engine.verifier import verify_decision

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


# R1..R3 eligible (distinct CAS), R4 gated (crossmatch on B7), R5 gated (sanity age).
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
        entry = {"record": r, "salt": SALT, "commitment": c, "kind": "recipient"}
        revealed[r["id"]] = entry
        by_id[r["id"]] = entry
    seed = donor_entry["commitment"]
    ranked_eligible, _ = rank(DONOR, RECIPS, P, seed)
    ranked_commitments = [by_id[e["id"]]["commitment"] for e in ranked_eligible]
    onchain = {
        "donorCommitment": donor_entry["commitment"],
        "policyVersion": VERSION,
        "rankedRecipientCommitments": ranked_commitments,
        "rankingHash": ranking_hash(donor_entry["commitment"], ranked_commitments, VERSION),
    }
    registered = [e["commitment"] for e in revealed.values()]
    return onchain, revealed, registered, ranked_eligible


def test_accepts_a_faithful_cas_decision():
    onchain, revealed, registered, _ = _build()
    ok, checks = verify_decision(onchain, revealed, registered)
    assert ok, [c["name"] for c in checks if not c["ok"]]


def test_gated_recipients_are_excluded_from_the_ranking():
    _, _, _, ranked = _build()
    ids = [e["id"] for e in ranked]
    assert set(ids) == {"R1", "R2", "R3"}  # R4 (crossmatch) + R5 (sanity) excluded


def test_rejects_including_an_ineligible_recipient():
    onchain, revealed, registered, _ = _build()
    gated = revealed["R4"]["commitment"]  # ineligible (crossmatch)
    rc = onchain["rankedRecipientCommitments"] + [gated]
    tampered = {**onchain, "rankedRecipientCommitments": rc,
                "rankingHash": ranking_hash(onchain["donorCommitment"], rc, VERSION)}
    ok, _ = verify_decision(tampered, revealed, registered)
    assert ok is False


def test_rejects_a_reordered_ranking():
    onchain, revealed, registered, _ = _build()
    rc = list(onchain["rankedRecipientCommitments"])
    rc[0], rc[1] = rc[1], rc[0]
    tampered = {**onchain, "rankedRecipientCommitments": rc,
                "rankingHash": ranking_hash(onchain["donorCommitment"], rc, VERSION)}
    ok, _ = verify_decision(tampered, revealed, registered)
    assert ok is False


def test_rejects_an_unregistered_record():
    onchain, revealed, registered, _ = _build()
    missing = [c for c in registered if c != onchain["rankedRecipientCommitments"][0]]
    ok, _ = verify_decision(onchain, revealed, missing)
    assert ok is False


def test_rejects_recipient_hidden_under_unknown_kind():
    onchain, revealed, registered, _ = _build()
    revealed["R1"] = {**revealed["R1"], "kind": "ghost"}
    ok, checks = verify_decision(onchain, revealed, registered)
    assert ok is False
    assert next(c for c in checks if "kinds are recognized" in c["name"])["ok"] is False
