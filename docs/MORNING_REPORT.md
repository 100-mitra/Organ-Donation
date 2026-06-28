# Morning report — Phase 1 walking skeleton (2026-06-28)

**Bottom line:** Phase 1 DoD is **MET and green end-to-end** (`commit → log → recompute → compare`,
trivial one-factor ranking), committed in five increments on branch `phase-1-walking-skeleton`. I then
ran an adversarial multi-agent review of the loop. It confirmed the architecture is sound, and surfaced
**7 high/critical findings** that need a scope/judgment call from you. **Per the night's rules I stopped
at the DoD and did NOT improvise any of these fixes** — they are written up below, ready to execute.

---

## What's green (done + committed)
| Layer | Tests | Notes |
|---|---|---|
| engine (trivial ranking + canon-v1 hash) | 6 pytest | `skeleton-waiting-time-v0`, NOT kidney_v1 |
| commitments (canon-v1) | 7 pytest | frozen cross-language vector |
| contracts (AuditLedger) | 6 Hardhat | role-gated, exact event args |
| api + off-chain store | 3 pytest | web3.py → local node |
| web (canon-v1 JS port + verify) | 8 vitest | reproduces frozen vector byte-for-byte, first try |
| **loop e2e** | Python + JS harness | both PASS incl. negative tamper check |

Run instructions: [`README.md`](../README.md). Loop gate: `bash scripts/check_e2e.sh` (stack running).
Commits: `2e70600` (phase 0) → `7925867` → `3a4cb09` → `6a1588b` → `9c02443` → `8631fb9`.

**What the review praised (so we don't break it):** the recompute is *genuinely independent* (both
verifiers re-rank from revealed records, not from the server's answer); scope discipline is "a model
walking skeleton" (ranking truly trivial, AuditLedger minimal, no Phase 2 / LATER leak); the contract
has "no security defects" (both write paths allocator-gated, allocator immutable, no PII on-chain).

---

## Findings that need your judgment

### GROUP A — Soundness gap: the revealed set is not bound to what was committed on-chain
**One root cause, four findings.** Verification reads only `DecisionLogged`; it never reads the
`Registered` events. So the verifier recomputes from whatever `/reveal` returns — a set the **server is
free to choose** — instead of from the population actually committed on the ledger. Consequences the
skeptics confirmed:
- **[CRITICAL]** A dishonest allocator can register the true pool, then `/reveal` (and `/match` over) a
  *different* pool; both verifiers still PASS.
- **[CRITICAL]** A recipient registered on-chain but omitted from `/reveal` → PASS (silent candidate drop).
- **[HIGH]** `/match` can drop a higher-ranked recipient and still pass (candidate set not pinned).
- **[HIGH]** Duplicate ids in `/reveal` collapse via last-write-wins in `byId` (ballot-stuffing hidden).

**Why I didn't fix it:** this changes the verifier's **trust model** — it means treating `/reveal` as
adversarial and binding it to on-chain `Registered` commitments (new `read_commitments()` in
`api/chain.py`; set-equality + permutation + uniqueness checks in `web/src/verify.js`, `scripts/e2e.py`,
`web/verify_e2e.mjs`; new tests). That is a real architecture decision, and it is plausibly **Phase 3**
work ("Real audit ledger + privacy", where access-controlled `/reveal` already lives). Your rules said
keep it minimal, stop at the DoD, and bring judgment calls to you — so here it is.

**Recommended fix (when you greenlight it):**
1. `api/chain.py`: add `read_commitments()` reading `Registered` events → the on-chain committed set.
2. Both verifiers: assert (a) every revealed recipient commitment ∈ registered set; (b) the decision's
   ranked commitments are a *permutation* of the registered recipient commitments (no drops/extras);
   (c) ids and commitments in `/reveal` are unique.
3. Add a negative e2e: drop/duplicate/substitute a recipient → verification must FAIL.
*No contract change needed — `Registered` already exists; we just start reading it.* AuditLedger stays minimal.

**Open question for you:** harden this now as a Phase 1.x pass, or carry it as a documented limitation
into Phase 3? (See logged limitation D-013.)

### GROUP B — canon-v1 determinism is under-pinned (latent, all tests currently pass)
The Python↔JS agreement holds for today's data but the spec allows inputs that would silently diverge:
- **[HIGH]** Integers > 2⁵³ diverge (Python keeps precision; JS rounds the double). Both float-guards
  pass. → Bound canon-v1 integers to `[-(2^53-1), 2^53-1]`; reject `!Number.isSafeInteger` in
  `canon.js` and `abs > 2**53-1` in `commitments.py`; add boundary vectors.
- **[HIGH]** Float asymmetry: Python rejects `2.0`, JS serializes it as `2` (JS can't distinguish at
  runtime). → State the asymmetry in `docs/canonicalization.md`; rely on a producer-side integer schema.
- **[HIGH]** Only ONE frozen vector. → Add vectors for: non-ASCII/emoji string value, nested empty
  `{}`/`[]`, negative int, explicit `null`/booleans, mixed-case/digit-leading keys (pins code-point
  sort), and a 2+ level nested object.

These are squarely canon-v1 spec work (the night's rule 2 mandate) and **low-risk** — guards + docs +
frozen vectors, no behavior change for valid inputs. I held off only because it is past the DoD and
adds new spec + vectors; it's a fast follow if you want it.

---

## What's blocked
Nothing is blocked. The loop is green; the live stack ran end-to-end. These are *hardening* decisions,
not failures.

## What I'd try next (in order, on your go-ahead)
1. **Group B** first (mechanical, low-risk, ~30 min): tighten canon-v1 + add the frozen-vector matrix.
2. **Group A** decision: if "fix now", implement the `Registered`-binding cross-check + negative e2e;
   if "defer", I'll leave D-013 as the documented limitation and pick it up in Phase 3.
3. Only then consider Phase 2 (real CAS) — unchanged from the roadmap.

## Why I stopped here
The Phase 1 goal — the full loop green end-to-end with a trivial ranking — is done. Both remaining
groups are either a trust-model judgment call (A) or past-DoD spec hardening (B). The night's rules were
explicit: stop at the DoD, keep it minimal, and surface judgment calls rather than improvise. So I did.

*(Background processes from tonight's run — Hardhat node + uvicorn — have been stopped; restart per the
README. The full review output is at the workflow task file referenced in the session.)*
