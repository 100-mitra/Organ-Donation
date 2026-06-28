"""Determinism + frozen-vector tests for the commitment scheme.

These tests are the guard rail for the entire verifiability thesis: if the
commitment for a given (record, salt) ever changes, independent recompute breaks.
The same frozen vectors in engine/tests/vectors/commitment_vectors.json must later
be reproduced by the JS browser verifier (Phase 1) — see docs/canonicalization.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.commitments import (
    CANONICALIZATION_VERSION,
    canonical_json,
    commit,
    keccak256,
)

VECTORS_PATH = Path(__file__).parent / "vectors" / "commitment_vectors.json"
VECTORS = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))


def test_keccak_is_ethereum_variant_not_nist_sha3():
    # The canonical empty-input Keccak-256 digest. NIST SHA3-256("") differs
    # (a7ffc6f8...), so this asserts we are using the Ethereum variant.
    assert "0x" + keccak256(b"").hex() == VECTORS["keccak256_empty"]


def test_canonicalization_version_matches_vectors():
    assert CANONICALIZATION_VERSION == VECTORS["canonicalization_version"]


@pytest.mark.parametrize("vec", VECTORS["vectors"], ids=lambda v: v["name"])
def test_frozen_canonical_json(vec):
    assert canonical_json(vec["record"]) == vec["canonical_json"]


@pytest.mark.parametrize("vec", VECTORS["vectors"], ids=lambda v: v["name"])
def test_frozen_commitment(vec):
    assert commit(vec["record"], vec["salt"]) == vec["commitment"]


@pytest.mark.parametrize("vec", VECTORS["vectors"], ids=lambda v: v["name"])
def test_key_insertion_order_does_not_change_commitment(vec):
    record = vec["record"]
    reordered = {k: record[k] for k in reversed(list(record))}
    assert commit(reordered, vec["salt"]) == commit(record, vec["salt"])


def test_floats_are_rejected():
    # Integer/fixed-point only — a float anywhere must raise, not silently hash.
    with pytest.raises(ValueError):
        commit({"cpra": 80.0}, "00")
    with pytest.raises(ValueError):
        commit({"nested": {"x": [1, 2.5]}}, "00")


def test_different_salt_changes_commitment():
    record = VECTORS["vectors"][0]["record"]
    assert commit(record, "00") != commit(record, "01")
