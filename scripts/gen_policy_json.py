"""Derive the machine-readable policy JSON from the human-authored YAML.

`docs/policy/kidney_v1.yaml` is the source of truth; the Python engine AND the JS
verifier both load `docs/policy/kidney_v1.json` so they interpret byte-identical
policy structure. `engine/tests/test_policy.py` asserts the JSON matches the YAML,
so editing the YAML without regenerating fails CI. Run: `python scripts/gen_policy_json.py`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def derive(version: str = "kidney_v1") -> str:
    src = ROOT / "docs" / "policy" / f"{version}.yaml"
    policy = yaml.safe_load(src.read_text(encoding="utf-8"))
    # sort_keys for a canonical, stable artifact; integer map keys become strings
    # (JSON requirement) — the scorer looks up map ratings by str(input).
    return json.dumps(policy, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> None:
    version = sys.argv[1] if len(sys.argv) > 1 else "kidney_v1"
    out = ROOT / "docs" / "policy" / f"{version}.json"
    out.write_text(derive(version), encoding="utf-8", newline="\n")  # LF, not CRLF
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
