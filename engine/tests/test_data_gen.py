"""Synthetic generator: determinism, India distribution shape, canon-v1 validity."""
from __future__ import annotations

from collections import Counter

from engine.commitments import canonical_json
from engine.data_gen import generate_pool
from engine.policy import load_policy
from engine.scoring import rank


def test_deterministic_for_a_given_seed():
    assert generate_pool(20, seed=42) == generate_pool(20, seed=42)


def test_different_seeds_differ():
    assert generate_pool(20, seed=1) != generate_pool(20, seed=2)


def test_records_are_canon_v1_valid_integer_only():
    donor, recips = generate_pool(40, seed=7)
    canonical_json(donor)  # raises on floats / out-of-range integers
    for r in recips:
        canonical_json(r)


def test_abo_distribution_shape_matches_india():
    _, recips = generate_pool(3000, seed=3)
    c = Counter(r["abo"] for r in recips)
    assert c.most_common(1)[0][0] == "O"  # O most common (~37%)
    assert min(c, key=c.get) == "AB"  # AB rarest (~7%)
    assert c["O"] / 3000 > 0.30


def test_generated_pool_is_rankable():
    donor, recips = generate_pool(50, seed=9)
    policy = load_policy()
    ranked, evaluated = rank(donor, recips, policy, "0x" + "00" * 32)
    assert len(evaluated) == 50
    assert all(isinstance(e["cas"], int) for e in ranked)
    # with O/B-heavy donors some candidates are gated; ranking ⊆ evaluated
    assert len(ranked) <= 50
