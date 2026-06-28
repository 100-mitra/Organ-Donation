import { useState } from "react";
import { verifyDecision } from "./verify.js";

// Phase 1 walking-skeleton UI: three buttons that drive the whole loop.
//   Register -> POST /seed   (commit on-chain)
//   Match    -> POST /match  (rank + log decision)
//   Verify   -> GET /audit + /reveal, then recompute IN THE BROWSER and compare.
// The Verify button does NOT trust the server's answer — it re-derives the
// ranking from the revealed records using the canon-v1 JS port (verify.js).

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8010";

export default function App() {
  const [log, setLog] = useState([]);
  const [decision, setDecision] = useState(null);
  const [verify, setVerify] = useState(null);
  const [busy, setBusy] = useState(false);

  const say = (m) => setLog((l) => [...l, m]);

  async function guard(fn) {
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      say(`ERROR: ${e.message}`);
    } finally {
      setBusy(false);
    }
  }

  const onRegister = () =>
    guard(async () => {
      setVerify(null);
      setDecision(null);
      const r = await fetch(`${API}/seed`, { method: "POST" }).then((x) => x.json());
      say(`Registered donor ${r.donor.id} + ${r.recipients.length} recipients (committed on-chain)`);
    });

  const onMatch = () =>
    guard(async () => {
      const d = await fetch(`${API}/match`, { method: "POST" }).then((x) => x.json());
      setDecision(d);
      say(`Logged decision #${d.decisionId}: ${d.rankedRecipientIds.join(" > ")}`);
    });

  const onVerify = () =>
    guard(async () => {
      const audit = await fetch(`${API}/audit`).then((x) => x.json());
      const revealed = await fetch(`${API}/reveal`).then((x) => x.json());
      const registered = await fetch(`${API}/commitments`).then((x) => x.json());
      const policy = await fetch(`${API}/policy`).then((x) => x.json());
      const reg = await fetch(`${API}/registrations`).then((x) => x.json());
      const latest = audit.decisions[audit.decisions.length - 1];
      if (!latest) throw new Error("no decision on-chain yet — Match first");
      const res = verifyDecision(
        latest, revealed.revealed, registered.registered, policy, reg.registrations, reg.erasures
      );
      setVerify({ ...res, decisionId: latest.decisionId });
      say(res.allOk ? `VERIFY PASSED: decision #${latest.decisionId} recompute matches chain` : "VERIFY FAILED");
    });

  const btn = { padding: "10px 16px", marginRight: 10, fontSize: 15, cursor: "pointer" };

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", maxWidth: 820, margin: "32px auto", padding: 16 }}>
      <h1 style={{ fontSize: 22 }}>Verifiable Allocation — Phase 2 (CAS)</h1>
      <p style={{ color: "#555" }}>
        Full Composite Allocation Score (eligibility gates + integer weighted scoring). The chain proves
        the logged ranking faithfully executed <code>kidney_v1</code>; Verify recomputes it{" "}
        <b>in your browser</b> and compares.
      </p>

      <div style={{ margin: "16px 0" }}>
        <button style={btn} onClick={onRegister} disabled={busy}>1. Register</button>
        <button style={btn} onClick={onMatch} disabled={busy}>2. Match</button>
        <button style={btn} onClick={onVerify} disabled={busy}>3. Verify</button>
      </div>

      {decision && (
        <div style={{ background: "#f6f6f6", padding: 12, borderRadius: 6, marginBottom: 16 }}>
          <b>Decision #{decision.decisionId}</b> &nbsp;policy <code>{decision.policyVersion}</code>
          <div>ranking: {decision.rankedRecipientIds.join(" > ")}</div>
          <div style={{ fontSize: 12, color: "#777", wordBreak: "break-all" }}>
            rankingHash {decision.rankingHash}
          </div>
        </div>
      )}

      {verify && (
        <div
          style={{
            padding: 12,
            borderRadius: 6,
            marginBottom: 16,
            background: verify.allOk ? "#e7f7e7" : "#fdecec",
            border: `1px solid ${verify.allOk ? "#3a3" : "#c33"}`,
          }}
        >
          <b>{verify.allOk ? "VERIFIED" : "MISMATCH"}</b> — decision #{verify.decisionId}
          <ul style={{ margin: "8px 0 0", paddingLeft: 20 }}>
            {verify.checks.map((c, i) => (
              <li key={i}>{c.ok ? "[ok] " : "[FAIL] "}{c.name}</li>
            ))}
          </ul>
        </div>
      )}

      <pre style={{ background: "#111", color: "#0f0", padding: 12, borderRadius: 6, minHeight: 80, whiteSpace: "pre-wrap" }}>
        {log.join("\n") || "click Register -> Match -> Verify"}
      </pre>
    </div>
  );
}
