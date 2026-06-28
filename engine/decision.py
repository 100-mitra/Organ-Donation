"""Build the allocation DECISION object + its ranking hash.

The decision is what gets logged on-chain (CLAUDE.md §8). Its `ranking_hash` binds
the donor, the policy version, and the ORDERED list of ranked recipient commitments
into a single value an independent verifier can recompute. The hash uses the same
canon-v1 serialization as commitments, so the JS verifier reproduces it with the
same code path that reproduces the frozen commitment vectors.
"""
from __future__ import annotations

from engine.commitments import canonical_json, keccak256


def ranking_hash(
    donor_commitment: str,
    ranked_recipient_commitments: list[str],
    policy_version: str,
) -> str:
    """keccak256 over the canon-v1 serialization of the decision core.

    Order of `ranked_recipient_commitments` is significant — reordering changes
    the hash (that is the whole point: it pins the exact ranking).
    """
    core = {
        "donor_commitment": donor_commitment,
        "policy_version": policy_version,
        "ranked_recipient_commitments": list(ranked_recipient_commitments),
    }
    return "0x" + keccak256(canonical_json(core).encode("utf-8")).hex()


def build_decision(
    donor_commitment: str,
    ranked_recipient_commitments: list[str],
    policy_version: str,
) -> dict:
    """Assemble the full decision record (off-chain view; on-chain logs the fields)."""
    return {
        "donor_commitment": donor_commitment,
        "policy_version": policy_version,
        "ranked_recipient_commitments": list(ranked_recipient_commitments),
        "ranking_hash": ranking_hash(
            donor_commitment, ranked_recipient_commitments, policy_version
        ),
    }
