// Tiny API client. Carries the optional allocator/auditor token so the gated
// endpoints (/seed, /match, /erase, /register, /reveal — D-022) work when the
// backend has ALLOCATOR_TOKEN set; harmless on the open endpoints.
export function makeApi(base, token) {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const call = async (path, method = "GET") => {
    const res = await fetch(`${base}${path}`, { method, headers });
    if (!res.ok) {
      const body = await res.text().catch(() => "");
      const hint = res.status === 401 ? " (set the allocator token above)" : "";
      throw new Error(`${path} → ${res.status}${hint}${body ? ` ${body.slice(0, 100)}` : ""}`);
    }
    return res.json();
  };
  return { base, get: (p) => call(p, "GET"), post: (p) => call(p, "POST") };
}

export const short = (hex, n = 8) =>
  typeof hex === "string" && hex.length > 2 * n ? `${hex.slice(0, n)}…${hex.slice(-4)}` : hex;
