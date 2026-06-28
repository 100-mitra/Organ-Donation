"""Synthetic donor/recipient generator with India-appropriate distributions.

DATA generation only, from a SEEDED PRNG so output is reproducible. This randomness
is for *inputs*, not scoring — the CAS engine stays deterministic (no RNG in
scoring, CLAUDE.md §10). All generated values are integer/str/bool/list (canon-v1
valid). Distributions are approximate, representative Indian figures — NOT real
patient data, and exact numbers vary by region/study.
"""
from __future__ import annotations

import random

# Approx Indian ABO frequencies (per 1000) — O and B notably higher than Western
# populations; AB the rarest. Sums to 1000.
ABO_WEIGHTS = {"O": 374, "B": 329, "A": 224, "AB": 73}

# Simplified integer antigen pools per HLA locus (illustrative — not real allele
# codes; the model is A/B/DR with a handful of antigens each, CLAUDE.md §9).
HLA_POOL = {
    "A": [1, 2, 3, 11, 24, 26, 33, 68],
    "B": [7, 8, 15, 35, 40, 44, 51, 57],
    "DR": [1, 3, 4, 7, 11, 13, 15, 17],
}

REGIONS = ["TN", "KA", "KL", "AP", "MH", "GJ", "RJ", "DL", "PB", "UP", "WB", "BR", "OD", "MP", "AS"]


def _abo(rng: random.Random) -> str:
    r = rng.randrange(1000)
    acc = 0
    for grp, w in ABO_WEIGHTS.items():
        acc += w
        if r < acc:
            return grp
    return "AB"


def _hla(rng: random.Random) -> dict:
    return {loc: sorted(rng.sample(pool, 2)) for loc, pool in HLA_POOL.items()}


def gen_donor(rng: random.Random, did: str = "D1") -> dict:
    return {
        "id": did,
        "abo": _abo(rng),
        "hla": _hla(rng),
        "age": rng.randint(18, 65),
        "region": rng.choice(REGIONS),
        "recovered_at_epoch_day": 20000,
    }


def gen_recipient(rng: random.Random, rid: str) -> dict:
    # CPRA skew: most candidates unsensitized, a minority highly sensitized.
    cpra = 0 if rng.random() < 0.6 else rng.choice([10, 20, 50, 80, 95, 98, 99, 100])
    unacc = (
        sorted(rng.sample(HLA_POOL["B"] + HLA_POOL["A"], rng.choice([0, 0, 1, 2])))
        if cpra
        else []
    )
    return {
        "id": rid,
        "abo": _abo(rng),
        "hla": _hla(rng),
        "age": rng.randint(3, 75),
        "unacceptable_antigens": unacc,
        "cpra": cpra,
        "dialysis_start_epoch_day": rng.randint(14000, 19500),
        "prior_living_donor": rng.random() < 0.05,
        "region": rng.choice(REGIONS),
        "urgent": rng.random() < 0.05,
    }


def generate_pool(n: int = 20, seed: int = 0) -> tuple[dict, list[dict]]:
    """Return (donor, [recipient × n]) — reproducible for a given seed."""
    rng = random.Random(seed)
    donor = gen_donor(rng)
    recipients = [gen_recipient(rng, f"R{i + 1}") for i in range(n)]
    return donor, recipients
