import { useState } from "react";
import { verifyDecision } from "./verify.js"; // the SAME lockstep verifier; not reimplemented
import { short } from "./api.js";

const btn = (bg) => ({
  padding: "10px 16px", marginRight: 10, fontSize: 15, cursor: "pointer",
  border: `1px solid ${bg}`, background: bg, color: "#fff", borderRadius: 6,
});

function Banner({ ok, children }) {
  return (
    <div style={{
      padding: "10px 14px", borderRadius: 8, fontWeight: 800, fontSize: 17, margin: "10px 0",
      background: ok ? "#e7f7e7" : "#fdecec", border: `2px solid ${ok ? "#3a3" : "#c33"}`,
      color: ok ? "#175e17" : "#a11",
    }}>
      {children}
    </div>
  );
}

function Checks({ checks }) {
  return (
    <ul style={{ listStyle: "none", padding: 0, margin: "4px 0", fontSize: 13 }}>
      {checks.map((c, i) => (
        <li key={i} style={{ color: c.ok ? "#2a7" : "#c33", padding: "1px 0" }}>
          {c.ok ? "✓" : "✗"} {c.name}
        </li>
      ))}
    </ul>
  );
}

export default function Verify({ api, demo = false }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [honest, setHonest] = useState(null);
  const [tampered, setTampered] = useState(null);

  async function load() {
    const [audit, revealed, registered, policy, reg] = await Promise.all([
      api.get("/audit"), api.get("/reveal"), api.get("/commitments"),
      api.get("/policy"), api.get("/registrations"),
    ]);
    const latest = audit.decisions[audit.decisions.length - 1];
    if (!latest) throw new Error("no decision yet — run a match on the Allocate tab first");
    return { latest, revealed: revealed.revealed, registered: registered.registered, policy, reg };
  }

  const run = (fn) => async () => {
    setErr(null);
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  };

  const onVerify = run(async () => {
    setTampered(null);
    const { latest, revealed, registered, policy, reg } = await load();
    const res = verifyDecision(latest, revealed, registered, policy, reg.registrations, reg.erasures);
    setHonest({ decisionId: latest.decisionId, pool: latest.candidatePool.length, ...res });
  });

  const onTamper = run(async () => {
    const { latest, revealed, registered, policy, reg } = await load();
    // Edit a patient record AFTER the fact: backdate dialysis start to "jump the queue".
    const t = structuredClone(revealed);
    const rid = Object.keys(t).find((k) => t[k].kind === "recipient");
    const before = t[rid].record.dialysis_start_epoch_day;
    const after = before - 2000;
    t[rid].record.dialysis_start_epoch_day = after;
    const res = verifyDecision(latest, t, registered, policy, reg.registrations, reg.erasures);
    setTampered({ rid, before, after, decisionId: latest.decisionId, ...res });
  });

  return (
    <div>
      <div style={{ background: "#f4f7ff", border: "1px solid #d7e3ff", borderRadius: 8, padding: 12, marginBottom: 14, fontSize: 14, color: "#334" }}>
        <b>Authorized-auditor view.</b> Verification re-derives the ranking <b>in your browser</b> from the
        on-chain decision + the revealed records{" "}
        {demo
          ? "(here: the captured snapshot; live, they come from the access-controlled /reveal endpoint, D-022)"
          : "revealed by the access-controlled /reveal endpoint (token-gated, D-022; open here on synthetic data)"}
        . It does <b>not</b> trust the allocator — it
        recomputes the Composite Allocation Score and checks every value against the ledger.
      </div>

      <div style={{ margin: "12px 0" }}>
        <button style={btn("#2563eb")} onClick={onVerify} disabled={busy}>Verify latest decision</button>
        <button style={btn("#b45")} onClick={onTamper} disabled={busy}>Tamper demo</button>
      </div>

      {err && <div style={{ color: "#c33", marginBottom: 10 }}>⚠ {err}</div>}

      {honest && (
        <div>
          <Banner ok={honest.allOk}>
            {honest.allOk ? "✓ VERIFIED" : "✗ MISMATCH"} — decision #{honest.decisionId}
            {honest.allOk && ` · recompute matches the ledger (${honest.pool} candidates considered)`}
          </Banner>
          <Checks checks={honest.checks} />
        </div>
      )}

      {tampered && (
        <div style={{ marginTop: 18, borderTop: "1px dashed #ccc", paddingTop: 12 }}>
          <div style={{ fontSize: 14, marginBottom: 6 }}>
            <b>Tamper demo.</b> We backdated <b>{tampered.rid}</b>'s dialysis-start
            (<code>{tampered.before} → {tampered.after}</code>, ~2000 days earlier) to jump the queue —
            an edit made <i>after</i> the decision was logged.
          </div>
          <Banner ok={tampered.allOk}>
            {tampered.allOk ? "✓ VERIFIED (unexpected!)" : "✗ TAMPERING DETECTED"} — decision #{tampered.decisionId}
          </Banner>
          <div style={{ fontSize: 13, color: "#666", marginBottom: 4 }}>
            The edited record no longer opens to its on-chain commitment (and the recompute no longer
            matches), so the failing checks below expose the tampering:
          </div>
          <Checks checks={tampered.checks} />
        </div>
      )}
    </div>
  );
}
