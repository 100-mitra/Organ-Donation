"""Off-chain ENCRYPTED PII store + individual erasure (Phase 3).

PII never goes on-chain — only the salted commitment does (§8). Records are
encrypted at rest (AES-256-GCM); the per-record salt is the privacy + erasure lever
(§14). Erasing a record DESTROYS its salt + ciphertext, after which its on-chain
commitment is permanently unlinkable (the public commitment itself stays — the
ledger is append-only — but it can no longer be opened). In-memory backing here;
the encrypt/erase interface is the point and a SQLite backend is a drop-in swap.
"""
from __future__ import annotations

import json
import os

from Crypto.Cipher import AES

from engine.commitments import canonical_json, commit


class EncryptedStore:
    def __init__(self, key: bytes | None = None) -> None:
        # At-rest key. In production this is a KMS/HSM-held key, never on disk with
        # the data; here it is process-local.
        self._key = key or os.urandom(32)
        self._by_id: dict[str, dict] = {}

    def add(self, record: dict, kind: str, salt_hex: str | None = None) -> dict:
        rid = record["id"]
        salt = salt_hex or os.urandom(16).hex()
        commitment = commit(record, salt)
        cipher = AES.new(self._key, AES.MODE_GCM)
        ct, tag = cipher.encrypt_and_digest(canonical_json(record).encode("utf-8"))
        self._by_id[rid] = {
            "commitment": commitment, "salt": salt, "kind": kind,
            "nonce": cipher.nonce, "ct": ct, "tag": tag, "erased": False,
        }
        return {"id": rid, "commitment": commitment, "kind": kind}

    def _decrypt(self, e: dict) -> dict:
        cipher = AES.new(self._key, AES.MODE_GCM, nonce=e["nonce"])
        return json.loads(cipher.decrypt_and_verify(e["ct"], e["tag"]))

    def get(self, rid: str) -> dict | None:
        """Decrypted entry {record, salt, commitment, kind} or None (missing/erased)."""
        e = self._by_id.get(rid)
        if e is None or e["erased"]:
            return None
        return {"record": self._decrypt(e), "salt": e["salt"],
                "commitment": e["commitment"], "kind": e["kind"]}

    def recipients(self) -> list[dict]:
        return [self.get(rid) for rid, e in self._by_id.items()
                if e["kind"] == "recipient" and not e["erased"]]

    def reveal(self) -> dict[str, dict]:
        """Records + salts an auditor recomputes from — erased records are absent."""
        return {rid: self.get(rid) for rid, e in self._by_id.items() if not e["erased"]}

    def erase(self, rid: str) -> str | None:
        """Destroy the salt + ciphertext for a record (the §14 erasure). Returns the
        (now-unlinkable) commitment so the caller can mark it erased on-chain."""
        e = self._by_id.get(rid)
        if e is None or e["erased"]:
            return None
        commitment = e["commitment"]
        e["salt"] = e["nonce"] = e["ct"] = e["tag"] = None  # destroyed
        e["erased"] = True
        return commitment

    def clear(self) -> None:
        self._by_id.clear()
