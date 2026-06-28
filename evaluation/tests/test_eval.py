"""Tests for the evaluation harness: waitlist, policies, simulation."""
from __future__ import annotations

from evaluation.policies import (
    cas_policy, longevity_policy, rank_cas, rank_fcfs, with_weights,
)
from evaluation.simulate import simulate
from evaluation.waitlist import generate


def test_waitlist_deterministic():
    assert generate(50, 20, seed=1) == generate(50, 20, seed=1)


def test_donor_stream_arrives_over_time():
    _w, d = generate(100, 30, seed=2)
    rec = [x["recovered_at_epoch_day"] for x in d]
    assert rec == sorted(rec) and len(set(rec)) == 30  # strictly increasing


def test_policy_variants_are_independent_copies():
    assert cas_policy()["attributes"]["longevity_epts"]["weight"] == 0
    assert longevity_policy(25)["attributes"]["longevity_epts"]["weight"] == 25
    assert cas_policy()["attributes"]["longevity_epts"]["weight"] == 0  # not mutated
    assert with_weights(waiting_time=50)["attributes"]["waiting_time"]["weight"] == 50


def test_fcfs_applies_gates_and_orders_by_waiting():
    w, d = generate(60, 1, seed=3)
    ranked, _ = rank_fcfs(d[0], w, cas_policy(), "0x" + "00" * 32)
    wd = [e["waiting_days"] for e in ranked]
    assert wd == sorted(wd, reverse=True)  # longest waiting first
    assert len(ranked) <= len(w)  # gates may exclude


def test_simulation_invariants():
    res = simulate(*_run(200, 60, 4, rank_cas))
    tx = res["transplants"]
    assert len(tx) <= 60  # at most one transplant per donor
    assert len(tx) + len(res["not_transplanted"]) == 200
    tx_ids = {t["recipient_id"] for t in tx}
    assert len(tx_ids) == len(tx)  # nobody transplanted twice
    assert tx_ids.isdisjoint({r["id"] for r in res["not_transplanted"]})


def test_cas_and_fcfs_allocate_differently():
    w, d = generate(200, 60, seed=5)
    cas = [t["recipient_id"] for t in simulate(w, d, rank_cas, cas_policy())["transplants"]]
    fcfs = [t["recipient_id"] for t in simulate(w, d, rank_fcfs, cas_policy())["transplants"]]
    assert cas != fcfs


def _run(n, m, seed, fn):
    w, d = generate(n, m, seed=seed)
    return w, d, fn, cas_policy()
