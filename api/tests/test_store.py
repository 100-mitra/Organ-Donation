"""Chain-free unit tests for the off-chain store."""
from __future__ import annotations

from api.store import OffChainStore
from engine.commitments import commit


def test_store_commitment_matches_engine():
    s = OffChainStore()
    rec = {"id": "R1", "abo": "O", "waiting_days": 100}
    e = s.add(rec, "recipient", salt_hex="00112233")
    assert e["commitment"] == commit(rec, "00112233")
    assert e["kind"] == "recipient"


def test_reveal_exposes_salt_and_recipients_are_filtered():
    s = OffChainStore()
    s.add({"id": "R1", "waiting_days": 1}, "recipient", "00")
    s.add({"id": "D1"}, "donor", "01")
    rev = s.reveal()
    assert set(rev) == {"R1", "D1"}
    assert rev["R1"]["salt"] == "00"
    assert [e["record"]["id"] for e in s.recipients()] == ["R1"]


def test_random_salt_is_used_when_none_given():
    s = OffChainStore()
    e1 = s.add({"id": "R1", "x": 1}, "recipient")
    s2 = OffChainStore()
    e2 = s2.add({"id": "R1", "x": 1}, "recipient")
    # Different random salts => different commitments for the same record.
    assert e1["salt"] != e2["salt"]
    assert e1["commitment"] != e2["commitment"]
