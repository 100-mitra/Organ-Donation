import { useState } from "react";
import { makeApi } from "./api.js";
import Allocate from "./Allocate.jsx";
import Verify from "./Verify.jsx";
import { makeDemoApi } from "./demo/demoApi.js";
import bundle from "./demo/bundle.json";

const DEFAULT_API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8010";
// Demo mode (Phase 7, D-026): a static build with no live API/chain. The Verify
// flow reads the bundled pre-captured snapshot; verifier logic is unchanged.
const DEMO = import.meta.env.VITE_DEMO === "1";

export default function App() {
  const [tab, setTab] = useState(DEMO ? "verify" : "allocate");
  const [token, setToken] = useState("");
  const api = DEMO ? makeDemoApi(bundle) : makeApi(DEFAULT_API, token);

  const tabBtn = (id, label) => (
    <button
      onClick={() => setTab(id)}
      style={{
        padding: "8px 16px", fontSize: 15, cursor: "pointer", border: "none",
        borderBottom: tab === id ? "3px solid #2563eb" : "3px solid transparent",
        background: "none", color: tab === id ? "#111" : "#666",
        fontWeight: tab === id ? 700 : 400,
      }}
    >
      {label}
    </button>
  );

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", maxWidth: 880, margin: "24px auto", padding: 16, color: "#111" }}>
      <h1 style={{ fontSize: 22, marginBottom: 2 }}>Verifiable Organ Allocation</h1>
      <p style={{ color: "#555", marginTop: 0 }}>
        Deceased-donor kidney matching by a transparent policy (<code>kidney_v1</code>), logged to a
        permissioned ledger so an auditor can <b>recompute and confirm</b> the allocation was faithful.
      </p>

      {DEMO && (
        <div style={{ background: "#fff8e6", border: "1px solid #eedc9a", borderRadius: 8, padding: "10px 14px", marginBottom: 14, fontSize: 13, color: "#5a4a12" }}>
          <b>Static demo — synthetic data, pre-captured decision.</b> This page shows one real
          allocation produced by the full system (CAS engine + local permissioned chain) and captured
          as a snapshot (decision #{bundle._meta.decision_id}, policy{" "}
          <code>{bundle._meta.policy_version}</code>). The on-chain data shown is that captured
          snapshot — a live deployment reads it from the chain. Verification and the tamper demo run
          <b> for real, in your browser</b>, with the same verifier the tests pin. Not a live
          production system; no real patient data.{" "}
          <a href="https://github.com/100-mitra/Organ-Donation">source</a> ·{" "}
          <a href="https://github.com/100-mitra/Organ-Donation/blob/main/docs/ANALYSIS.md">write-up (what this proves and doesn't)</a>
        </div>
      )}

      <div style={{ display: "flex", alignItems: "center", gap: 12, borderBottom: "1px solid #ddd", marginBottom: 16 }}>
        {tabBtn("allocate", DEMO ? "Decision (captured)" : "Allocate")}
        {tabBtn("verify", "Verify (auditor)")}
        <span style={{ flex: 1 }} />
        {!DEMO && (
          <input
            value={token}
            onChange={(e) => setToken(e.target.value)}
            placeholder="allocator token (blank = demo)"
            style={{ fontSize: 12, padding: "5px 8px", width: 210, border: "1px solid #ccc", borderRadius: 4 }}
          />
        )}
      </div>

      {tab === "allocate" ? <Allocate api={api} captured={DEMO ? bundle.match : null} /> : <Verify api={api} demo={DEMO} />}

      <p style={{ color: "#999", fontSize: 12, marginTop: 28 }}>
        Synthetic data only · process-integrity guarantee, not input-truth (oracle boundary, see
        docs/threat-model.md) · API: <code>{api.base}</code>
      </p>
    </div>
  );
}
