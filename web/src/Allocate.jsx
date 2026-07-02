import { useState } from "react";
import { short } from "./api.js";

const btn = {
  padding: "10px 16px", marginRight: 10, fontSize: 15, cursor: "pointer",
  border: "1px solid #2563eb", background: "#2563eb", color: "#fff", borderRadius: 6,
};
const card = { border: "1px solid #e2e2e2", borderRadius: 8, padding: 12, marginBottom: 10 };

function Breakdown({ breakdown }) {
  const rows = Object.entries(breakdown).sort((a, b) => b[1].weight - a[1].weight);
  return (
    <table style={{ fontSize: 13, marginTop: 8, borderCollapse: "collapse", width: "100%", maxWidth: 460 }}>
      <thead>
        <tr style={{ color: "#888", textAlign: "left" }}>
          <th>attribute</th><th style={{ textAlign: "right" }}>points</th>
          <th style={{ textAlign: "center" }}>× weight</th><th style={{ textAlign: "right" }}>= contribution</th>
        </tr>
      </thead>
      <tbody>
        {rows.map(([name, b]) => (
          <tr key={name} style={{ color: b.weight === 0 ? "#bbb" : "#333" }}>
            <td>{name.replace(/_/g, " ")}</td>
            <td style={{ textAlign: "right" }}>{b.points}</td>
            <td style={{ textAlign: "center" }}>{b.weight}</td>
            <td style={{ textAlign: "right", fontWeight: 600 }}>{b.weighted}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function Allocate({ api, captured = null }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [seeded, setSeeded] = useState(null);
  // Demo mode is read-only: show the pre-captured decision; never fake a live match.
  const [decision, setDecision] = useState(captured);

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

  const onRegister = run(async () => {
    setDecision(null);
    setSeeded(await api.post("/seed"));
  });
  const onMatch = run(async () => setDecision(await api.post("/match")));

  const excluded = decision ? decision.explanations.filter((e) => !e.eligible) : [];

  return (
    <div>
      {captured ? (
        <p style={{ color: "#555" }}>
          The decision below was produced by the real pipeline — pool registered on-chain (salted
          commitments only), CAS ranking computed, decision logged — and captured as this demo's
          snapshot. Running a <i>new</i> match needs the live stack (clone the repo); this page
          won't fake one.
        </p>
      ) : (
        <>
          <p style={{ color: "#555" }}>
            Register the candidate pool + donor on-chain, then run the match. Each record's salted
            commitment goes to the ledger; the PII stays in the encrypted off-chain store.
          </p>
          <div style={{ margin: "12px 0" }}>
            <button style={btn} onClick={onRegister} disabled={busy}>1 · Register pool</button>
            <button style={btn} onClick={onMatch} disabled={busy || !seeded}>2 · Run match</button>
          </div>
        </>
      )}

      {err && <div style={{ color: "#c33", marginBottom: 10 }}>⚠ {err}</div>}
      {seeded && !decision && (
        <div style={{ color: "#2a7" }}>
          Registered donor {seeded.donor.id} + {seeded.recipients.length} recipients
          {seeded.reset_erased ? ` (reset: erased ${seeded.reset_erased} prior)` : ""}.
        </div>
      )}

      {decision && (
        <div>
          <h3 style={{ marginBottom: 4 }}>
            Decision #{decision.decisionId} · policy <code>{decision.policyVersion}</code>
          </h3>
          <div style={{ fontSize: 12, color: "#777", marginBottom: 12 }}>
            donor {short(decision.donorCommitment)} · candidate pool of {decision.candidatePool.length} ·
            ranking {short(decision.rankingHash)}
          </div>

          <div style={{ fontWeight: 700, margin: "6px 0" }}>Ranked (eligible)</div>
          {decision.rankedRecipientIds.map((id, i) => {
            const e = decision.explanations.find((x) => x.id === id);
            return (
              <div key={id} style={card}>
                <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
                  <span style={{ fontSize: 18, fontWeight: 800, color: "#2563eb" }}>#{i + 1}</span>
                  <b style={{ fontSize: 16 }}>{id}</b>
                  <span style={{ fontSize: 14 }}>CAS <b>{e.cas}</b></span>
                  <span style={{ fontSize: 12, color: "#2a7" }}>gates: all passed</span>
                </div>
                <Breakdown breakdown={e.breakdown} />
              </div>
            );
          })}

          {excluded.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontWeight: 700, margin: "6px 0", color: "#a55" }}>Excluded by gates</div>
              {excluded.map((e) => (
                <div key={e.id} style={{ ...card, borderColor: "#f0d6d6", background: "#fcf6f6" }}>
                  <b>{e.id}</b> — failed gate:{" "}
                  <span style={{ color: "#c33" }}>
                    {Object.entries(e.gates).filter(([, ok]) => !ok).map(([g]) => g).join(", ")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
