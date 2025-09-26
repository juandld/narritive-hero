#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
TEST_DIR="$ROOT_DIR/tests/backend"
BACKEND_DIR="$ROOT_DIR/backend"

cd "$TEST_DIR"

# Try to prepare a venv for consistent deps; fall back gracefully if offline.
if [ -x "$TEST_DIR/setup_venv.sh" ]; then
  bash "$TEST_DIR/setup_venv.sh" || echo "Note: setup_venv failed (likely offline); continuing."
fi

# Activate venv if it exists
if [ -f "$TEST_DIR/.venv/bin/activate" ]; then
  source "$TEST_DIR/.venv/bin/activate"
fi

export PYTHONPATH="$BACKEND_DIR"

if python -c "import pytest" >/dev/null 2>&1; then
  echo "Running backend tests (pytest)..."
  pytest -q
else
  echo "pytest not available (offline?). Running smoke tests..."
  python3 "$TEST_DIR/run_smoke_tests.py"
fi
