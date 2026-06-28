"""Tests for the trivial Phase 1 ranking + decision ranking hash."""
from __future__ import annotations

from engine.decision import build_decision, ranking_hash
from engine.scoring import POLICY_VERSION, rank_recipients, ranked_ids
from engine.skeleton_fixtures import RECIPIENTS


def test_ranking_is_waiting_time_descending_with_id_tiebreak():
    # R2 and R4 both have 1800 days; tie-break by ascending id => R2 before R4.
    assert ranked_ids(RECIPIENTS) == ["R2", "R4", "R1", "R3", "R5"]


def test_ranking_is_deterministic_regardless_of_input_order():
    forward = ranked_ids(RECIPIENTS)
    reversed_pool = list(reversed(RECIPIENTS))
    assert ranked_ids(reversed_pool) == forward


def test_ranking_does_not_mutate_input():
    before = [r["id"] for r in RECIPIENTS]
    rank_recipients(RECIPIENTS)
    assert [r["id"] for r in RECIPIENTS] == before


def test_ranking_hash_is_order_sensitive():
    donor = "0x" + "11" * 32
    a = "0x" + "aa" * 32
    b = "0x" + "bb" * 32
    h1 = ranking_hash(donor, [a, b], POLICY_VERSION)
    h2 = ranking_hash(donor, [b, a], POLICY_VERSION)
    assert h1 != h2  # reordering the ranking changes the hash


def test_ranking_hash_is_reproducible():
    donor = "0x" + "11" * 32
    commits = ["0x" + "aa" * 32, "0x" + "bb" * 32, "0x" + "cc" * 32]
    h1 = ranking_hash(donor, commits, POLICY_VERSION)
    h2 = ranking_hash(donor, list(commits), POLICY_VERSION)
    assert h1 == h2 and h1.startswith("0x") and len(h1) == 66


def test_build_decision_shape():
    d = build_decision("0x" + "11" * 32, ["0x" + "aa" * 32], POLICY_VERSION)
    assert set(d) == {
        "donor_commitment",
        "policy_version",
        "ranked_recipient_commitments",
        "ranking_hash",
    }
    assert d["policy_version"] == "skeleton-waiting-time-v0"
