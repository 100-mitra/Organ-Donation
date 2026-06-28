# CLAUDE.md — Organ Donation & Transplantation Platform (v2)

> **One-line:** A *verifiable-allocation* platform for deceased-donor **kidney** matching. An
> off-chain engine computes a transparent, deterministic ranking using a Composite Allocation Score
> modeled on OPTN "continuous distribution"; a permissioned smart contract logs every decision
> immutably so anyone can independently recompute it and confirm the allocation **faithfully executed
> the published policy.**

This file is the **source of truth** for the project. It is intended to live at the repo root so
Claude Code reads it automatically. Read it fully before writing any code.

---

## 0. How to work on this project (read first)

- **Build strictly phase by phase** (see §11). Do **not** start a phase until the previous phase's
  *Definition of Done* genuinely passes (tests green).
- **Stay in scope.** Never add anything in §4 *Non-goals*. New ideas go into `docs/LATER.md`, never
  into the core.
- **Test as you build**, not after. Every phase ends with a green test suite.
- **PII never goes on-chain.** Only salted commitment hashes and decision logs do. This is a hard rule.
- **Determinism is sacred** (see §5, §10). The engine must be bit-for-bit reproducible or the whole
  verification thesis collapses.
- **Ask the maintainer before** changing the architecture, the allocation policy, or the scope.
- This is a solo, learning-focused rebuild. The maintainer writes code too — when asked to scaffold or
  unblock, produce small, clear, well-tested increments rather than large opaque dumps.

---

## 1. Context & motivation

India's organ allocation has a **documented, citable transparency problem** — which is the concrete
motivation for this project, not a generic "blockchain is good" pitch:

- Allocation is **state-fragmented and inconsistent**: Tamil Nadu runs a transparent, publicly visible
  state waitlist, while Delhi allocates **hospital-wise**; several states prioritize government-hospital
  patients regardless of medical urgency — all flagged as inequitable against THOTA's "medical criteria
  only" principle. (Indian J. Nephrology SWOT, 2024)
- Deceased-donation rate is **< 1 per million population (~0.8 PMP)** — roughly **50× below Spain** —
  and most transplants are living-donor, exposing the deceased-donor weakness. (NOTTO data; PIB 2024)
- **Trafficking is concrete, not hypothetical**: the Gurgaon kidney scandal (2008, ~600 illegal
  transplants) directly drove the 2011 THOTA amendment; the Indraprastha Apollo racket (2016); and the
  Bangladesh–India racket (2024) using forged donor-relationship documents.

This is a **v2 rebuild** of a published undergraduate project that conflated several unrelated goals
(it even contained a leftover medical chatbot). The goal now is to **finish a lean, correct,
well-evaluated core** and learn the concepts deeply. Success = closing the loop: a working, tested,
reproducible system that allocates kidneys by a transparent policy and lets a third party verify the
allocation step was executed honestly.

---

## 2. Core thesis & the precise claim (do not drift from this)

Blockchain's job here is **not** to store medical records. Its job is to be a **tamper-evident
enforcement and audit log of the allocation policy**.

> **"Don't trust that the ranking was computed honestly — recompute it and verify."**

**Scope the claim precisely (this is what separates this from weak prior work):**

- ✅ **What the system proves:** the logged allocation is *exactly* what the published, versioned policy
  produces for the committed inputs — no silent queue-jumping, no after-the-fact tampering with the
  ranking or the rules.
- ❌ **What it does NOT prove:** that the off-chain *inputs themselves* (blood type, HLA, dialysis date)
  are truthful. A ledger makes data tamper-evident *after entry* but cannot verify reality — the
  **oracle problem**. Input integrity is a governance question (who is authorized to attest data),
  handled in §10, **not** something the chain solves. State this limitation explicitly everywhere; it
  is the #1 critique of the entire field, and owning it is what makes the project credible.

**Novelty claim (keep it honest and narrow):** *verifiable, policy-faithful allocation* — modeled on
OPTN continuous distribution and applied to the Indian context. Not "blockchain for organ donation"
(done many times, weakly). There is no canonical "verifiable fair matching" system; the closest prior
art is verifiable sealed-bid auctions (§15).

---

## 3. Lessons from v1 — explicit anti-patterns (do NOT repeat)

- ❌ **No chatbot / disease-prediction / NLP anything.** The v1 paper had a leftover symptom-checker
  pasted in. Out of scope, unrelated.
- ❌ **No public Ethereum mainnet, and no PII on any chain.** Local permissioned chain; PII stays
  off-chain, encrypted.
- ❌ **No homegrown "hash generation" that ignores the previous hash**, and **no custom "mining" over
  SQL queries.** v1 mashed two incompatible designs together. Pick one coherent architecture (§5).
- ❌ **Don't invent arbitrary scoring.** v1's "intelligent allocation algorithm" was never defined.
  Model the policy on real allocation (OPTN continuous distribution / KAS) — see §9.
- ❌ **Don't overclaim.** The chain proves *process integrity*, not *truth* (oracle problem). Don't
  claim "decentralized trust" — this is a permissioned consortium simulation (§5).
- ❌ **Don't describe algorithms only in prose.** Everything ships as code + tests + measured results.

---

## 4. Scope — finish line first, then optional bonus ($0 budget)

The plan is shaped so you **finish early and can stop proud**, with ambition layered on top as
genuinely optional rounds. (This replaces the earlier "12-phase ladder," which had no real finish line
and let scope ratchet upward — the exact failure mode of v1.)

- **The project = Tier 1 (Phases 0–5).** Deceased-donor kidney matching (CAS) + audit ledger +
  verifiable recompute + privacy + UI + evaluation + honest writeup. **Phase 5 is the hard finish
  line: a "Minimum Shippable Project" you would be happy to present even if you build nothing else.**
- **Optional bonus = ONE capstone (Phase 6).** Pick *one* of: ZK verify-without-revealing, **or**
  kidney paired-exchange optimization — not both. The early ZK spike (Phase 1.5) tells you which.
- **Optional = ship & tell (Phase 7).** Free public deploy + polished paper.
- **Parked in `docs/LATER.md` (deliberately cut):** governance/consent module, cold-chain IoT
  simulation, multi-organ generalization, and the *second* capstone. Pull these in only if you still
  want more after Phase 7.

**Two disciplines that keep this finishable:**
1. **Default to cut.** Adding anything to the active plan requires removing or parking something else.
   The plan is allowed — encouraged — to *shrink*.
2. **Decisions log from day one** (`docs/decisions.md`): a running note of every real choice and why.
   Writing is continuous, not a final-phase scramble — and the honesty it captures *is* the contribution.

**$0-budget rule (hard constraint):** every component runs **locally or on a free tier**. Never
introduce a paid dependency. If a feature would otherwise need money or hardware (IoT sensors, cloud
GPUs, a commercial solver, real patient data), **simulate it** and say so (§6).

**True non-goals (still excluded):** real patient data; a production deployment with real
NOTTO/hospital organizations; anything requiring paid infrastructure or physical hardware.

---

## 5. Architecture

```
            ┌──────────────┐      register / match / audit      ┌──────────────────┐
   Browser  │   React UI   │  ───────────────────────────────▶  │  FastAPI backend │
            └──────────────┘                                    └───────┬──────────┘
                                                       run match │      │ store PII (encrypted)
                                                                 ▼      ▼
                                                     ┌────────────┐   ┌──────────────┐
                                                     │  Matching  │   │  Off-chain   │
                                                     │  engine    │   │  DB (SQLite) │
                                                     │  (Python)  │   └──────────────┘
                                                     └─────┬──────┘
                                          log decision +   │ write commitments
                                          policy version   ▼
                                                 ┌────────────────────┐
                                                 │  Solidity contract │  (local Hardhat chain)
                                                 │  AuditLedger       │  ← tamper-evident events
                                                 └────────────────────┘
```

- **Matching engine (Python, off-chain):** given an available kidney + the candidate pool, applies
  eligibility gates then the Composite Allocation Score (§9), and returns a **deterministic** ranked
  list with a per-candidate explanation. Pure logic, no blockchain dependency.
  - **Use integer / fixed-point arithmetic for all scoring** (e.g., points scaled to integers). Never
    floats — floating-point rounding differs across platforms and would make independent verification
    fail. This is a hard requirement, not a preference.
- **Off-chain store:** full PII in a local DB, encrypted at rest. Never leaves the backend.
- **On-chain contract (Solidity, local chain):** stores **commitments** (salted hashes) of records;
  logs each allocation **decision** as an immutable event; role-gated so only an authorized
  `allocator` can write.
- **Honest framing of "permissioned":** the prototype runs a **single local node**. It *simulates* what
  in production would be a **consortium chain governed by NOTTO + transplant centres** (the real-world
  governance model, and the one regulators favour — §14). Do not claim decentralization or
  "trustless"; claim *auditable, role-governed process integrity*. Note in the write-up that no
  blockchain organ-allocation system has reached real deployment (§15), so this is a prototype +
  simulation, stated plainly.
- **API (FastAPI):** orchestrates register → run-match → read-audit.
- **Web (React):** register, trigger a match, view the ranked result, and a public **Verify** page
  (§10).

---

## 6. Tech stack & versions (every item is free / open-source / local)

| Layer | Choice (all $0) |
|---|---|
| Matching engine / API | Python 3.11+, FastAPI, pytest, web3.py |
| Contracts | Solidity `^0.8.24`, Hardhat, ethers v6 |
| Web | React 18 + Vite (keep it minimal — polish is secondary) |
| Dev DB | SQLite (encrypted fields) |
| Chain | Local Hardhat node; **optional** Sepolia testnet via free faucet (Tier 3 "live" story only) |
| ZK proofs (Phase 6) | RISC Zero or SP1 **zkVM** (open-source; prove locally on your laptop), or Circom + snarkjs |
| Optimization (Phase 7) | OR-Tools / HiGHS / PuLP+CBC — **free/open solvers; NOT Gurobi** |
| Hosting (Phase 11) | Vercel / Netlify / GitHub Pages / Hugging Face Spaces (free tier) |
| Lint/format | ruff + black (Py), solhint + prettier (Sol/JS) |

**$0 reality check:** local chain = free; ZK proving runs on your CPU (slow, not paid); ILP solvers
above are fully free (avoid Gurobi/CPLEX, which are paid/academic-only); demo hosting and a testnet
faucet are free tiers. The only "cost" is your time and some compute/electricity.

**Why not Hyperledger Fabric:** real permissioned Fabric is the "production" answer but an ops swamp.
Access-controlled Solidity on a local chain teaches the same concepts (append-only, tamper-evident,
role-gated writes, policy-as-code) at a fraction of the setup risk. Note Fabric/consortium as the
production path in the write-up and move on.

---

## 7. Repo structure

```
.
├── CLAUDE.md                 # this file
├── docs/
│   ├── LATER.md              # parked ideas — NOT in current scope
│   ├── policy/kidney_v1.yaml # versioned CAS policy (rating scales, weights, gates)
│   ├── related-work.md       # §15 expanded, with citations (feeds a future paper)
│   └── threat-model.md
├── engine/                   # Python matching engine (pure logic)
│   ├── compatibility.py      # ABO + virtual crossmatch (hard gates)
│   ├── scoring.py            # CAS: rating functions × weights, integer arithmetic
│   ├── data_gen.py           # synthetic donor/recipient generator (India distributions)
│   ├── commitments.py        # canonical JSON + salted keccak256
│   └── tests/
├── contracts/                # Hardhat project
│   ├── contracts/AuditLedger.sol
│   ├── test/
│   └── scripts/
├── api/                      # FastAPI app (glue)
│   └── tests/
├── web/                      # React + Vite UI
└── scripts/                  # repo-wide dev scripts (run chain, seed, demo)
```

---

## 8. Data model

**Donor** (deceased): `id`, `abo`, `hla` {A:[...], B:[...], DR:[...]}, `age`, `kidney_size_proxy`,
`region`, `recovered_at`.

**Recipient**: `id`, `abo`, `hla`, `age`, `unacceptable_antigens` (virtual crossmatch),
`cPRA`, `dialysis_start_date`, `prior_living_donor` (bool), `region`, `urgency_flags`.

**MatchRun**: `donor_id`, `policy_version`, `timestamp`, `candidate_ids[]`.

**Decision**: ordered `ranked_recipient_commitments[]`, `donor_commitment`, `policy_version`,
`ranking_hash`, `allocator_address`, `timestamp`.

**On-chain vs off-chain split:**
- Off-chain (DB): all of the above, in full.
- On-chain (events only): `donor_commitment`, `ranked_recipient_commitments[]` (or `ranking_hash`),
  `policy_version`, `timestamp`, `allocator`.
- **Commitment** = `keccak256(canonical_json(record) || salt)`, with a per-record random `salt` stored
  off-chain. The salt both prevents on-chain enumeration of patients **and** is the erasure mechanism
  (§14): destroy the salt + off-chain record and the commitment becomes unlinkable.

---

## 9. Allocation policy v1 — Composite Allocation Score (`docs/policy/kidney_v1.yaml`)

**Model it on OPTN "continuous distribution"** (the real-world future of US allocation: a single
weighted composite score replacing rigid classifications). Do **not** invent ad-hoc points.

The policy is **versioned and configuration-driven**. The contract logs the `policy_version` used for
every decision, so a verifier always knows which rules to apply. All numbers below are **illustrative
starting defaults** — tunable, but any change bumps the version.

**Step A — eligibility hard gates (candidate excluded if any fails):**
1. **ABO compatibility** (donor → recipient): O → O,A,B,AB · A → A,AB · B → B,AB · AB → AB.
   *(ABO-identical-preferred, to protect O recipients, is a known fairness refinement — in `LATER.md`.)*
2. **Virtual crossmatch:** exclude if the donor expresses any of the recipient's `unacceptable_antigens`.
3. **Sanity:** size/age bands not absurd (configurable).

**Step B — Composite Allocation Score.** Each attribute has a **rating function** (maps the attribute
value → integer points) and a **weight**; `CAS = Σ (weight_i × rating_i)`, all integer arithmetic.
Higher CAS = higher priority. Attributes are grouped into the five OPTN continuous-distribution buckets
so the structure mirrors real policy and the write-up can cite it:

| Bucket (OPTN) | Attribute (kidney v1) | Rating direction | Default weight |
|---|---|---|---|
| Patient access | Waiting time **from dialysis start** (not listing date) | longer → more points | 30 |
| Patient access | Pediatric (recipient < 18) | yes → bonus | 15 |
| Patient access | Prior living donor (reciprocity) | yes → bonus | 15 |
| Candidate biology | Sensitization (CPRA) | higher CPRA → more points (steep at top) | 20 |
| Candidate biology | HLA match (A/B/DR, 0–6 mismatches) | fewer mismatches → more points | 15 |
| Placement efficiency | Proximity (same region / ischemia time) | closer → more points | 5 |
| Post-transplant survival | EPTS-style longevity match | *defined, default weight 0* (see note) | 0 |
| Medical urgency | (minimal for kidney; most candidates are on dialysis) | — | 0 |

> **Critical/ethical note on longevity matching:** "post-transplant survival" (EPTS-style) maximizes
> life-years but can systematically disadvantage older or sicker patients — a real equity tension. It
> is **defined but weight-0 by default** in v1 so the model is honest and complete without baking in
> that bias; turning it on is a documented policy choice (and a great thing to *evaluate*, §11).

**Step C — determinism & tie-breaking (required for verifiability):**
- Integer/fixed-point only; no floats; no wall-clock or RNG inside scoring.
- Canonical JSON serialization (sorted keys, fixed number formats, UTF-8) is the **single source of
  truth** for both commitments and scoring — specify it once and reuse it.
- Tie-break deterministically: (1) longer waiting time, then (2) a seed derived from
  `keccak(decision_id || recipient_id)`. Same inputs + same policy version → identical ranking, always.
- Output: the ranked list **plus a human-readable explanation per candidate** (gates passed, per-bucket
  point breakdown).

---

## 10. Verifiable-allocation mechanism

**v1 (lean — build this): recompute-and-compare.**
1. At registration, each record's salted **commitment** is written on-chain.
2. At allocation, the engine produces a ranking; the **decision** (commitments + `policy_version` +
   `ranking_hash`) is logged on-chain.
3. To verify, an auditor takes the on-chain decision, the published `kidney_v{n}.yaml`, and the revealed
   records+salts, **recomputes** the ranking with the same deterministic engine, and checks it equals
   what was logged. The public **Verify** page does exactly this in the browser.

**v2 (Phase 6 stretch, genuinely novel): prove it in zero-knowledge.** A zk proof that "this ranking is
correct under policy vN" *without* revealing the medical inputs. Realistic route is a **zkVM (RISC Zero
/ SP1)**, not hand-written Circom — per the 2025 zk-SNARK SoK, ~90% of ZK bugs are circuit-level and
hashing inside a circuit is very expensive. Closest precedent: verifiable sealed-bid auctions (§15).

**Trust model — state it explicitly (this is the oracle boundary from §2):**
- The mechanism guarantees **policy-faithful execution**, i.e. integrity of the *computation*.
- It does **not** guarantee input truthfulness. Mitigate that *organizationally*: inputs are attested
  by an authorized, identified `allocator` role (a hospital/NOTTO actor); the chain records **who**
  attested **what** and **when**, so dishonest input becomes *attributable* even though it can't be
  prevented cryptographically. Document this in `docs/threat-model.md`: which attacks you stop
  (ranking tampering, queue-jumping, rule-swapping, repudiation) vs. which you don't (a corrupt
  allocator entering false data).

---

## 11. Roadmap & Definition of Done

> **Finish line first.** Phases 0–5 are the whole project; **Phase 5 is a hard stop — a "Minimum
> Shippable Project" you'd be proud to present even if you build nothing more.** Phases 6–7 are
> optional bonus. Build in order; every phase ends green with its DoD met.

### Tier 1 — the project (your real finish line)

- **Phase 0 — Foundations.** Freeze scope (kidney only), finalize §8 model + §9 CAS policy v1; set up
  repo, dev env, CI; start `docs/decisions.md` and `docs/LATER.md`. **DoD:** scaffold builds, CI green,
  decisions log exists.
- **Phase 1 — Walking skeleton (thin end-to-end slice).** The skinniest possible pipeline wired across
  *all* layers: register → trivial 1-factor ranking → commit + log decision on the local chain →
  recompute-verify, with a bare UI. Stub/hardcode everything non-essential. **DoD:** the whole pipeline
  runs end-to-end and the Verify step passes — a demoable system in week one, even though the ranking
  is trivial.
- **Phase 1.5 — ZK feasibility spike (timeboxed, ~1–2 days).** Prove a *trivial* 5-candidate ranking in
  a zkVM (RISC Zero/SP1). De-risks the flagship **before** you sink effort into it, and decides your
  Phase 6 capstone. **DoD:** either a working toy proof, or a written "too costly — here's why" in
  `decisions.md`. Both outcomes are wins.
- **Phase 2 — Real matching engine (CAS).** Replace the trivial ranking with the full
  continuous-distribution CAS: synthetic data (India ABO/HLA distributions), ABO + virtual-crossmatch
  gates, integer scoring, deterministic tie-breaks, per-candidate explanations, unit tests. **DoD:**
  given a donor, outputs a correct, explainable, **reproducible** ranking; tests pass.
- **Phase 3 — Real audit ledger + privacy.** Flesh out `AuditLedger.sol` (roles, decision events, full
  commitments) and the off-chain side (encrypted PII store, salted commitments). Hardhat + API tests.
  **DoD:** register writes a commitment on-chain with PII stored off-chain; a real decision is logged
  and the full tamper-evident trail reads back.
- **Phase 4 — Web UI + public Verify page.** Register, match, view the ranked result, and a **Verify**
  page that recomputes the ranking from on-chain data and confirms it matches. **DoD:** a non-technical
  person can drive the whole flow in a browser.
- **Phase 5 — Evaluate, harden, document (the finish line).** The field's most-repeated failure is *no
  real evaluation* (§15). Beat it:
  - Simulate a realistic waitlist; report **fairness metrics**: access for highly sensitized (high-CPRA)
    patients, blood-type-O disadvantage, waiting-time equity, pediatric outcomes.
  - **Baseline comparison:** your CAS vs. naive first-come-first-served (and CAS with longevity weight
    on/off) — quantify the equity effect.
  - **Systems metrics:** throughput, latency, gas/op.
  - **Threat model** (§10) + reproducible README + the **"Limitations & What Blockchain Actually Adds"**
    writeup. **DoD:** results documented; repo reproduces from a fresh clone; an independent Verify run
    passes.

> ### ★ MINIMUM SHIPPABLE PROJECT — you are DONE here, and may stop, proud. ★
> Everything below is optional bonus. Pick **at most one** capstone. Default to *cut*: adding anything
> requires parking something else (`docs/LATER.md`).

### Tier 2 — optional capstone (choose ONE, only after Phase 5 ships)

- **Phase 6 — Capstone (pick exactly one):**
  - **(A) ZK verify-without-revealing** — *if the Phase 1.5 spike was promising.* A zkVM proof that the
    full ranking is correct under policy vN **without exposing any medical inputs** — resolves the
    privacy↔verifiability tension (§10). The flagship novelty; higher risk.
  - **(B) Kidney paired exchange (KPD)** — ILP over a compatibility graph (cycles + altruistic-donor
    chains; free solver OR-Tools/HiGHS/PuLP+CBC), logged + verifiable. Self-contained, lower-risk,
    equally impressive; legal in India under THOTA.
  - *Recommendation:* let the spike decide — if ZK felt tractable and fun, do (A); otherwise (B) is the
    higher-certainty choice. The other becomes "future work," **not** a second capstone.

### Tier 3 — ship & tell (optional)

- **Phase 7 — Deploy & publish.** Free hosting (Vercel/Netlify/HF Spaces); optional Sepolia testnet
  deploy (free faucet) for a "live" story; polish the honest paper (§2, §10, §15). **DoD:** a stranger
  can open the live demo, run the Verify flow, and read a reproducible writeup.

**Parked in `docs/LATER.md` (deliberately cut from the main line):** governance/consent module,
cold-chain IoT simulation, multi-organ generalization, and the *second* capstone. Pick up only if you
still want more after Phase 7.

---

## 12. Working agreement / conventions

- **TDD-ish:** write or update tests with every change; each phase ends green.
- **Small commits**, conventional-commit style (`feat:`, `fix:`, `test:`, `docs:`).
- **No scope creep:** anything in §4 *Non-goals* is rejected and logged in `docs/LATER.md`.
- **Determinism is sacred** in the engine — integer math, canonical serialization, no hidden
  randomness, no wall-clock in scoring.
- **Synthetic data only.** Never use real patient data.

---

## 13. Domain glossary

- **ABO** — blood-group compatibility; first hard gate.
- **HLA** — tissue-typing antigens (A/B/DR here); fewer mismatches = better graft survival.
- **CPRA** — calculated panel-reactive antibody; how sensitized/hard-to-match a recipient is.
- **Virtual crossmatch** — checking a donor against a recipient's *unacceptable antigens*.
- **Cold ischemia time** — hours an organ survives outside the body (kidney ~24–36h → forgiving
  logistics; why kidney is the v1 choice).
- **Continuous distribution / Composite Allocation Score (CAS)** — OPTN's model replacing rigid
  classifications with one weighted composite score across attribute buckets (lung live 2023; kidney in
  progress). The template for §9.
- **KDPI / EPTS** — real donor-quality / recipient-survival indices used for longevity matching
  (inspiration; EPTS-style attribute is weight-0 by default in v1).
- **Oracle problem** — a blockchain cannot verify the truth of real-world data fed into it; it only
  secures data *after* entry. The boundary of this project's guarantee (§2, §10).
- **NOTTO / ROTTO / SOTTO** — India's national/regional/state transplant organizations; the real
  governance hierarchy this models. Legal basis: **THOTA** (Transplantation of Human Organs and Tissues
  Act, 1994; amended 2011; Rules 2014).
- **Commitment** — salted hash of a record stored on-chain to enable verification without exposing PII.
- **Allocator** — the only role authorized to attest data and write decisions to the ledger.

---

## 14. Legal & ethical notes (privacy design, with citations)

The off-chain-PII + on-chain-commitment design is **required** by data-protection law, and the research
sharpens exactly why:

- **Immutability vs. erasure.** GDPR Art. 17, HIPAA's amendment right (45 CFR 164.526), and **India's
  DPDP Act 2023 §12** (right to correction/erasure) all conflict with an append-only ledger. The
  **EDPB Guidelines 02/2025** are blunt: *"technical impossibility is not a justification"* for denying
  data-subject rights — you must design for erasure **up front**.
- **A hash of personal data is still personal data.** Per EDPB pseudonymisation guidance and the EU
  STOA report, salted/keyed hashes are *pseudonymisation, not anonymisation*. Implication: even the
  on-chain commitment is personal data **until the salt is destroyed** — so commitments stay on the
  **permissioned** chain (not world-readable), and the **erasure mechanism is destroying the off-chain
  salt + record**, after which the commitment is unlinkable. This is the compliance linchpin; make sure
  salts are individually destroyable.
- **Permissioned governance is the legally-favoured model.** CNIL (2018) holds that private/permissioned
  chains "do not raise specific issues" and have an identifiable controller — reinforcing the §5 framing
  of a NOTTO + hospitals consortium.
- **Do NOT use chameleon-hash / redactable chains** for the core: legally unproven and they erode the
  immutability that justifies using a ledger at all. Mention as an alternative only.
- This is a **research/learning prototype on synthetic data**, modeling — not replacing — the
  authority-governed real system (NOTTO). Not a medical device; makes no clinical claims.

---

## 15. Related work & design justification (feeds a future paper — see `docs/related-work.md`)

- **The field is thin and weak — your opening.** The best critical survey (Calik & Bendechache, MDPI
  *Blockchains*, 2024) reviewed 24 blockchain-organ-transplant papers: **none reached real deployment**,
  7/24 were purely conceptual, there are **no standard datasets/benchmarks**, and most report only gas
  cost. This is why rigorous evaluation (Phase 5) and honest scoping put you near the top of the field.
- **The canonical prototype** is literally v1's reference [1]: Hawashin, Jayaraman, Salah, Yaqoob et al.,
  *IEEE Access* 2022 — private Ethereum, 6 smart contracts, 6 algorithms, code on GitHub. Acknowledge
  it did more than v1 and position against it.
- **Allocation realism:** OPTN continuous distribution (the CAS model, §9), KAS rules (dialysis-start
  waiting time, CPRA priority, HLA, pediatric, proximity), KDPI/EPTS longevity matching.
- **Verifiable-allocation prior art:** verifiable sealed-bid auctions (Galal & Youssef, ESORICS 2018;
  zk-STARK auctions 2024) are the closest precedent; Health-zkIDM (*Sensors* 2022) shows off-chain
  compute + on-chain verification in healthcare. No canonical "verifiable fair matching" exists → the
  gap you occupy.
- **Privacy/compliance:** EDPB 02/2025; CNIL 2018; DPDP Act 2023 §12 (§14).
- **Kidney paired exchange (Phase 6):** Roth, Sönmez & Ünver (QJE 2004; Nobel 2012); Abraham, Blum &
  Sandholm (EC-2007, NP-hardness + branch-and-price ILP); long chains (Ashlagi et al.; PNAS 2015).

**Key reference URLs** (full list in `docs/related-work.md`):
Calik & Bendechache survey — https://www.mdpi.com/2813-5288/2/2/8 ·
Hawashin et al. IEEE Access 2022 — https://ieeexplore.ieee.org/document/9787401/ ·
OPTN Continuous Distribution — https://www.hrsa.gov/optn/policies-bylaws/policy-issues/continuous-distribution ·
Roth/Sönmez/Ünver, Kidney Exchange (QJE 2004) — https://academic.oup.com/qje/article-abstract/119/2/457/1894508 ·
Galal & Youssef, verifiable sealed-bid auction (2018) — https://eprint.iacr.org/2018/704.pdf ·
EDPB Guidelines 02/2025 on blockchain — https://www.edpb.europa.eu/system/files/2025-04/edpb_guidelines_202502_blockchain_en.pdf ·
India transplant SWOT (Indian J. Nephrology 2024) — https://indianjnephrol.org/from-policy-to-practice-a-swot-analysis-of-indias-organ-transplantation-regulatory-framework/
