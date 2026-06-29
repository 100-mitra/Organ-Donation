# Verifiable Organ Allocation — deceased-donor kidney matching

> A *verifiable-allocation* prototype for deceased-donor kidney matching. An off-chain engine ranks
> candidates by a transparent, deterministic policy (a Composite Allocation Score modeled on OPTN
> continuous distribution); a permissioned smart contract logs every decision immutably; and an
> auditor-side verifier — written twice (Python + JavaScript) and parity-locked byte-for-byte —
> **recomputes the ranking from the revealed inputs and confirms it faithfully executed the published
> policy**. The claim is narrow and deliberate: *policy-faithful execution you can check, not trust* —
> **not** "decentralized trust."

**Status: Phases 0–5 complete — the Minimum Shippable Project.** The full register → match → log →
recompute → verify loop runs end-to-end across all layers with the real CAS engine, an encrypted
off-chain PII store, a role-gated audit ledger that closes silent queue-jumping, a browser Verify page
with a live tamper demo, and a multi-seed evaluation. The honest write-up is in
[`docs/ANALYSIS.md`](docs/ANALYSIS.md); the full spec is [`CLAUDE.md`](CLAUDE.md) and the running
design-decision log is [`docs/decisions.md`](docs/decisions.md).

## What it proves — and what it does not

**Proves (process integrity):**

1. **Policy-faithful execution** — the verifier recomputes the CAS from the revealed records + the
   versioned policy and checks the ranking and its `ranking_hash` equal what was logged. The recompute
   is pinned across Python and JS by frozen cross-language vectors.
2. **Tamper-evidence** — editing any record after a decision is logged breaks its salted commitment, so
   Verify FAILS (shown live in the UI by backdating a record).
3. **No silent exclusion** — the contract requires the logged candidate pool to equal the full active
   registered set (so it reverts an incomplete pool), and the verifier independently reconstructs that
   set from the event log — a registered recipient cannot be silently dropped.
4. **Erasure-compatible privacy** — PII never goes on-chain (only salted commitments do) and is
   encrypted at rest; destroying a record's salt makes its on-chain commitment permanently unlinkable.

**Does NOT prove (the honest boundary):** it does not prove the *inputs* are true — the **oracle
problem**. A corrupt allocator entering fabricated data produces a commitment that faithfully reflects
the lie; the ledger makes that *attributable*, not *preventable*. And because verification needs the
revealed records (served over a token-gated endpoint), the honest claim is *"a designated auditor,
given revealed data, can verify"* — **not** "anyone can." Full detail and citations in
[`docs/ANALYSIS.md`](docs/ANALYSIS.md) and [`docs/threat-model.md`](docs/threat-model.md).

## The verifiable loop

1. **commit** — each record's salted commitment (`canon-v1`,
   [`docs/canonicalization.md`](docs/canonicalization.md)) is written on-chain. PII stays off-chain,
   encrypted.
2. **match** — the CAS engine applies the ABO + virtual-crossmatch gates, scores eligible candidates
   with integer arithmetic, and returns a deterministic ranking with a per-candidate explanation.
3. **log** — the decision (donor commitment, ordered ranked commitments, `rankingHash`, policy version,
   candidate pool) is logged as a role-gated on-chain event.
4. **recompute → compare** — an auditor re-ranks the *revealed* records with the same deterministic
   engine; the recomputed ranking + hash must equal what was logged. A tampered or subset pool fails.

The recompute exists in **two independent implementations** — Python ([`engine/`](engine/)) and
JavaScript ([`web/src/`](web/src/)) — both reproducing the same frozen vectors for commitments, the
full CAS ranking, and the decision hash.

## Evaluation (mechanism, not fairness)

Over a 400-recipient synthetic waitlist and 150 donors, **30 seeds**, mean ± std (full numbers,
denominators, and charts in [`evaluation/RESULTS.md`](evaluation/RESULTS.md)):

- CAS roughly doubles access for the hardest-to-serve vs first-come-first-served: high-CPRA
  (sensitized) **36% ± 4 → 84% ± 5**, pediatric **37% ± 5 → 86% ± 6** — paid for by lower adult /
  low-CPRA access.
- CAS does **not** fix — slightly worsens — the blood-type-O disadvantage (**32% ± 3 → 28% ± 3**); it is
  an ABO-compatibility effect, not a scoring choice.
- The weights are tunable dials (monotonic sensitivity), and turning on longevity weighting trades age
  for equity (mean transplant age **30 → 24**) — which is why it ships at weight 0 by default.

These describe *what the policy trades off* on synthetic data — **not** a proof of real-world fairness.

## Prerequisites

- Python 3.11+ (verified on 3.14), Node 18+ (verified on 24).

## Install

```bash
pip install -r requirements.txt
( cd contracts && npm install )
( cd web && npm install )
```

## Run the stack (4 terminals, or background)

```bash
# 1) local chain
cd contracts && npx hardhat node

# 2) deploy AuditLedger (writes deployments/localhost.json that the API reads)
cd contracts && npx hardhat run scripts/deploy.js --network localhost

# 3) API  (port 8010; the web app defaults to this — override with VITE_API_URL)
python -m uvicorn api.main:app --host 127.0.0.1 --port 8010

# 4) web UI
cd web && npm run dev        # open the printed URL: Register -> Match -> Verify
```

## Verify the loop is green (with the stack running)

```bash
bash scripts/check_e2e.sh        # Python recompute + the exact browser verify path (Node)
```

## Tests & evaluation

```bash
python -m pytest engine api evaluation -q   # engine + API + evaluation unit tests
( cd contracts && npx hardhat test )        # AuditLedger role-gating, pool-completeness, events
( cd web && npm test )                      # canon-v1 + CAS JS ports reproduce the frozen vectors
python -m evaluation.run                    # regenerate evaluation/RESULTS.md numbers + charts
```

## Read more

- [`docs/ANALYSIS.md`](docs/ANALYSIS.md) — the Phase 5 write-up: what it proves, the evaluation, the field, future work.
- [`evaluation/RESULTS.md`](evaluation/RESULTS.md) — full metrics (mean ± std, denominators, sensitivity, systems/gas).
- [`docs/threat-model.md`](docs/threat-model.md) — attacks stopped vs. not, the oracle boundary, privacy boundaries.
- [`docs/decisions.md`](docs/decisions.md) — every real design choice and why.
- [`CLAUDE.md`](CLAUDE.md) — the full project spec; [`docs/LATER.md`](docs/LATER.md) — deliberately parked scope.

## Scope & privacy

Synthetic data only — never real patient data. PII never goes on-chain; off-chain records are encrypted
at rest and `/reveal` is token-gated (`ALLOCATOR_TOKEN`) — it runs open *only* on synthetic data for the
demo and **must never be public in production**. This is a research/learning prototype on a single local
node *simulating* a NOTTO + hospitals consortium; it does not claim decentralization. Nothing here is
pulled from [`docs/LATER.md`](docs/LATER.md).
