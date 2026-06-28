"""Canonical serialization + salted keccak256 commitments.

This module is the SINGLE SOURCE OF TRUTH for how a record becomes an on-chain
commitment. Both the matching engine (when it logs a decision) and any independent
verifier (the browser Verify page) MUST canonicalize and hash records exactly the
way this module does, or verification fails. The cross-language agreement between
this Python code and the JS verifier is the linchpin of the whole thesis, so the
algorithm is pinned in docs/canonicalization.md and locked by frozen test vectors
in engine/tests/vectors/commitment_vectors.json.

Hard rules (CLAUDE.md §9, §10):
  - Integer / fixed-point values ONLY. Floats are REJECTED up front, because
    float formatting differs across platforms and would break independent
    recompute — the determinism rule is not a preference, it is the thesis.
  - Deterministic serialization: sorted keys, no insignificant whitespace, UTF-8.
  - keccak256 is the Ethereum variant (NOT NIST SHA3-256) so on-chain bytes32
    values match exactly.
"""
from __future__ import annotations

import json
from typing import Any

from eth_hash.auto import keccak

# Bump this whenever the canonicalization algorithm changes. It travels with the
# frozen vectors so a verifier knows which rules produced a given commitment.
CANONICALIZATION_VERSION = "canon-v1"


# canon-v1 integers MUST be within the JS safe-integer range, so Python and JS
# serialize them identically. Beyond this a JS double silently loses precision
# (and may switch to exponent form), diverging from Python's exact int. See
# docs/canonicalization.md.
MAX_SAFE_INT = 2**53 - 1  # 9007199254740991 == Number.MAX_SAFE_INTEGER


def _assert_canon_valid(value: Any, path: str = "$") -> None:
    """Recursively validate a record against canon-v1.

    Rejects: floats (any — they diverge across platforms), integers outside
    [-MAX_SAFE_INT, MAX_SAFE_INT], and non-string object keys. bool is an int
    subclass carrying value 0/1 and is an allowed scalar.
    """
    if isinstance(value, bool):
        return  # True/False are valid; do not treat as out-of-range ints
    if isinstance(value, float):
        raise ValueError(
            f"float at {path}: {value!r}. canon-v1 is integer-only "
            "(floats diverge across platforms)."
        )
    if isinstance(value, int):
        if not (-MAX_SAFE_INT <= value <= MAX_SAFE_INT):
            raise ValueError(
                f"integer out of canon-v1 safe range at {path}: {value!r}. "
                f"Must be within +/-{MAX_SAFE_INT} (JS Number.MAX_SAFE_INTEGER)."
            )
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueError(f"non-string object key at {path}: {k!r}")
            _assert_canon_valid(v, f"{path}.{k}")
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            _assert_canon_valid(v, f"{path}[{i}]")


def canonical_json(record: dict) -> str:
    """Return the canonical JSON string for *record* (see docs/canonicalization.md).

    Sorted keys, compact separators, non-ASCII emitted as raw UTF-8 (matching
    JS ``JSON.stringify`` rather than Python's default \\uXXXX escaping). Floats
    are rejected before serialization.
    """
    _assert_canon_valid(record)
    return json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def keccak256(data: bytes) -> bytes:
    """Ethereum-style Keccak-256 (NOT NIST SHA3-256)."""
    return keccak(data)


def commit(record: dict, salt_hex: str) -> str:
    """Compute the salted commitment for *record*.

    ``commitment = keccak256( utf8(canonical_json(record)) || bytes.fromhex(salt) )``

    Returns a 0x-prefixed 32-byte hex string suitable for an on-chain ``bytes32``.
    The salt is per-record, random, and stored off-chain; destroying it makes the
    commitment unlinkable — the erasure mechanism of CLAUDE.md §14.
    """
    salt = bytes.fromhex(salt_hex)
    message = canonical_json(record).encode("utf-8") + salt
    return "0x" + keccak256(message).hex()
