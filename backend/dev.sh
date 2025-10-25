#!/bin/bash
set -euo pipefail

# Prefer user override, then search common python binaries (macOS + Linux)
REQUIRED_PYTHON="3.10"
if [ -n "${PYTHON_BIN:-}" ]; then
    PY_BIN="${PYTHON_BIN}"
else
    PY_BIN=""
    for cand in python3.12 python3.11 python3.10 python3 python; do
        if command -v "${cand}" >/dev/null 2>&1; then
            PY_BIN="${cand}"
            break
        fi
    done
fi

if [ -z "${PY_BIN}" ]; then
    cat <<'EOF' >&2
Error: No python interpreter found. Install Python 3.10+ (e.g., Homebrew `brew install python@3.11`,
pyenv, or python.org) and retry, or set PYTHON_BIN=/path/to/python ./dev.sh
EOF
    exit 1
fi

PY_VERSION="$("${PY_BIN}" - <<'PYCODE'
import sys
print(".".join(str(v) for v in sys.version_info[:3]))
PYCODE
)"

if ! "${PY_BIN}" - <<'PYCODE'
import sys
sys.exit(0 if sys.version_info >= (3, 10) else 1)
PYCODE
then
    cat <<EOF >&2
Error: ${PY_BIN} reports Python ${PY_VERSION}. Narrative Hero backend requires Python ${REQUIRED_PYTHON}+.
Install a newer Python (e.g., Homebrew \`brew install python@3.11\`, or pyenv.org) and rerun.
Alternatively set PYTHON_BIN=/path/to/python ./dev.sh
EOF
    exit 1
fi

VENV_DIR="${VENV_DIR:-venv}"

if [ ! -d "${VENV_DIR}" ]; then
    echo "Creating virtualenv in ${VENV_DIR}..."
    "${PY_BIN}" -m venv "${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"

# Check if .env file exists, if not, copy from example
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "Creating .env file from .env.example..."
        cp .env.example .env
    else
        echo "Warning: backend/.env is missing and no .env.example was found. Create backend/.env before launching."
    fi
fi

# Install/update dependencies (use venv pip directly)
"${VENV_DIR}/bin/pip" install -r requirements.txt --quiet

# Run the FastAPI server (exec to allow parent to manage the PID)
PORT=${BACKEND_DEV_PORT:-8000}
exec "${VENV_DIR}/bin/uvicorn" main:app --host 0.0.0.0 --port "${PORT}" --reload
