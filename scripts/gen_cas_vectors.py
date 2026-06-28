"""Generate the frozen CAS-ranking vectors (Python is the source of truth).

Each case fixes a donor + recipient pool + tie-break seed; the expected per-candidate
eligibility/CAS/points and the eligible ranking are computed by the engine. Both the
Python engine (engine/tests/test_cas_vectors.py) and the JS twin (web/src/cas.test.js)
must reproduce every case. Run: `python scripts/gen_cas_vectors.py`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.data_gen import generate_pool
from engine.demo_pool import DONOR, RECIPIENTS
from engine.policy import load_policy
from engine.scoring import rank

ROOT = Path(__file__).resolve().parents[1]
P = load_policy()
SEED = "0x" + "ab" * 32


def comparable(evaluated: list[dict]) -> list[dict]:
    out = []
    for e in evaluated:
        if e["eligible"]:
            out.append({
                "id": e["id"], "eligible": True, "cas": e["cas"],
                "points": {k: v["points"] for k, v in e["breakdown"].items()},
            })
        else:
            out.append({"id": e["id"], "eligible": False, "cas": None, "points": None})
    return out


def case(name: str, donor: dict, recips: list[dict], seed: str) -> dict:
    ranked, evaluated = rank(donor, recips, P, seed)
    return {
        "name": name,
        "decision_seed": seed,
        "donor": donor,
        "recipients": recips,
        "expected": {"scored": comparable(evaluated), "ranking": [e["id"] for e in ranked]},
    }


# A keccak tie-break case: three identical eligible recipients (equal CAS + equal
# waiting_days) — only the keccak seed disambiguates, exercising that path in both ports.
TIE_DONOR = {
    "id": "D1", "abo": "O", "hla": {"A": [1, 2], "B": [7, 8], "DR": [4, 15]},
    "age": 40, "region": "TN", "recovered_at_epoch_day": 20000,
}
_BASE = {
    "abo": "O", "hla": {"A": [1, 2], "B": [7, 8], "DR": [4, 15]}, "age": 45,
    "unacceptable_antigens": [], "cpra": 0, "dialysis_start_epoch_day": 16000,
    "prior_living_donor": False, "region": "TN", "urgent": False,
}
TIE_RECIPS = [{**_BASE, "id": rid} for rid in ("RA", "RB", "RC")]

d8, r8 = generate_pool(8, seed=123)

cases = [
    case("demo_pool", DONOR, RECIPIENTS, SEED),
    case("synthetic_8", d8, r8, SEED),
    case("tie_break_keccak", TIE_DONOR, TIE_RECIPS, SEED),
]

out = {
    "policy_version": "kidney_v1",
    "note": ("Frozen CAS-ranking vectors. Python (engine) and JS (cas.js) MUST reproduce "
             "each case's `scored` (eligibility + cas + per-attribute points) and `ranking`. "
             "Regenerate only deliberately. See docs/decisions.md D-018."),
    "cases": cases,
}
path = ROOT / "engine" / "tests" / "vectors" / "cas_ranking_vectors.json"
path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
print(f"wrote {len(cases)} cases to {path}")
for c in cases:
    print(f"  {c['name']:18} ranking={c['expected']['ranking']}")
