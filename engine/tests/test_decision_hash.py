"""Python side of the decision ranking_hash parity contract (binds the pool)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.decision import ranking_hash

V = json.loads(
    (Path(__file__).parent / "vectors" / "decision_hash_vectors.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", V["cases"], ids=lambda c: c["name"])
def test_decision_ranking_hash_vector(case):
    assert ranking_hash(
        case["donor_commitment"], case["candidate_pool"],
        case["ranked_recipient_commitments"], case["policy_version"],
    ) == case["ranking_hash"]
