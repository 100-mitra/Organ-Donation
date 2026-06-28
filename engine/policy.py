"""Load the versioned, machine-readable allocation policy.

The contract logs `policy_version` with every decision; the verifier loads the
matching policy and re-applies it. Both the engine and the JS verifier consume the
same `docs/policy/<version>.json` (derived from the YAML source by
scripts/gen_policy_json.py) so they interpret byte-identical rules.
"""
from __future__ import annotations

import json
from pathlib import Path

POLICY_DIR = Path(__file__).resolve().parents[1] / "docs" / "policy"


def load_policy(version: str = "kidney_v1") -> dict:
    path = POLICY_DIR / f"{version}.json"
    if not path.exists():
        raise FileNotFoundError(f"policy {path} not found (run scripts/gen_policy_json.py)")
    return json.loads(path.read_text(encoding="utf-8"))
