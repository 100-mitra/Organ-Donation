"""CAS scorer tests: rating functions, features, eligibility, ranking, tie-breaks."""
from __future__ import annotations

from engine.policy import load_policy
from engine.scoring import (
    POLICY_VERSION,
    distance_band,
    extract_features,
    hla_mismatches,
    rank,
    rate,
)

P = load_policy()
SEED = "0x" + "11" * 32


def R(name):
    return P["attributes"][name]["rating"]


DONOR = {
    "id": "D1",
    "abo": "O",
    "hla": {"A": [1, 2], "B": [7, 8], "DR": [4, 15]},
    "age": 40,
    "region": "TN",
    "recovered_at_epoch_day": 20000,
}


def recip(rid, abo="O", hla=None, age=45, unacc=None, cpra=0, dstart=16350, pld=False,
          region="TN", urgent=False):
    return {
        "id": rid, "abo": abo,
        "hla": hla or {"A": [1, 2], "B": [7, 8], "DR": [4, 15]},
        "age": age, "unacceptable_antigens": unacc or [], "cpra": cpra,
        "dialysis_start_epoch_day": dstart, "prior_living_donor": pld,
        "region": region, "urgent": urgent,
    }


# ---- rating functions (exact, integer) ----

def test_rate_linear_clamped_waiting():
    r = R("waiting_time")  # num 2, den 73, max 100
    assert [rate(r, v) for v in (0, 365, 3650, 40000)] == [0, 10, 100, 100]


def test_rate_step_cpra():
    r = R("sensitization_cpra")
    assert [rate(r, v) for v in (0, 19, 20, 79, 80, 95, 99, 100)] == [0, 0, 10, 25, 50, 75, 95, 100]


def test_rate_linear_descending_hla():
    r = R("hla_match")  # max 100, per 16, floor 0
    assert [rate(r, v) for v in (0, 6, 7)] == [100, 4, 0]


def test_rate_threshold_pediatric():
    r = R("pediatric")
    assert [rate(r, v) for v in (10, 17, 18, 40)] == [100, 100, 0, 0]


def test_rate_boolean_and_map():
    assert [rate(R("prior_living_donor"), v) for v in (True, False)] == [100, 0]
    pr = R("proximity")
    assert [rate(pr, v) for v in (0, 1, 2, 3)] == [100, 50, 0, 0]  # 3 -> default


# ---- features ----

def test_waiting_days_derived_and_clamped():
    assert extract_features(DONOR, recip("R", dstart=16350), P)["waiting_days"] == 3650
    assert extract_features(DONOR, recip("R", dstart=21000), P)["waiting_days"] == 0  # negative -> 0


def test_hla_mismatches_count():
    assert hla_mismatches(DONOR["hla"], DONOR["hla"]) == 0
    assert hla_mismatches({"A": [1, 2], "B": [7, 8], "DR": [4, 15]},
                          {"A": [1, 3], "B": [7, 9], "DR": [5, 15]}) == 3  # {2},{8},{4}


def test_distance_band():
    z = P["region_zones"]
    assert [distance_band("TN", x, z) for x in ("TN", "KA", "DL")] == [0, 1, 2]


# ---- ranking ----

def test_ineligible_excluded_from_ranking():
    pool = [recip("R1"), recip("Rxm", unacc=[7])]  # donor expresses B7 -> crossmatch fail
    ranked, evaluated = rank(DONOR, pool, P, SEED)
    assert [e["id"] for e in ranked] == ["R1"]
    rxm = next(e for e in evaluated if e["id"] == "Rxm")
    assert rxm["eligible"] is False and rxm["gates"]["virtual_crossmatch"] is False


def test_ranking_is_cas_descending():
    pool = [recip("Rlow", dstart=19000), recip("Rhigh", dstart=10000)]  # Rhigh waits longer
    ranked, _ = rank(DONOR, pool, P, SEED)
    assert [e["id"] for e in ranked] == ["Rhigh", "Rlow"]
    cas = [e["cas"] for e in ranked]
    assert cas == sorted(cas, reverse=True)


def test_tie_break_is_deterministic_regardless_of_input_order():
    a, b = recip("RA"), recip("RB")  # identical features -> equal CAS + equal waiting_days
    o1 = [e["id"] for e in rank(DONOR, [a, b], P, SEED)[0]]
    o2 = [e["id"] for e in rank(DONOR, [b, a], P, SEED)[0]]
    assert o1 == o2  # keccak tie-break, order-independent
    ranked = rank(DONOR, [a, b], P, SEED)[0]
    assert ranked[0]["cas"] == ranked[1]["cas"]  # truly a tie


def test_cas_is_integer_and_fully_explained():
    e = rank(DONOR, [recip("R1")], P, SEED)[0][0]
    assert isinstance(e["cas"], int)
    assert set(e["breakdown"]) == set(P["attributes"])
    assert set(e["gates"]) == {"abo", "virtual_crossmatch", "sanity"}
    for b in e["breakdown"].values():
        assert isinstance(b["points"], int) and isinstance(b["weighted"], int)


def test_policy_version_is_kidney_v1():
    assert POLICY_VERSION == "kidney_v1"
