// Demo-mode data source (Phase 7, D-026). Serves the pre-captured bundle
// (web/src/demo/bundle.json — REAL output of the local stack, written and
// self-verified by scripts/capture_demo_bundle.py) through the same api
// interface makeApi() provides, so Verify.jsx and the lockstep verifier
// (verify.js / cas.js) run byte-for-byte unchanged — only the data source
// differs from a live deployment, which would fetch these from the API/chain.
export function makeDemoApi(bundle) {
  const routes = {
    "/audit": bundle.audit,
    "/reveal": bundle.reveal,
    "/commitments": bundle.commitments,
    "/registrations": bundle.registrations,
    "/policy": bundle.policy,
  };
  return {
    base: "bundled snapshot (demo)",
    get: async (path) => {
      if (!(path in routes)) throw new Error(`${path} is not in the demo snapshot`);
      // structuredClone: callers (e.g. the tamper demo) may mutate the response.
      return structuredClone(routes[path]);
    },
    post: async (path) => {
      throw new Error(`${path}: demo mode is read-only — clone the repo to run the live stack`);
    },
  };
}
