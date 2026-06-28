"""Chain-free unit tests for engine.verifier — incl. the registration binding (D-013)."""
from __future__ import annotations

from engine.commitments import commit
from engine.decision import ranking_hash
from engine.verifier import verify_decision

POLICY = "skeleton-waiting-time-v0"

DONOR = {"id": "D1", "abo": "O"}
R1 = {"id": "R1", "waiting_days": 1000}
R2 = {"id": "R2", "waiting_days": 2000}


def _fixture():
    revealed = {
        "D1": {"record": DONOR, "salt": "00", "commitment": commit(DONOR, "00"), "kind": "donor"},
        "R1": {"record": R1, "salt": "01", "commitment": commit(R1, "01"), "kind": "recipient"},
        "R2": {"record": R2, "salt": "02", "commitment": commit(R2, "02"), "kind": "recipient"},
    }
    ranked = [revealed["R2"]["commitment"], revealed["R1"]["commitment"]]  # R2 (2000) first
    onchain = {
        "donorCommitment": revealed["D1"]["commitment"],
        "policyVersion": POLICY,
        "rankedRecipientCommitments": ranked,
        "rankingHash": ranking_hash(revealed["D1"]["commitment"], ranked, POLICY),
    }
    registered = [e["commitment"] for e in revealed.values()]
    return onchain, revealed, registered


def test_accepts_a_faithful_decision():
    onchain, revealed, registered = _fixture()
    ok, _ = verify_decision(onchain, revealed, registered)
    assert ok


def test_rejects_when_a_decision_commitment_was_never_registered():
    # ISOLATES THE BINDING: the ranking still recomputes correctly, but one revealed
    # commitment is absent from the on-chain Registered set -> must reject (D-013).
    onchain, revealed, registered = _fixture()
    registered_missing = [c for c in registered if c != revealed["R1"]["commitment"]]
    ok, checks = verify_decision(onchain, revealed, registered_missing)
    assert ok is False
    binding = next(c for c in checks if c["name"].startswith("revealed R1"))
    ranking = next(c for c in checks if c["name"].startswith("recomputed ranking =="))
    assert binding["ok"] is False  # the binding is what caught it
    assert ranking["ok"] is True   # ranking alone would have passed -> binding adds the protection


def test_rejects_a_substituted_unregistered_record():
    # The substitution attack: reveal a self-consistent record that was never committed.
    onchain, revealed, registered = _fixture()
    fake = {"id": "R1", "waiting_days": 9999}
    revealed["R1"] = {"record": fake, "salt": "01", "commitment": commit(fake, "01"), "kind": "recipient"}
    ok, _ = verify_decision(onchain, revealed, registered)
    assert ok is False


def test_rejects_a_tampered_ranking_hash():
    onchain, revealed, registered = _fixture()
    onchain = {**onchain, "rankingHash": "0x" + "00" * 32}
    ok, _ = verify_decision(onchain, revealed, registered)
    assert ok is False
