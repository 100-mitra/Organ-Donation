"""Build the allocation DECISION object + its ranking hash.

The decision is logged on-chain (CLAUDE.md §8). Its `ranking_hash` binds the donor,
the policy version, the full CANDIDATE POOL considered (Phase 3 — closes subset-drop,
D-015), and the ORDERED ranked-eligible commitments into one value an independent
verifier recomputes. The hash uses the same canon-v1 serialization as commitments,
so the JS verifier reproduces it on the same code path.
"""
from __future__ import annotations

from engine.commitments import canonical_json, keccak256


def ranking_hash(
    donor_commitment: str,
    candidate_pool: list[str],
    ranked_recipient_commitments: list[str],
    policy_version: str,
) -> str:
    """keccak256 over the canon-v1 serialization of the decision core. List order is
    significant for both the pool and the ranking."""
    core = {
        "donor_commitment": donor_commitment,
        "policy_version": policy_version,
        "candidate_pool": list(candidate_pool),
        "ranked_recipient_commitments": list(ranked_recipient_commitments),
    }
    return "0x" + keccak256(canonical_json(core).encode("utf-8")).hex()


def build_decision(
    donor_commitment: str,
    candidate_pool: list[str],
    ranked_recipient_commitments: list[str],
    policy_version: str,
) -> dict:
    return {
        "donor_commitment": donor_commitment,
        "policy_version": policy_version,
        "candidate_pool": list(candidate_pool),
        "ranked_recipient_commitments": list(ranked_recipient_commitments),
        "ranking_hash": ranking_hash(
            donor_commitment, candidate_pool, ranked_recipient_commitments, policy_version
        ),
    }
