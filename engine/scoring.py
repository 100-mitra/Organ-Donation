"""Composite Allocation Score (CAS) — pure INTEGER interpreter of kidney_v1.

Replaces the Phase 1 trivial ranking. Given a donor + candidate pool + the policy:
apply the eligibility gates, compute CAS = Σ weight_i × rating_i for each eligible
candidate, rank with deterministic tie-breaks, and return a per-candidate
explanation (gates passed + per-attribute point breakdown).

Integer-only; no floats, no wall-clock, no RNG (CLAUDE.md §10). The JS twin
(web/src/verify.js) must reproduce this byte-for-byte — the contract is the frozen
vectors in engine/tests/vectors/cas_ranking_vectors.json.

Two derived conventions (see docs/decisions.md D-017):
  * waiting_days = donor.recovered_at_epoch_day − recipient.dialysis_start_epoch_day
    (clamped ≥0) — derivable from the committed records, so the verifier needs no
    external "as-of" date and no contract change.
  * tie-break seed = keccak256(decision_seed ‖ recipient_id), with decision_seed =
    the donor commitment (on-chain, known to the verifier).
"""
from __future__ import annotations

from engine.commitments import keccak256
from engine.compatibility import HLA_LOCI, eligibility

POLICY_VERSION = "kidney_v1"


def _clamp(x: int, lo: int, hi: int) -> int:
    return lo if x < lo else hi if x > hi else x


def hla_mismatches(donor_hla: dict, recip_hla: dict) -> int:
    """Donor antigens the recipient does not share, summed over A/B/DR (0..6)."""
    total = 0
    for locus in HLA_LOCI:
        total += len(set(donor_hla.get(locus, [])) - set(recip_hla.get(locus, [])))
    return min(total, 6)


def distance_band(donor_region: str, recip_region: str, zones: dict) -> int:
    if donor_region == recip_region:
        return 0
    dz = zones.get(donor_region)
    if dz is not None and dz == zones.get(recip_region):
        return 1
    return 2


def extract_features(donor: dict, recip: dict, policy: dict) -> dict:
    waiting_days = max(0, donor["recovered_at_epoch_day"] - recip["dialysis_start_epoch_day"])
    return {
        "waiting_days": waiting_days,
        "age_years": recip["age"],
        "prior_living_donor": recip["prior_living_donor"],
        "cpra": recip["cpra"],
        "hla_mismatches": hla_mismatches(donor["hla"], recip["hla"]),
        "distance_band": distance_band(donor["region"], recip["region"], policy["region_zones"]),
        "epts_score": _clamp(recip["age"], 0, 100),  # placeholder input; weight 0 in v1
        "urgent": recip.get("urgent", False),
    }


def rate(rating: dict, value) -> int:
    """Integer rating function (taxonomy pinned in kidney_v1.yaml)."""
    t = rating["type"]
    if t == "linear_clamped":
        return _clamp((value * rating["num"]) // rating["den"], 0, rating["max_points"])
    if t == "linear_descending":
        return max(rating["floor_points"], rating["max_points"] - value * rating["per_mismatch"])
    if t == "step":
        pts = 0
        for s in rating["steps"]:  # ascending breakpoints; highest at<=value wins
            if value >= s["at"]:
                pts = s["points"]
        return pts
    if t == "threshold_bonus":
        return rating["points_if_true"] if value < rating["lt"] else rating["points_if_false"]
    if t == "boolean_bonus":
        # STRICT identity, not truthiness — Python bool() and JS Boolean() disagree on
        # empty containers (bool([]) is False, Boolean([]) is true). Only a literal True
        # earns the bonus, so both engines agree for every input (D-019).
        return rating["points_if_true"] if value is True else rating["points_if_false"]
    if t == "map":
        return rating["map"].get(str(value), rating["default"])
    raise ValueError(f"unknown rating type: {t!r}")


def score(donor: dict, recip: dict, policy: dict) -> dict:
    feats = extract_features(donor, recip, policy)
    cas = 0
    breakdown: dict = {}
    for name, attr in policy["attributes"].items():
        pts = rate(attr["rating"], feats[attr["rating"]["input"]])
        weighted = attr["weight"] * pts
        cas += weighted
        breakdown[name] = {
            "bucket": attr["bucket"],
            "weight": attr["weight"],
            "points": pts,
            "weighted": weighted,
        }
    return {"cas": cas, "breakdown": breakdown, "waiting_days": feats["waiting_days"]}


def _tie_seed(decision_seed: str, recipient_id: str) -> str:
    raw = decision_seed[2:] if decision_seed.startswith("0x") else decision_seed
    return keccak256(bytes.fromhex(raw) + recipient_id.encode("utf-8")).hex()


def evaluate(donor: dict, recipients: list[dict], policy: dict) -> list[dict]:
    """Per-candidate gate + score result (unordered) — the explanation payload."""
    out = []
    for r in recipients:
        ok, gates = eligibility(donor, r, policy)
        row = {"id": r["id"], "eligible": ok, "gates": gates}
        if ok:
            row.update(score(donor, r, policy))
        out.append(row)
    return out


def rank(
    donor: dict, recipients: list[dict], policy: dict, decision_seed: str
) -> tuple[list[dict], list[dict]]:
    """Return (ranked_eligible, evaluated). ranked_eligible is CAS order with the
    policy's deterministic tie-breaks; evaluated includes ineligible candidates."""
    evaluated = evaluate(donor, recipients, policy)
    eligible = [e for e in evaluated if e["eligible"]]

    def key(e):
        k: list = [-e["cas"]]
        for rule in policy["tie_break"]:
            if rule["by"] == "waiting_days":
                k.append(-e["waiting_days"] if rule["direction"] == "desc" else e["waiting_days"])
            elif rule["by"] == "keccak_seed":
                k.append(_tie_seed(decision_seed, e["id"]))  # asc string
        return tuple(k)

    return sorted(eligible, key=key), evaluated


def ranked_ids(donor: dict, recipients: list[dict], policy: dict, decision_seed: str) -> list[str]:
    ranked, _ = rank(donor, recipients, policy, decision_seed)
    return [e["id"] for e in ranked]
