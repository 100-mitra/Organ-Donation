# Decisions log

> A running record of every real choice and why — written continuously, not in a final-phase
> scramble (CLAUDE.md §4). The honesty this captures *is* part of the contribution. Newest at top.
> Format: `D-NNN` · date · status · context → decision → consequences.

---

## D-025 · 2026-06-28 · accepted — Phase 6 capstone = kidney paired exchange (KPD), not ZK
**Context.** Phase 6 is an *optional* single capstone — "pick exactly one" of (A) ZK
verify-without-revealing or (B) kidney paired exchange, never both, with the choice deferred to the
Phase 1.5 ZK feasibility spike (CLAUDE.md §4, §11; default-to-cut, [[d-001]]). The spike ([[d-016]],
recorded on branch `spike/zk`) found ZK *feasible* — a zkVM proof recomputes a canon-v1 commitment
in-circuit — but costly and higher-risk: ~3-minute CPU proofs with the on-chain (groth16) wrap left
unmeasured, so public, reveal-free verification is not yet proven end-to-end. **Decision.** Choose
**(B) KPD** as the one Phase 6 capstone: an ILP over a compatibility graph (2-/3-cycles + altruistic-donor
chains) on a free solver (OR-Tools/HiGHS/PuLP+CBC), logged + verifiable by the same recompute-and-compare
path; legal in India under THOTA. **(A) ZK becomes documented future work, not a second capstone** — the
higher-certainty option wins, per CLAUDE.md's own "let the spike decide; otherwise (B)" guidance.
**Consequence.** Phase 6 scope is fixed to KPD; ZK verify-without-revealing is parked as future work
(it would make verification *public*, closing the auditor-only limitation [[d-003]]). This entry is the
source for the "chosen capstone" claim in the Phase 5 write-up ([`ANALYSIS.md`](ANALYSIS.md) §7). The KPD
build has not started — this records the *choice*, not its implementation.

## D-024 · 2026-06-28 · accepted — Phase 5 evaluation: framing + simulation design + reproducibility
**Context.** The evaluation must quantify the policy's behaviour without over-claiming fairness on
synthetic data. **Decisions.** (1) **Framing:** report "**what the mechanism does**" — the relative
trade-offs vs the FCFS baseline — explicitly NOT a proof of real-world fairness (synthetic data can't
establish that). (2) **Simulation:** a fixed seeded waitlist (~hundreds, India ABO/HLA/CPRA via
`engine/data_gen`) + a deceased-donor stream arriving over time; each donor's kidney goes to rank #1, who
leaves the waitlist — deterministic, no RNG in the sim. (3) **FCFS baseline = same hard gates, ranked
purely by waiting time** (so the comparison isolates the *scoring* effect, not the gates). (4) **Longevity
variant** = `kidney_v1` with the (default-0) `longevity_epts` weight turned on, to surface the age/equity
tension. (5) **Reproducibility:** the equity + sensitivity numbers and the charts are byte-deterministic
(seeded); the systems *timing* (throughput/latency) is illustrative + machine-dependent, and gas/op is
measured separately by `scripts/gas.js`. (6) `matplotlib`/`numpy` are eval-only deps. **Consequence.**
Defensible relative findings: CAS lifts high-CPRA access ~35%→71% and pediatric ~38%→83% (cost: low-CPRA
/adult); the blood-type-O disadvantage persists in both (ABO, not scoring); longevity-on drops mean
transplant age ~30→22. Numbers + charts in [`../evaluation/RESULTS.md`](../evaluation/RESULTS.md).

## D-023 · 2026-06-28 · accepted — Phase 4 UI: Verify reuses the lockstep verifier; tamper demo is the centerpiece
**Context.** The web UI must let a non-technical person drive register → match → view explanations →
verify, with verification as the centerpiece. **Decisions.** (1) The Verify panel calls the EXISTING
`web/src/verify.js` (which uses `cas.js`/`canon.js`) — verification logic is NOT reimplemented in the UI,
so the browser path stays byte-for-byte in lockstep with the engine and the frozen vectors keep covering
it. (2) The centerpiece is a visible **tamper demo**: the UI backdates a revealed record's dialysis-start
*after* the decision was logged; the edited record no longer opens to its on-chain commitment, so Verify
FAILS — making tamper-evidence tangible. Locked by a vitest unit test + a live N4 negative. (3) The Verify
tab is framed as the **authorized-auditor** flow over the token-gated `/reveal` ([[d-022]]); an optional
token field carries `Authorization: Bearer` for the gated endpoints (demo-open on synthetic data).
(4) No engine/contract/API change — Phase 4 is purely a thin `web/` layer over the existing endpoints.
**Consequence.** A browser-drivable end-to-end flow whose verification is the same trusted code path the
tests pin, with tampering shown failing live.

## D-022 · 2026-06-28 · accepted — /reveal is an intentional, access-controlled PII disclosure
**Context.** The verifiable-recompute model *requires* an authorized auditor to obtain records + salts
to recompute (CLAUDE.md §10, [[d-003]]); but the encrypted-at-rest store is undone if `/reveal` hands
plaintext to anyone. (Phase 3 adversarial review, confirmed.) **Decision.** `/reveal` (and the allocator
write endpoints) are gated by an `ALLOCATOR_TOKEN` (`Authorization: Bearer`); unset = demo mode, open on
**synthetic data only**; set = enforced (401 otherwise). Documented in [`threat-model.md`](threat-model.md)
as a deliberate, gated disclosure that **must never be public in production** (and CORS narrowed there).
**Consequence.** The privacy story is coherent: encrypted at rest + disclosed only to an authorized
auditor. Full production auth/identity + CORS hardening remains a deployment concern (LATER.md).

## D-021 · 2026-06-28 · accepted — verifier requires the fetched policy (no silent disk fallback)
**Context.** The Phase 3 review found a Python↔JS divergence: with `policy=None`, the Python verifier
silently loaded the policy from local disk and passed, while the JS verifier (no filesystem) skipped the
recompute and failed — opposite verdicts on identical input, breaking lockstep. **Decision.** Drop the
Python disk fallback; **both** ports require the policy to be passed in (the auditor fetches it via
`/policy`, exactly as the browser does), so they prove the SAME policy bytes were used and behave
identically on `policy=None` (recompute fails). `scripts/e2e.py` now fetches `/policy`. **Consequence.**
Byte-for-byte lockstep restored; the auditor recomputes against the decision's policy, not local disk.
*(Standing rule [[d-004]].)*

## D-020 · 2026-06-28 · accepted — Phase 3 real ledger: pool-completeness, encrypted store, erasure
**Context.** The real audit ledger had to close the carried-forward subset-drop gap and add privacy.
**Decisions.** (1) **AuditLedger** gained a recipient/donor registration lifecycle + per-recipient
erasure, and `logDecision` ENFORCES `candidatePool == active recipient set` (length == count + strictly
ascending + all active) — so a registered recipient cannot be dropped from a decision (closes D-015
on-chain). (2) The verifier (both ports) **independently reconstructs** the active set from the
registration/erasure events (block-aware) and checks `pool == active` + `revealed == pool`, not trusting
the contract. (3) `ranking_hash` now binds the pool (frozen `decision_hash_vectors.json`, both ports).
(4) Off-chain PII is **encrypted at rest** (AES-256-GCM); `erase()` destroys salt+ciphertext →
commitment unlinkable (§14). (5) `/seed` resets the on-chain active set so each match's pool is exact;
old decisions still verify (block-aware reconstruction). **Consequence.** Subset-drop is genuinely
closed (contract + independent verifier), parity preserved, privacy added — confirmed by the Phase 3
adversarial review ("holds rigorously on-chain"; crypto core "sound").

## D-019 · 2026-06-28 · accepted — boolean_bonus uses STRICT identity (Python/JS truthiness divergence)
**Context.** The Phase 2 adversarial review found a real cross-language parity bug: `extract_features`
coerced `prior_living_donor`/`urgent` with Python `bool()` / JS `Boolean()`, which **disagree on empty
containers** — `bool([])` is `False` (0 pts) but `Boolean([])` is `true` (100 pts). A record with
`prior_living_donor=[]` (accepted by the `dict[str, Any]` API and canon-v1 valid) gets an *identical
commitment* in both languages but a **1500-point CAS swing** (weight 15), so the browser verifier would
disagree with the logged ranking — the exact divergence the thesis forbids; the three original vectors
(literal true/false) never caught it. **Decision.** `boolean_bonus` now uses **strict identity**
(`value is True` / `value === true`) so only a literal `True` earns the bonus and both engines agree for
*every* input; `extract_features` passes the raw value through. Added a `boolean_strictness` frozen
vector (`[]`/`{}` → treated as false) that both ports must reproduce. **Consequence.** Parity restored
and locked; a malformed boolean is a deterministic "no bonus" in both languages rather than a silent
divergence. *(From Phase 2 review; standing rule [[d-004]].)*

## D-018 · 2026-06-28 · accepted — CAS ranking is byte-for-byte parity-locked across Python and JS
**Context.** The verifiability thesis needs the CAS recompute to be identical in the engine and the
browser, the same way commitments were locked (D-004/D-011). **Decision.** `web/src/cas.js` is the JS
twin of `engine/scoring.py` + `compatibility.py` (integer arithmetic; `Math.floor` for the one integer
division; keccak tie-break via the shared canon-v1 keccak). Frozen `cas_ranking_vectors.json` fixes
three cases — the demo pool (with gated candidates), an 8-candidate synthetic pool, and a pure
keccak-tie case (three identical-CAS recipients) — recording each candidate's eligibility + CAS +
per-attribute points + the eligible ranking. Both `engine/tests/test_cas_vectors.py` and
`web/src/cas.test.js` must reproduce every case; the browser fetches the policy via a new `/policy`
endpoint so it interprets the same JSON the engine loads. **Consequence.** Python and JS agreed on every
vector on the first run — including the keccak tie-break order — so "verifiable" means independently
reproducible for the full CAS, not just commitments. Standing rule: on divergence, fix the spec, not one
language ([[d-004]]).

## D-017 · 2026-06-28 · accepted — Phase 2 CAS: derived inputs, tie-break seed, policy-as-JSON, eligible-coverage
**Context.** Replacing the trivial ranking with the full integer CAS forced several determinism choices
that the verifier (Python + JS) must reproduce identically. **Decisions.**
1. **waiting_days is derived, not stored:** `waiting_days = donor.recovered_at_epoch_day −
   recipient.dialysis_start_epoch_day` (clamped ≥0). Both values live in the committed records, so the
   verifier needs **no external "as-of" date and no contract change** — a registration-time `waiting_days`
   snapshot would be wrong (waiting accrues) and an external as-of would need logging.
2. **Tie-break seed = `keccak256(donor_commitment ‖ recipient_id)`.** The policy's `keccak_seed` tie-break
   needs a decision id known to the verifier; the donor commitment is on-chain and unique per match, so it
   is the seed. Reuses canon-v1 keccak (already in both languages).
3. **Policy ships as derived JSON.** `kidney_v1.yaml` stays the human source; `scripts/gen_policy_json.py`
   derives `kidney_v1.json`, which **both** the Python engine and the JS verifier load, so they interpret
   byte-identical rules. `test_policy.py` asserts JSON==YAML. Added `region_zones` to the policy (proximity
   needs it; anything affecting the score must be in the versioned config). No version bump — kidney_v1 was
   never logged on-chain (Phase 1 used `skeleton-waiting-time-v0`), so this completes v1 rather than changing it.
4. **Gates change coverage:** the ranked set is the **eligible** recipients only, so the verifier's coverage
   check becomes "ranked set == eligible(revealed recipients)" (recompute eligibility, not all-revealed).
**Consequence.** The CAS ranking is fully recomputable from the committed records + policy, by an
independent reimplementation, with integer-only arithmetic. JS parity is enforced by frozen CAS vectors (next).

## D-015 · 2026-06-28 · RESOLVED (2026-06-28) — kind-mislabel FIXED (Phase 1); subset-drop CLOSED (Phase 3)
**Context.** Re-running the adversarial workflow on the D-013 fix confirmed the binding closes the
*fabrication/substitution* attack (a revealed record never Registered is rejected — proven by N2), but
it only enforces **revealed ⊆ registered**, not coverage. Two residual attacks were found:
- **[HIGH] kind-mislabel — RESOLVED (2026-06-28).** A registered+revealed recipient tagged with a bogus
  `kind` (or relabelled as a second donor) passed the binding loop but was filtered out of the re-rank,
  hiding it from the ranking. **Fixed verifier-side, no contract change** (maintainer chose this): both
  verifiers now (1) reject any unrecognized `kind`, (2) require exactly one donor matching the on-chain
  donor commitment, and (3) assert the ranked set equals the revealed-recipient set (coverage). Closed
  by isolating unit tests in both languages.
- **[CRITICAL] subset-drop — OPEN, deferred to Phase 3.** A dishonest server reveals only a *subset* of
  the registered pool and logs a decision over that subset; binding + re-rank + hash all pass → a
  top-priority registered recipient is silently dropped (the "no silent queue-jumping" guarantee, §2).
  **Why deferred:** a correct fix needs the verifier to know the *decision's candidate pool*, but the
  on-chain `Registered` set is **global and accumulates across every /seed** (new salts each time), so a
  naive "registered minus donor == ranked" check false-positives after repeated seeds. A correct fix
  needs registration scoped per match-run — a registration-epoch notion or logging the pool in the
  decision (a **contract change**, beyond the "AuditLedger unchanged" constraint). Tracked for Phase 3
  ("real audit ledger"), where persistent, scoped registration lands.
**Status.** kind-mislabel resolved (Phase 1). **subset-drop CLOSED in Phase 3 ([[d-020]]):** the contract
enforces `candidatePool == active recipient set` and the verifier independently reconstructs that set from
the event log — a registered recipient can no longer be silently dropped. The Phase 3 adversarial review
confirmed it "holds rigorously on-chain." Proven by the Hardhat incomplete-pool rejection + live e2e N3
(contract) + the verifier completeness check (both languages). *(Originated in re-verification of D-013.)*

## D-014 · 2026-06-28 · accepted — canon-v1 integer/float hardening + frozen-vector matrix
**Context.** Adversarial review found two latent Python↔JS divergences the single frozen vector never
exercised: integers > 2^53 (Python keeps precision, JS rounds the double) and the `2.0`/`2` asymmetry
(Python rejects the float type, JS can't see it). **Decision.** (1) Bound canon-v1 integers to the JS
safe range `±(2^53-1)`; both ports reject out-of-range (encode bigger values as strings). (2) Keep
Python's strict float-*type* rejection; document that JS validates by *value* (`Number.isSafeInteger`)
— an input-validation asymmetry with **no output divergence** (every jointly-accepted value
canonicalizes identically). (3) Expand frozen vectors from 1 to **7** (large/negative ints, key
ordering, unicode incl. emoji, nested empties, scalars, deep nesting). **Kept the label `canon-v1`**:
no previously-valid input's serialization changed (the R001 commitment is byte-identical), so no
on-chain data is invalidated and no version bump is warranted — this corrects an under-specification
rather than redefining the format. **Consequence.** Python and JS now reproduce the full matrix
byte-for-byte; the determinism foundation is pinned by tests, not merely asserted. *(From critique #5 /
review Group B.)*

## D-013 · 2026-06-28 · RESOLVED (2026-06-28) — Phase 1 verifier now binds /reveal to on-chain registrations
**Resolution.** Fixed in Phase 1 scope, no contract change: both verifiers now read the on-chain
`Registered` set (`/commitments`) and require every revealed record to open to a commitment that was
actually registered *before* re-ranking — so a substituted/fabricated pool is rejected. Proven by an
isolating unit test (ranking passes, binding fails) and a live N2 negative in both languages. This is
§8/§10 spec-conformance, not new scope. *(Residual, genuinely deferred: binding the FULL candidate set
— i.e. detecting a registered recipient silently omitted from a decision — needs the decision to commit
to its pool on-chain, a contract change, so it stays a later-phase item.)*

**Context.** An adversarial review of the green Phase 1 loop confirmed a soundness gap: the verifier
recomputes from whatever `/reveal` returns and never cross-checks it against the on-chain `Registered`
commitments, so a dishonest allocator could reveal a different pool than it committed and still PASS
(plus sibling cases: dropped candidate, omitted recipient, duplicate ids). **Decision (provisional).**
Phase 1 ships at its DoD with this documented as a KNOWN LIMITATION; whether to harden now (read
`Registered` events + set-equality/permutation/uniqueness checks — no contract change) or carry it into
Phase 3 ("real audit ledger + privacy") is a maintainer call. **Consequence.** The Phase 1 verifiability
demo is honest only for the *cooperative* path; the strong "verify the allocation was faithful" claim
should not be made until this binding exists. Full write-up + recommended fix in
[`MORNING_REPORT.md`](MORNING_REPORT.md). Status stays **open** until the maintainer decides.

## D-012 · 2026-06-28 · accepted — Hardhat node holds the allocator key in the skeleton
**Context.** Writes are role-gated to the `allocator`. **Decision.** In Phase 1 the local Hardhat
node manages account 0 and signs; the API sends `transact({"from": allocator})` with no local key
custody. **Consequence.** Keeps the skeleton minimal. A real key-custody / rotation / compromise
story (even simulated) is deferred to the threat model + [`LATER.md`](LATER.md) (critique #8); the
integrity model's dependence on this key is acknowledged, not yet hardened.

## D-011 · 2026-06-28 · accepted — JS keccak via js-sha3; canon-v1 agreement confirmed on first try
**Context.** Verifiability needs a *second* implementation that reproduces the engine's commitments.
**Decision.** The browser uses `js-sha3`'s `keccak256` (Ethereum variant) and a canon-v1 port
(`web/src/canon.js`). Its vitest reads the SAME frozen vectors as pytest. **Consequence.** Python and
JS reproduced every vector byte-for-byte on the first run — no spec change needed. Standing rule
holds: if they ever diverge, fix the canon-v1 spec, not one language ([[d-004]]).

## D-010 · 2026-06-28 · accepted — Off-chain store is in-memory; /reveal is open (skeleton only)
**Context.** Phase 1 needs an off-chain PII store and a way for the verifier to obtain revealed
records+salts. **Decision.** Use an in-memory store and an open `/reveal` endpoint for the walking
skeleton. **Consequence.** PII still never goes on-chain (only salted commitments do), but encryption
at rest and access-controlled reveal are explicitly Phase 3, not now. Documented so the skeleton's
openness is not mistaken for the target design.

## D-009 · 2026-06-28 · accepted — ranking_hash binds donor + policy + ordered ranked commitments
**Context.** The decision needs a single recomputable value pinning the exact ranking. **Decision.**
`ranking_hash = keccak256(canon_v1({donor_commitment, policy_version, ranked_recipient_commitments}))`,
reusing the commitment serialization so the JS verifier recomputes it on the same code path.
**Consequence.** Reordering the ranking changes the hash (proved by tests); one canon-v1 spec serves
both commitments and the decision hash.

## D-008 · 2026-06-28 · accepted — Skeleton policy id is "skeleton-waiting-time-v0", not kidney_v1
**Context.** The walking skeleton ranks by one trivial factor (waiting time), which is NOT the CAS
policy. **Decision.** Log the policy version as `skeleton-waiting-time-v0`. **Consequence.** The
on-chain log never falsely claims the real `kidney_v1` CAS was applied; swapping in the Phase 2 scorer
behind the same interface bumps the logged version honestly.

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
