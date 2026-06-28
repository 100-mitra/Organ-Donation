"""Chain-free unit tests for the encrypted off-chain store + erasure."""
from __future__ import annotations

from api.store import EncryptedStore
from engine.commitments import commit


def test_add_and_get_roundtrip_with_matching_commitment():
    s = EncryptedStore()
    rec = {"id": "R1", "abo": "O", "x": 1}
    meta = s.add(rec, "recipient", "00112233")
    assert meta["commitment"] == commit(rec, "00112233")
    got = s.get("R1")
    assert got["record"] == rec and got["salt"] == "00112233"
    assert got["commitment"] == meta["commitment"] and got["kind"] == "recipient"


def test_pii_is_encrypted_at_rest():
    s = EncryptedStore()
    s.add({"id": "R1", "secret": "sensitive-pii"}, "recipient", "00")
    raw = s._by_id["R1"]
    assert b"sensitive-pii" not in raw["ct"]  # plaintext never stored in the clear


def test_erase_destroys_salt_and_ciphertext_making_commitment_unlinkable():
    s = EncryptedStore()
    m = s.add({"id": "R1", "x": 1}, "recipient", "00")
    c = s.erase("R1")
    assert c == m["commitment"]  # returned so the caller can mark erased on-chain
    assert s.get("R1") is None  # record no longer recoverable
    assert "R1" not in s.reveal()
    e = s._by_id["R1"]
    assert e["salt"] is None and e["ct"] is None and e["nonce"] is None and e["erased"] is True
    assert s.erase("R1") is None  # idempotent


def test_recipients_and_reveal_exclude_erased():
    s = EncryptedStore()
    s.add({"id": "R1", "x": 1}, "recipient", "00")
    r2 = s.add({"id": "R2", "x": 2}, "recipient", "01")
    s.add({"id": "D1"}, "donor", "02")
    s.erase("R1")
    assert [r["commitment"] for r in s.recipients()] == [r2["commitment"]]
    assert set(s.reveal()) == {"R2", "D1"}


def test_random_salt_when_none_given():
    s1, s2 = EncryptedStore(), EncryptedStore()
    a = s1.add({"id": "R1", "x": 1}, "recipient")
    b = s2.add({"id": "R1", "x": 1}, "recipient")
    assert a["commitment"] != b["commitment"]  # different random salts
