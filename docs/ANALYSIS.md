# Analysis — verifiable deceased-donor kidney allocation

> Phase 5 write-up (metrics + synthesis). Every claim is cited to a decision
> ([`decisions.md`](decisions.md), `D-NNN`), the threat model ([`threat-model.md`](threat-model.md)),
> the evaluation ([`../evaluation/RESULTS.md`](../evaluation/RESULTS.md)), or the spec (`CLAUDE.md`).
> Tone is deliberately unembellished. **§4 is authored separately and left as a stub here.**

## 1. What this is

This is a verifiable-allocation prototype for deceased-donor kidney matching. An off-chain engine
computes a transparent, deterministic ranking — a Composite Allocation Score (CAS) modeled on OPTN
continuous distribution, using integer arithmetic only (D-004, D-017) — a permissioned smart contract
(`AuditLedger`) logs each decision, and an auditor-side verifier — implemented twice (Python
`engine/verifier.py` and JavaScript `web/src/verify.js`) and parity-locked byte-for-byte by frozen
cross-language vectors (D-018, D-021, D-023) — recomputes the ranking from the revealed inputs and
confirms it equals what was logged. The claim is
narrow and deliberate: **policy-faithful execution you can check, not trust** (D-003) — explicitly *not*
"decentralized trust" (CLAUDE.md §5). The motivation is India's documented allocation opacity (D-002, CLAUDE.md §1):
allocation is state-fragmented and inconsistent — Tamil Nadu runs a transparent public waitlist while
Delhi allocates hospital-wise, and several states prioritize government-hospital patients regardless of
medical urgency, all flagged as inequitable against THOTA's "medical criteria only" principle. The
well-documented Indian organ-trafficking cases (Gurgaon 2008, Apollo 2016, Bangladesh–India 2024)
sharpen the broader integrity concern, but they are *living-donor* relationship fraud; a *deceased-donor*
allocation ledger does not address them (D-002), so this project targets allocation **transparency**,
not trafficking.

## 2. What it proves (precise guarantees)

- **Policy-faithful execution.** The verifier independently recomputes the CAS from the revealed
  records and the versioned policy, and checks the ranking and its `ranking_hash` equal the logged
  decision (recompute-and-compare). The recompute is pinned across the two implementations by frozen
  cross-language vectors — for the salted commitments (D-004), the full CAS ranking (D-018), and the
  decision hash (D-009), which D-020 extended to also bind the candidate pool — which Python and JS
  reproduce byte-for-byte.
- **Tamper-evidence.** Each record is committed as a salted keccak256 fingerprint; editing a record
  *after* a decision is logged changes its commitment, so the verifier's binding check fails and
  verification reports the tampering. This is shown live in the UI (D-023): backdating a recipient's
  dialysis-start makes the edited record no longer open to its on-chain commitment, and Verify FAILS —
  locked by a unit test and a live end-to-end negative.
- **No silent exclusion.** The contract's `logDecision` requires the candidate pool to equal the full
  active registered recipient set (complete, strictly ascending, all active), so it **reverts an
  incomplete pool**; independently, the verifier reconstructs the active set from the on-chain
  registration/erasure events (block-aware) and checks `pool == active` and `revealed == pool` — so a
  registered recipient cannot be silently dropped from a decision (D-015, D-020). Proven by a Hardhat
  incomplete-pool rejection and a live negative; the Phase 3 adversarial review confirmed it "holds
  rigorously on-chain" (D-020).
- **Erasure-compatible privacy.** PII never goes on-chain (only salted commitments do) and is encrypted
  at rest (AES-256-GCM); erasing a record destroys its salt + ciphertext, after which the append-only
  on-chain commitment is permanently **unlinkable**. Implemented and unit-tested: erasing a record
  excludes it from `/reveal` and emits an on-chain `Erased` marker (D-020; §14; `api/store.py`). *(Documented tension, D-005:
  erasing a record also makes its past decisions unverifiable — auditable XOR erasable, per record.)*

## 3. What it does NOT prove (the honest boundaries)

- **Input truthfulness.** The chain proves the *computation* was faithful to the *committed inputs* — it
  does not prove the inputs are *true* (the oracle problem). A corrupt allocator entering a fabricated
  dialysis date / CPRA / HLA produces a commitment that faithfully reflects the lie, and verification
  passes. The mitigation is **organizational, not cryptographic**: the ledger records who attested what
  and when, making dishonest input *attributable* but not *preventable* (threat-model.md; CLAUDE.md §2,
  §10).
- **Registration-time completeness.** "No silent exclusion" (§2) covers dropping a *registered*
  candidate. An allocator who simply never registers someone is the same oracle-class problem and is out
  of scope (threat-model.md; D-015).
- **Public vs. authorized-auditor verification.** Verification needs the revealed records + salts, which
  are served only over the access-controlled `/reveal` endpoint (token-gated, D-022). So the honest
  claim is *"a designated auditor, given revealed data, can confirm policy-faithful execution"* — **not**
  "anyone can verify" (D-003). Verification that is public *and* reveals nothing requires zero-knowledge
  proofs (→ §7).
- **Policy fairness.** The evaluation (§5) reports relative trade-offs on synthetic data. It does not —
  and synthetic data cannot — establish real-world fairness (D-024).

## 4. What blockchain actually adds

*[author to write]*

## 5. What the evaluation shows (mechanism, not fairness)

Setup: a seeded synthetic waitlist of 400 recipients (India ABO/HLA/CPRA distributions) and a stream of
150 deceased donors, allocated under three policies — CAS (`kidney_v1`), naive FCFS (the *same* hard
gates, but ranked purely by waiting time, isolating the scoring effect), and CAS with the longevity
weight turned on. Reported as **mean ± std over 30 seeds** (± is seed-to-seed spread); these describe
*what the mechanism does*, not real-world fairness (D-024; RESULTS.md).

- **CAS roughly doubles access for the hardest-to-serve, at a cost to the median patient.** High-CPRA
  (sensitized) access rises from **36% ± 4 (FCFS) → 84% ± 5 (CAS)** and pediatric from **37% ± 5 → 86%
  ± 6**, paid for by lower low-CPRA (38% ± 1 → 22% ± 2) and adult (38% ± 1 → 26% ± 1) access. The error
  bars are small against the gaps, so this is robust, not a single-seed artifact. (Denominators of 400:
  high-CPRA 99 ± 11, pediatric 79 ± 9 — RESULTS.md.)
- **CAS does not fix — and slightly worsens — the blood-type-O disadvantage:** O access is **32% ± 3
  (FCFS) → 28% ± 3 (CAS)** vs non-O 41–43%. This is an ABO-compatibility effect (O recipients can only
  receive O kidneys), not a scoring choice, and it persists under both policies (RESULTS.md). (O ≈ 151 ±
  11 of 400 ≈ 38% of the pool, consistent with the synthetic India ABO frequency configured in
  `engine/data_gen.py` (O ≈ 37%).)
- **The weights are legible, tunable dials.** Sensitivity is monotonic: raising the CPRA weight 0→40
  lifts sensitized-patient access **0.34 ± 0.05 → 0.98 ± 0.02** (RESULTS.md).
- **Longevity weighting trades age for equity.** Turning it on drops mean transplant age **30.0 ± 1.9 →
  24.3 ± 2.1** (at weight 25), reaching **22.4 ± 1.7** at weight 40 — maximizing life-years disadvantages
  older patients, a documented tension, so it is weight-0 by default (RESULTS.md; weight-0 rationale per D-024).
- *Systems (illustrative, one machine):* ~407 allocations/s and ~2.8 ms to rank a 400-recipient
  waitlist; on-chain gas ≈ 91k (registerRecipient), 72k (logDecision, pool=5), 29k (eraseRecipient)
  (RESULTS.md).

## 6. How this compares to the field

The blockchain-organ-donation literature is prototype-only. The best critical survey (Calik &
Bendechache, MDPI *Blockchains*, 2024) reviewed 24 papers: **none reached real deployment**, 7/24 were
purely conceptual, there are no standard datasets or benchmarks, and most report only gas cost (CLAUDE.md
§15). Against that backdrop, this project's contribution is (a) a working, tested, *independently
verifiable* system; (b) a real multi-seed evaluation — 30 seeds, mean ± std, with an FCFS baseline (D-024; RESULTS.md) — the field's most-repeated
gap; and (c) explicit, honest scoping of what is and is not guaranteed (§2–§3). The decisions log
(D-001–D-025) records every real choice and its rationale; owning the oracle boundary and the
auditor-only limitation rather than over-claiming **is itself the contribution** (D-001, D-003;
CLAUDE.md §2).

## 7. Future work

- **ZK verify-without-revealing.** Proven feasible by a timeboxed Phase-1.5 spike, whose decision
  **D-016** and metrics live on the `spike/zk` branch (not in this main-branch log): a working zkVM proof
  that recomputes a canon-v1 commitment *in-circuit*, with spike-recorded figures of ~3-minute CPU proofs
  and a ~2.8 MB core proof; the on-chain groth16 wrap was not measured. This is the route to
  *public* verification that closes §3's auditor-only limitation (D-003).
- **Kidney paired exchange (KPD)** — selected as the Phase 6 capstone (D-025: chosen over the ZK option
  after the Phase-1.5 spike found ZK feasible but higher-risk; CLAUDE.md Phase 6 had left the choice
  open). It is an ILP over a compatibility graph (cycles + altruistic-donor chains, free solver), logged
  and verified the same way (CLAUDE.md Phase 6B).
- **Real consortium deployment.** A NOTTO + transplant-centres consortium chain is where the
  blockchain's distinctive value (BFT consensus among mutually-distrusting validators) is actually
  realized; the prototype is a single local node *simulating* that, so the consensus value is simulated,
  not demonstrated (threat-model.md).
- **Stronger oracle mitigations.** Multi-party attestation by independent hospitals/NOTTO to raise
  input-integrity beyond attributability (threat-model.md) — which the sources treat as the open oracle
  problem, not a solved one — and, as a proposal of this write-up, a registration-completeness mechanism
  for the never-registered gap (§3).
