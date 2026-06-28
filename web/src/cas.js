// Composite Allocation Score (CAS) — JavaScript twin of engine/scoring.py +
// engine/compatibility.py. MUST reproduce the Python engine byte-for-byte; the
// contract is the frozen vectors in engine/tests/vectors/cas_ranking_vectors.json.
// Integer-only arithmetic (Math.floor for the one integer division).

import { hexToBytes, keccak256Bytes } from "./canon.js";

const HLA_LOCI = ["A", "B", "DR"];

function clamp(x, lo, hi) {
  return x < lo ? lo : x > hi ? hi : x;
}

export function hlaMismatches(donorHla, recipHla) {
  let total = 0;
  for (const loc of HLA_LOCI) {
    const r = new Set(recipHla[loc] || []);
    for (const a of donorHla[loc] || []) if (!r.has(a)) total += 1;
  }
  return Math.min(total, 6);
}

export function distanceBand(donorRegion, recipRegion, zones) {
  if (donorRegion === recipRegion) return 0;
  const dz = zones[donorRegion];
  if (dz != null && dz === zones[recipRegion]) return 1;
  return 2;
}

export function extractFeatures(donor, recip, policy) {
  return {
    waiting_days: Math.max(0, donor.recovered_at_epoch_day - recip.dialysis_start_epoch_day),
    age_years: recip.age,
    prior_living_donor: recip.prior_living_donor,
    cpra: recip.cpra,
    hla_mismatches: hlaMismatches(donor.hla, recip.hla),
    distance_band: distanceBand(donor.region, recip.region, policy.region_zones),
    epts_score: clamp(recip.age, 0, 100),
    urgent: recip.urgent,
  };
}

export function rate(rating, value) {
  switch (rating.type) {
    case "linear_clamped":
      return clamp(Math.floor((value * rating.num) / rating.den), 0, rating.max_points);
    case "linear_descending":
      return Math.max(rating.floor_points, rating.max_points - value * rating.per_mismatch);
    case "step": {
      let pts = 0;
      for (const s of rating.steps) if (value >= s.at) pts = s.points;
      return pts;
    }
    case "threshold_bonus":
      return value < rating.lt ? rating.points_if_true : rating.points_if_false;
    case "boolean_bonus":
      // STRICT identity, not truthiness — Boolean([]) is true but Python bool([]) is
      // False; only a literal true earns the bonus, so both engines agree (D-019).
      return value === true ? rating.points_if_true : rating.points_if_false;
    case "map": {
      const k = String(value);
      return k in rating.map ? rating.map[k] : rating.default;
    }
    default:
      throw new Error(`unknown rating type: ${rating.type}`);
  }
}

export function eligibility(donor, recip, policy) {
  const g = policy.gates;
  const abo = (g.abo[donor.abo] || []).includes(recip.abo);
  let xm = true;
  if (g.virtual_crossmatch.enabled) {
    const expressed = new Set();
    for (const loc of HLA_LOCI) for (const a of donor.hla[loc] || []) expressed.add(a);
    xm = !(recip.unacceptable_antigens || []).some((a) => expressed.has(a));
  }
  const sane = recip.age >= g.sanity.min_age_years && recip.age <= g.sanity.max_age_years;
  const gates = { abo, virtual_crossmatch: xm, sanity: sane };
  return { eligible: abo && xm && sane, gates };
}

export function score(donor, recip, policy) {
  const feats = extractFeatures(donor, recip, policy);
  let cas = 0;
  const breakdown = {};
  for (const [name, attr] of Object.entries(policy.attributes)) {
    const points = rate(attr.rating, feats[attr.rating.input]);
    const weighted = attr.weight * points;
    cas += weighted;
    breakdown[name] = { bucket: attr.bucket, weight: attr.weight, points, weighted };
  }
  return { cas, breakdown, waiting_days: feats.waiting_days };
}

// keccak256(decision_seed ‖ recipient_id) -> hex (no 0x), matching engine _tie_seed.
function tieSeed(decisionSeed, id) {
  const seed = hexToBytes(decisionSeed);
  const idBytes = new TextEncoder().encode(id);
  const msg = new Uint8Array(seed.length + idBytes.length);
  msg.set(seed, 0);
  msg.set(idBytes, seed.length);
  return keccak256Bytes(msg).slice(2);
}

export function evaluate(donor, recipients, policy) {
  return recipients.map((r) => {
    const { eligible, gates } = eligibility(donor, r, policy);
    const row = { id: r.id, eligible, gates };
    if (eligible) Object.assign(row, score(donor, r, policy));
    return row;
  });
}

export function rank(donor, recipients, policy, decisionSeed) {
  const evaluated = evaluate(donor, recipients, policy);
  const eligible = evaluated.filter((e) => e.eligible);
  const seeds = {};
  const seedOf = (id) => (seeds[id] ??= tieSeed(decisionSeed, id));
  eligible.sort((a, b) => {
    if (a.cas !== b.cas) return b.cas - a.cas; // CAS desc
    for (const rule of policy.tie_break) {
      if (rule.by === "waiting_days") {
        if (a.waiting_days !== b.waiting_days) {
          return rule.direction === "desc"
            ? b.waiting_days - a.waiting_days
            : a.waiting_days - b.waiting_days;
        }
      } else if (rule.by === "keccak_seed") {
        const sa = seedOf(a.id);
        const sb = seedOf(b.id);
        if (sa !== sb) return sa < sb ? -1 : 1; // asc
      }
    }
    return 0;
  });
  return { ranked: eligible, evaluated };
}
