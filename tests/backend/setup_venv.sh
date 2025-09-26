#!/usr/bin/env bash
set -euo pipefail

# Create a local virtual environment for backend tests and install deps.
# Safe to run multiple times; it will reuse the existing venv.

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$HERE/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

VENV_DIR="$HERE/.venv"

pybin="python3"
if command -v pyenv >/dev/null 2>&1; then
  # Prefer the pyenv shim if available
  pybin="$(command -v python3)"
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating test venv at $VENV_DIR"
  "$pybin" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip >/dev/null 2>&1 || true

echo "Installing backend dependencies (may require network)..."
if ! python -m pip install -r "$BACKEND_DIR/requirements.txt" >/dev/null 2>&1; then
  echo "Warning: Could not install backend requirements (offline?)."
fi

echo "Installing test dependencies..."
if ! python -m pip install -r "$HERE/requirements-dev.txt" >/dev/null 2>&1; then
  echo "Warning: Could not install test requirements (offline?)."
fi

echo "Venv ready at $VENV_DIR"

