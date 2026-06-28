"""Eligibility HARD GATES (CLAUDE.md §9 Step A): ABO, virtual crossmatch, sanity.

A candidate failing ANY gate is excluded from scoring entirely (not down-ranked).
Pure + deterministic. The JS twin lives in web/src/verify.js (Phase 2 parity).
"""
from __future__ import annotations

HLA_LOCI = ("A", "B", "DR")


def abo_ok(donor_abo: str, recip_abo: str, policy: dict) -> bool:
    """donor -> recipient ABO compatibility (compatibility, not identity)."""
    return recip_abo in policy["gates"]["abo"].get(donor_abo, [])


def donor_antigens(donor_hla: dict) -> set:
    """All HLA antigens the donor expresses across A/B/DR."""
    out: set = set()
    for locus in HLA_LOCI:
        out.update(donor_hla.get(locus, []))
    return out


def crossmatch_ok(donor_hla: dict, recip_unacceptable: list, policy: dict) -> bool:
    """Virtual crossmatch: fail if the donor expresses any unacceptable antigen."""
    if not policy["gates"]["virtual_crossmatch"]["enabled"]:
        return True
    return donor_antigens(donor_hla).isdisjoint(set(recip_unacceptable))


def sanity_ok(recip: dict, policy: dict) -> bool:
    s = policy["gates"]["sanity"]
    return s["min_age_years"] <= recip["age"] <= s["max_age_years"]


def eligibility(donor: dict, recip: dict, policy: dict) -> tuple[bool, dict]:
    """Return (eligible, {gate_name: passed}) — the gate map feeds the explanation."""
    gates = {
        "abo": abo_ok(donor["abo"], recip["abo"], policy),
        "virtual_crossmatch": crossmatch_ok(
            donor["hla"], recip.get("unacceptable_antigens", []), policy
        ),
        "sanity": sanity_ok(recip, policy),
    }
    return all(gates.values()), gates
