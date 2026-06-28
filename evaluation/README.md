# Evaluation harness (Phase 5 — metrics)

Offline analysis over the matching engine: simulate deceased-donor allocation on a
synthetic waitlist and quantify the trade-offs each policy makes. The generated
numbers + charts live in [`RESULTS.md`](RESULTS.md).

> **Framing.** These describe **what the mechanism does** — not a proof of real-world
> fairness, which synthetic data cannot establish. The defensible signal is the
> *relative* shift CAS makes vs the first-come-first-served (FCFS) baseline.

## Reproduce
```bash
pip install -r requirements.txt
python -m evaluation.run                          # -> evaluation/RESULTS.md + out/*.png
cd contracts && npx hardhat run scripts/gas.js    # illustrative on-chain gas/op
python -m pytest evaluation/tests -q              # harness tests
```
Deterministic for the fixed config (400 recipients, 150 donors, seed 0).

## Modules
| file | role |
|---|---|
| `waitlist.py` | seeded synthetic waitlist (India ABO/HLA/CPRA, `engine/data_gen.py`) + donor stream |
| `policies.py` | the compared policies — CAS (`kidney_v1`), CAS+longevity, FCFS (same gates, waiting-time queue), `with_weights` |
| `simulate.py` | time-stepped allocation (each donor's kidney → rank #1, who leaves the waitlist) |
| `metrics.py` | subgroup access rates (CPRA / blood-type-O / pediatric), waiting/age/CPRA, comparison table |
| `sensitivity.py` | sweep a key CAS weight, watch a subgroup metric move |
| `systems.py` | throughput + per-match latency (illustrative) |
| `charts.py`, `run.py` | charts + `RESULTS.md` |

The write-up synthesis ("Limitations & What Blockchain Actually Adds") is a separate,
later step; this directory is the metrics half.
