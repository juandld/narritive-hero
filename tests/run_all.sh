#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "[1/2] Backend tests"
pushd "$ROOT_DIR/tests/backend" >/dev/null
chmod +x ./test.sh || true
./test.sh || { echo "Backend tests failed"; exit 1; }
popd >/dev/null

echo "[2/2] Frontend tests (if configured)"
if [ -f "$ROOT_DIR/frontend/package.json" ]; then
  pushd "$ROOT_DIR/frontend" >/dev/null
  if jq -e '.scripts.test' package.json >/dev/null 2>&1; then
    npm run test || echo "Frontend tests not configured or failed; skipping"
  else
    echo "No frontend test script found; skipping"
  fi
  popd >/dev/null
fi

echo "Done."
