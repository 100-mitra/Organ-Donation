"""Eligibility gate tests: ABO, virtual crossmatch, sanity."""
from __future__ import annotations

from engine.compatibility import abo_ok, crossmatch_ok, donor_antigens, eligibility, sanity_ok
from engine.policy import load_policy

P = load_policy()
DHLA = {"A": [1, 2], "B": [7, 8], "DR": [4, 15]}


def test_abo_truth_table():
    assert abo_ok("O", "A", P) and abo_ok("O", "O", P) and abo_ok("O", "AB", P)
    assert abo_ok("A", "A", P) and abo_ok("A", "AB", P)
    assert not abo_ok("A", "O", P)
    assert not abo_ok("AB", "O", P)
    assert abo_ok("AB", "AB", P)


def test_donor_antigens_union():
    assert donor_antigens(DHLA) == {1, 2, 7, 8, 4, 15}


def test_crossmatch_excludes_on_unacceptable_antigen():
    assert crossmatch_ok(DHLA, [99], P)  # 99 not expressed -> ok
    assert not crossmatch_ok(DHLA, [7, 99], P)  # donor expresses B7 -> fail


def test_sanity_bands():
    assert sanity_ok({"age": 45}, P)
    assert sanity_ok({"age": 0}, P)
    assert not sanity_ok({"age": 95}, P)  # max 90


def test_eligibility_combines_gates():
    donor = {"abo": "A", "hla": DHLA}
    recip = {"abo": "O", "hla": {}, "unacceptable_antigens": [], "age": 45}
    ok, gates = eligibility(donor, recip, P)
    assert ok is False and gates["abo"] is False  # A cannot give to O
    assert gates["virtual_crossmatch"] is True and gates["sanity"] is True
