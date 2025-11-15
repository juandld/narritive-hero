#!/usr/bin/env bash
set -euo pipefail

# Create a local virtual environment for backend tests and install deps.
# Safe to run multiple times; it will reuse the existing venv.

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$HERE/../.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

VENV_DIR="$HERE/.venv"

need_python() {
  local bin=$1
  "$bin" - <<'PY' >/dev/null 2>&1
import sys
sys.exit(0 if sys.version_info >= (3, 10) else 1)
PY
}

choose_python() {
  if [ -n "${PYTHON_BIN:-}" ]; then
    if need_python "$PYTHON_BIN"; then
      echo "$PYTHON_BIN"
      return 0
    else
      echo "PYTHON_BIN ($PYTHON_BIN) must be Python 3.10+." >&2
      return 1
    fi
  fi

  local -a candidates=()
  if command -v pyenv >/dev/null 2>&1; then
    if pyenv_bin="$(pyenv which python3 2>/dev/null)"; then
      candidates+=("$pyenv_bin")
    fi
  fi
  for name in python3.12 python3.11 python3.10 python3; do
    if command -v "$name" >/dev/null 2>&1; then
      candidates+=("$(command -v "$name")")
    fi
  done
  for cand in "${candidates[@]}"; do
    if need_python "$cand"; then
      echo "$cand"
      return 0
    fi
  done
  echo "Unable to find Python 3.10+ (checked: ${candidates[*]:-none}). Set PYTHON_BIN to a suitable interpreter." >&2
  return 1
}

pybin="$(choose_python)"

if [ -d "$VENV_DIR" ]; then
  if [ ! -x "$VENV_DIR/bin/python" ] || ! need_python "$VENV_DIR/bin/python"; then
    echo "Existing test venv uses an older Python; recreating with $pybin"
    rm -rf "$VENV_DIR"
  fi
fi

if [ ! -d "$VENV_DIR" ]; then
  echo "Creating test venv at $VENV_DIR using $pybin"
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
