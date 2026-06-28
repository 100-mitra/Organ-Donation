"""Python side of the frozen CAS-ranking parity contract.

The JS twin (web/src/cas.test.js) reproduces the SAME vectors; together they prove
the CAS ranking is byte-for-byte identical across the two implementations.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.policy import load_policy
from engine.scoring import rank

V = json.loads(
    (Path(__file__).parent / "vectors" / "cas_ranking_vectors.json").read_text(encoding="utf-8")
)
P = load_policy()


def _comparable(evaluated: list[dict]) -> list[dict]:
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


@pytest.mark.parametrize("case", V["cases"], ids=lambda c: c["name"])
def test_cas_ranking_vector(case):
    ranked, evaluated = rank(case["donor"], case["recipients"], P, case["decision_seed"])
    assert [e["id"] for e in ranked] == case["expected"]["ranking"]
    assert _comparable(evaluated) == case["expected"]["scored"]
