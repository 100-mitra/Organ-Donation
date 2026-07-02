// The deployed demo must genuinely verify (Phase 7, D-026): the pre-captured
// bundle — real output of the local stack — must PASS the unchanged lockstep
// verifier in JS, and the browser tamper demo's exact edit must FAIL it.
// This gates the Pages deploy: a broken fixture cannot ship.
import { describe, expect, it } from "vitest";
import bundle from "./demo/bundle.json";
import { makeDemoApi } from "./demo/demoApi.js";
import { verifyDecision } from "./verify.js";

async function load(api) {
  const [audit, revealed, registered, policy, reg] = await Promise.all([
    api.get("/audit"), api.get("/reveal"), api.get("/commitments"),
    api.get("/policy"), api.get("/registrations"),
  ]);
  const latest = audit.decisions[audit.decisions.length - 1];
  return { latest, revealed: revealed.revealed, registered: registered.registered, policy, reg };
}

describe("bundled demo snapshot (real captured decision)", () => {
  it("verifies PASS through the demo api with the unchanged verifier", async () => {
    const { latest, revealed, registered, policy, reg } = await load(makeDemoApi(bundle));
    const res = verifyDecision(latest, revealed, registered, policy, reg.registrations, reg.erasures);
    expect(res.checks.length).toBeGreaterThan(0);
    expect(res.checks.filter((c) => !c.ok)).toEqual([]);
    expect(res.allOk).toBe(true);
  });

  it("FAILS on the tamper demo's exact edit (backdated dialysis start)", async () => {
    const { latest, revealed, registered, policy, reg } = await load(makeDemoApi(bundle));
    const rid = Object.keys(revealed).find((k) => revealed[k].kind === "recipient");
    revealed[rid].record.dialysis_start_epoch_day -= 2000;
    const res = verifyDecision(latest, revealed, registered, policy, reg.registrations, reg.erasures);
    expect(res.allOk).toBe(false);
  });

  it("matches the Allocate view's captured decision to the on-chain log", () => {
    const latest = bundle.audit.decisions[bundle.audit.decisions.length - 1];
    expect(bundle.match.decisionId).toBe(latest.decisionId);
    expect(bundle.match.rankingHash).toBe(latest.rankingHash);
    expect(bundle.match.policyVersion).toBe(latest.policyVersion);
  });

  it("demo api is read-only", async () => {
    await expect(makeDemoApi(bundle).post("/match")).rejects.toThrow(/read-only/);
  });
});
