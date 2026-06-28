"""Policy JSON must stay in sync with the YAML source, and be well-formed."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from engine.policy import load_policy

ROOT = Path(__file__).resolve().parents[2]


def test_json_matches_yaml_source():
    yaml_policy = yaml.safe_load((ROOT / "docs/policy/kidney_v1.yaml").read_text(encoding="utf-8"))
    expected = json.dumps(yaml_policy, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    actual = (ROOT / "docs/policy/kidney_v1.json").read_text(encoding="utf-8")
    assert actual == expected, "kidney_v1.json out of sync — run scripts/gen_policy_json.py"


def test_weights_sum_to_100():
    p = load_policy()
    assert sum(a["weight"] for a in p["attributes"].values()) == 100


def test_policy_has_required_sections():
    p = load_policy()
    assert p["version"] == "kidney_v1"
    assert {"gates", "attributes", "tie_break", "region_zones"} <= set(p)
