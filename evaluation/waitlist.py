"""Synthetic waitlist + deceased-donor stream for the evaluation (SEEDED).

Reuses the engine's India-distribution generator (engine/data_gen.py) for a few
hundred recipients, and builds a donor stream arriving over time (increasing
recovered_at). NOT real patient data — representative distributions only.
"""
from __future__ import annotations

import random

from engine.data_gen import gen_donor, gen_recipient

DONOR_INTERVAL_DAYS = 20  # one deceased donor every ~20 days (low rate, India-like)
EPOCH_BASE = 20000        # first donor's recovery day (recipients' dialysis predates this)


def generate(n_recipients: int = 400, n_donors: int = 150, seed: int = 0):
    """Return (waitlist, donor_stream). Reproducible for a given seed."""
    rng = random.Random(seed)
    waitlist = [gen_recipient(rng, f"R{i + 1}") for i in range(n_recipients)]
    donors = []
    for i in range(n_donors):
        d = gen_donor(rng, f"D{i + 1}")
        d["recovered_at_epoch_day"] = EPOCH_BASE + i * DONOR_INTERVAL_DAYS
        donors.append(d)
    return waitlist, donors
