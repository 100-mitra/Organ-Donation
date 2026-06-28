# LATER — parked ideas (deliberately NOT in current scope)

> The parking lot that keeps the project finishable. Anything here is **out of the active plan** until
> Phase 7 ships (CLAUDE.md §4, §11). **Default to cut:** pulling an item *in* requires pushing
> something else *out*. Listing an idea here is how we say "good, but not now" without losing it.

## Parked by the plan (CLAUDE.md §4 / §11)
- **The second capstone.** Phase 6 picks exactly ONE of {ZK verify-without-revealing, kidney paired
  exchange}. The other becomes future work here — *not* a second capstone.
- **Governance / consent module.** On-chain donor consent + authority governance workflow.
- **Cold-chain IoT simulation.** Simulated organ-transport telemetry / ischemia tracking.
- **Multi-organ generalization.** Extend beyond kidney (liver, heart, lung) — different ischemia
  windows, different allocation policies.

## Parked policy refinements (CLAUDE.md §9)
- **ABO-identical-preferred.** Prioritise ABO-identical over merely-compatible matches to protect
  O recipients (a known fairness refinement). v1 uses plain ABO compatibility.
- **Longevity (EPTS) weight > 0.** The `longevity_epts` attribute is *defined but weight-0* in
  `kidney_v1.yaml`. Turning it on is a documented policy choice with real equity tension; evaluating
  on/off is a Phase 5 experiment, not a v1 default.
- **Richer HLA model.** v1 uses A/B/DR with 0–6 mismatches. Epitope/eplet matching and more loci are
  more realistic but out of scope. *(Keep the "modeled on OPTN" claim as "inspired by," not "faithful
  to" — critique #8.)*

## Parked engineering
- **Remote CI.** GitHub Actions running pytest + Hardhat on push — deferred until a git remote exists;
  local test runs gate each phase for now.
- **Signed-Merkle-log baseline.** Build the *simpler* tamper-evident log (Merkle root over SQLite) as a
  comparison point, to argue precisely what the blockchain adds over it (critique #4). Candidate
  Phase 5 add-on *if* it earns its keep; otherwise argued in prose only.
- **Allocator key management / rotation.** The integrity model rests on the allocator key; a custody +
  rotation + compromise story (even simulated) belongs in the threat model, not the v1 build
  (critique #8).

## True non-goals (will NOT be built — CLAUDE.md §4)
- Real patient data (synthetic only, always).
- Production deployment with real NOTTO/hospital organisations.
- Anything needing paid infrastructure or physical hardware.
- Public Ethereum mainnet; PII on any chain.
