"""Off-chain PII store (Phase 1 walking skeleton: in-memory).

PII NEVER goes on-chain — only the salted commitment does (CLAUDE.md §8). This
in-memory store holds the full records + their per-record salts; the chain holds
only the commitments. Phase 3 replaces this with an encrypted SQLite store; the
interface is kept small so that swap is local.

The salt is random per record (privacy + the erasure lever, §14). Randomness here
is NOT a determinism violation — scoring is deterministic; salting is not scoring.
"""
from __future__ import annotations

import os

from engine.commitments import commit


class OffChainStore:
    def __init__(self) -> None:
        # id -> {record, salt, commitment, kind}
        self._by_id: dict[str, dict] = {}

    def add(self, record: dict, kind: str, salt_hex: str | None = None) -> dict:
        rid = record["id"]
        salt = salt_hex or os.urandom(16).hex()
        entry = {
            "record": record,
            "salt": salt,
            "commitment": commit(record, salt),
            "kind": kind,
        }
        self._by_id[rid] = entry
        return entry

    def get(self, rid: str) -> dict | None:
        return self._by_id.get(rid)

    def recipients(self) -> list[dict]:
        return [e for e in self._by_id.values() if e["kind"] == "recipient"]

    def reveal(self) -> dict[str, dict]:
        """The data an auditor needs to recompute: records + salts + commitments."""
        return {rid: dict(e) for rid, e in self._by_id.items()}

    def clear(self) -> None:
        self._by_id.clear()
