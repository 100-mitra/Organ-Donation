# Decisions log

> A running record of every real choice and why — written continuously, not in a final-phase
> scramble (CLAUDE.md §4). The honesty this captures *is* part of the contribution. Newest at top.
> Format: `D-NNN` · date · status · context → decision → consequences.

---

## D-007 · 2026-06-27 · accepted — Build the verify loop first, with a trivial scorer
**Context.** The riskiest integration is not the CAS arithmetic; it is getting three independent
implementations (Python engine, Solidity ledger, JS browser verifier) to agree on *the same bytes →
the same hash*. **Decision.** The Phase 1 walking skeleton closes `commit → log → recompute → compare`
using a trivial 1-factor (waiting-time) scorer; real CAS lands in Phase 2 behind the same interface.
**Consequence.** A demoable, end-to-end-verifiable system exists before any scoring complexity is added.

## D-006 · 2026-06-27 · accepted — keccak256 via `eth-hash[pycryptodome]`; Python 3.14 verified
**Context.** Commitments must use Ethereum Keccak-256 (NOT NIST SHA3-256), and must match what the
Solidity contract and a JS verifier compute. Python stdlib `hashlib` has no keccak. **Decision.** Use
`eth-hash[pycryptodome]` (the same keccak web3.py uses). **Consequence.** Confirmed it installs and
reproduces `keccak256("") = c5d2460…a470` on Python 3.14.2. No homegrown hash (avoids the v1
anti-pattern, CLAUDE.md §3).

## D-005 · 2026-06-27 · accepted — Erasure XOR verifiability is an accepted, documented tension
**Context.** §14 proposes "destroy the salt + record" as the erasure mechanism. But a commitment can
only be reopened (and thus verified) with its salt. **Decision.** Treat *auditable* and *erasable*
as mutually exclusive per record after the fact, and document it rather than pretend it is solved.
**Consequence.** Honouring an erasure request knowingly makes that record's past decisions
unverifiable. This is a feature of honest design, surfaced in `canonicalization.md` and (later)
`threat-model.md`, and is a planned paper subsection. *(From critique #7.)*

## D-004 · 2026-06-27 · accepted — Canonicalization is a versioned interop contract with frozen vectors
**Context.** "Use integers" alone does not make a ranking verifiable — an *independent*
reimplementation must produce identical bytes. The real hazards are JSON canonicalization edge cases
and rating-function boundary/rounding rules. **Decision.** Pin a named scheme (`canon-v1`,
[`canonicalization.md`](canonicalization.md)) and lock it with cross-language frozen vectors
([`commitment_vectors.json`](../engine/tests/vectors/commitment_vectors.json)) that Python **and** the
JS verifier must reproduce. Forbid floats outright (sidesteps RFC 8785's hardest clause).
**Consequence.** "Verifiable" means "independently reproducible," not merely "self-consistent."
*(From critique #5.)*

## D-003 · 2026-06-27 · accepted — Headline-claim discipline: "auditor with revealed data," not "anyone"
**Context.** Verification needs the revealed records + salts, which only the allocator holds; on-chain
data alone is unopenable commitments. **Decision.** Phase 5's claim is *"a designated auditor, given
revealed data, can confirm policy-faithful execution"* — **not** "anyone can verify." The stronger
public-verifiability claim is true only under the ZK capstone (Phase 6A). **Consequence.** The paper's
headline must match what each phase actually ships; do not borrow Phase 6's rhetoric for Phase 5.
*(From critique #2.)*

## D-002 · 2026-06-27 · accepted — Lead with allocation transparency, not living-donor trafficking
**Context.** The trafficking cases (Gurgaon, Apollo, Bangladesh–India) are *living-donor* relationship
fraud; this system allocates *deceased-donor* kidneys and would not catch them. **Decision.** Lead the
motivation with allocation transparency/fragmentation (Tamil Nadu vs Delhi hospital-wise; medical-
criteria-only), which the mechanism genuinely addresses; demote trafficking to a clearly-labelled
adjacent note. **Consequence.** Motivation and mechanism stay aligned; removes the obvious reviewer
attack. *(From critique #1.)*

## D-001 · 2026-06-27 · accepted — Scope frozen: deceased-donor kidney only
**Context.** v1 failed by scope-ratcheting (it even shipped a leftover chatbot). **Decision.** Tier 1
(Phases 0–5) on deceased-donor kidney matching is the whole project; Phase 5 is the finish line.
Adding anything to the active plan requires parking something else in [`LATER.md`](LATER.md).
**Consequence.** A real finish line exists; default-to-cut is the standing rule.
