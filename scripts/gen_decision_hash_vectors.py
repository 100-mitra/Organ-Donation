"""Generate frozen decision ranking_hash vectors (Python is the source of truth).

The Phase 3 ranking_hash binds donor + policy + the full candidate POOL + the
ranking. Both engine/decision.py and web/src/canon.js (rankingHash) must reproduce
these. Run: `python scripts/gen_decision_hash_vectors.py`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.decision import ranking_hash


def h(n: str) -> str:
    return "0x" + n * 32


CASES = [
    {"name": "basic", "donor_commitment": h("d1"),
     "candidate_pool": [h("a1"), h("a2"), h("a3")],
     "ranked_recipient_commitments": [h("a3"), h("a1")], "policy_version": "kidney_v1"},
    {"name": "all_gated_empty_ranking", "donor_commitment": h("d2"),
     "candidate_pool": [h("b1"), h("b2")],
     "ranked_recipient_commitments": [], "policy_version": "kidney_v1"},
    {"name": "single", "donor_commitment": h("d3"),
     "candidate_pool": [h("c1")],
     "ranked_recipient_commitments": [h("c1")], "policy_version": "kidney_v1"},
]

for c in CASES:
    c["ranking_hash"] = ranking_hash(
        c["donor_commitment"], c["candidate_pool"],
        c["ranked_recipient_commitments"], c["policy_version"]
    )

out = {
    "note": ("Frozen decision ranking_hash vectors (binds donor + policy + candidate "
             "pool + ranking). Python (decision.ranking_hash) and JS (canon.rankingHash) "
             "must reproduce every hash. See docs/decisions.md D-020."),
    "cases": CASES,
}
path = Path(__file__).resolve().parents[1] / "engine" / "tests" / "vectors" / "decision_hash_vectors.json"
path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
print(f"wrote {len(CASES)} cases to {path}")
for c in CASES:
    print(f"  {c['name']:24} {c['ranking_hash']}")
