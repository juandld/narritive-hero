#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== Running Narrative Hero tests ==="

echo "[1/1] Backend"
pushd "$ROOT_DIR/tests/backend" >/dev/null
chmod +x ./test.sh || true
./test.sh
popd >/dev/null

echo "\nAll done."

