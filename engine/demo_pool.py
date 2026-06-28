"""Fixed Phase 2 demo pool (deterministic) for the API /seed + the live demo.

Richer than the Phase 1 skeleton schema: full §8 records so the CAS gates + scoring
have something to work on. Deliberately includes candidates that the gates EXCLUDE
(R4 crossmatch, R5 sanity) so the explanation/eligibility is visible end-to-end.
The Phase 2 synthetic generator (engine/data_gen.py) covers realistic distributions;
this fixed pool keeps the demo reproducible.
"""
from __future__ import annotations

DONOR = {
    "id": "D1",
    "abo": "O",
    "hla": {"A": [1, 2], "B": [7, 8], "DR": [4, 15]},
    "age": 35,
    "region": "TN",
    "recovered_at_epoch_day": 20000,
}

RECIPIENTS = [
    # eligible — long wait
    {"id": "R1", "abo": "O", "hla": {"A": [1, 2], "B": [7, 8], "DR": [4, 15]}, "age": 50,
     "unacceptable_antigens": [], "cpra": 10, "dialysis_start_epoch_day": 13000,
     "prior_living_donor": False, "region": "TN", "urgent": False},
    # eligible — pediatric
    {"id": "R2", "abo": "A", "hla": {"A": [1, 3], "B": [7, 9], "DR": [4, 11]}, "age": 12,
     "unacceptable_antigens": [], "cpra": 0, "dialysis_start_epoch_day": 18500,
     "prior_living_donor": False, "region": "KA", "urgent": False},
    # eligible — highly sensitized + prior living donor
    {"id": "R3", "abo": "B", "hla": {"A": [2, 5], "B": [8, 12], "DR": [15, 7]}, "age": 40,
     "unacceptable_antigens": [], "cpra": 98, "dialysis_start_epoch_day": 17000,
     "prior_living_donor": True, "region": "MH", "urgent": False},
    # GATED — virtual crossmatch (donor expresses B7; recipient lists 7 as unacceptable)
    {"id": "R4", "abo": "O", "hla": {"A": [1, 2], "B": [7, 8], "DR": [4, 15]}, "age": 45,
     "unacceptable_antigens": [7], "cpra": 50, "dialysis_start_epoch_day": 15000,
     "prior_living_donor": False, "region": "DL", "urgent": False},
    # GATED — sanity (age out of band)
    {"id": "R5", "abo": "O", "hla": {"A": [1, 2], "B": [7, 8], "DR": [4, 15]}, "age": 95,
     "unacceptable_antigens": [], "cpra": 0, "dialysis_start_epoch_day": 14000,
     "prior_living_donor": False, "region": "AP", "urgent": False},
]
