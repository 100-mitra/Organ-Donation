#!/usr/bin/env bash
# Phase 1 loop gate: with the chain + API running, prove commit -> log ->
# recompute -> compare is green via BOTH independent recomputes (Python + the
# exact browser JS path). Exits non-zero on any mismatch.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_URL="${API_URL:-http://127.0.0.1:8010}"

echo "== Python independent recompute =="
API_URL="$API_URL" python "$ROOT/scripts/e2e.py"

echo
echo "== JavaScript (browser verify path) recompute =="
( cd "$ROOT/web" && API_URL="$API_URL" node verify_e2e.mjs )

echo
echo "ALL E2E GREEN"
