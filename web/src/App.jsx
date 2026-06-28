import { useState } from "react";
import { makeApi } from "./api.js";
import Allocate from "./Allocate.jsx";
import Verify from "./Verify.jsx";

const DEFAULT_API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8010";

export default function App() {
  const [tab, setTab] = useState("allocate");
  const [token, setToken] = useState("");
  const api = makeApi(DEFAULT_API, token);

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
        permissioned ledger so anyone can <b>recompute and confirm</b> the allocation was faithful.
      </p>

      <div style={{ display: "flex", alignItems: "center", gap: 12, borderBottom: "1px solid #ddd", marginBottom: 16 }}>
        {tabBtn("allocate", "Allocate")}
        {tabBtn("verify", "Verify (auditor)")}
        <span style={{ flex: 1 }} />
        <input
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="allocator token (blank = demo)"
          style={{ fontSize: 12, padding: "5px 8px", width: 210, border: "1px solid #ccc", borderRadius: 4 }}
        />
      </div>

      {tab === "allocate" ? <Allocate api={api} /> : <Verify api={api} />}

      <p style={{ color: "#999", fontSize: 12, marginTop: 28 }}>
        Synthetic data only · process-integrity guarantee, not input-truth (oracle boundary, see
        docs/threat-model.md) · API: <code>{api.base}</code>
      </p>
    </div>
  );
}
