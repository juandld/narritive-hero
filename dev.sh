#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$ROOT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  set -a
  source "$ENV_FILE"
  set +a
fi

# Respect user-defined dev ports
FRONTEND_DEV_PORT=${FRONTEND_DEV_PORT:-5173}
BACKEND_DEV_PORT=${BACKEND_DEV_PORT:-8000}
FRONTEND_DEV_HOST=${FRONTEND_DEV_HOST:-0.0.0.0}
FRONTEND_USE_HTTPS=${FRONTEND_USE_HTTPS:-0}
FRONTEND_CERT=${FRONTEND_CERT:-}
FRONTEND_KEY=${FRONTEND_KEY:-}

start_appwrite_stack() {
  if [ "${START_APPWRITE:-0}" != "1" ]; then
    return
  fi
  if ! command -v docker >/dev/null 2>&1; then
    echo "START_APPWRITE=1 requires Docker." >&2
    exit 1
  fi
  local compose_cmd=("docker" "compose")
  if ! docker compose version >/dev/null 2>&1; then
    if command -v docker-compose >/dev/null 2>&1; then
      compose_cmd=("docker-compose")
    else
      echo "Could not find docker compose. Install Docker Desktop or docker-compose." >&2
      exit 1
    fi
  fi
  echo "Starting Appwrite stack via docker compose..."
  "${compose_cmd[@]}" up -d mariadb redis smtp clamav appwrite
}

is_port_free() {
  local port=$1
  # Use bash's /dev/tcp to test connect; success means taken
  (echo > /dev/tcp/127.0.0.1/$port) >/dev/null 2>&1
  local rc=$?
  if [ $rc -eq 0 ]; then
    return 1 # port in use
  else
    return 0 # free
  fi
}

pick_frontend_port() {
  local start=${1:-5173}
  local limit=$((start+50))
  local p=$start
  while [ $p -le $limit ]; do
    if is_port_free $p; then echo $p; return 0; fi
    p=$((p+1))
  done
  echo $start
}

FE_PORT=$(pick_frontend_port ${FRONTEND_DEV_PORT})
if [ "$FE_PORT" != "$FRONTEND_DEV_PORT" ]; then
  echo "Note: Requested :$FRONTEND_DEV_PORT busy; using :$FE_PORT"
fi

start_appwrite_stack

# Start frontend dev server (use chosen free port). Use exec so PID is npm itself.
echo "Starting frontend dev server on :$FE_PORT..."
(
  cd frontend
  if ! command -v npm >/dev/null 2>&1; then
    echo "npm is required but was not found in PATH." >&2
    exit 1
  fi
  if [ ! -d node_modules ]; then
    echo "Installing frontend dependencies (node_modules missing)..."
    npm install
  elif [ -f package-lock.json ] && [ node_modules -ot package-lock.json ]; then
    echo "package-lock.json newer than node_modules; running npm install..."
    npm install
  fi
  extra_flags=(--host "${FRONTEND_DEV_HOST}" --port "${FE_PORT}" --strictPort)
  if [ "${FRONTEND_USE_HTTPS}" = "1" ]; then
    extra_flags+=(--https)
    if [ -n "${FRONTEND_CERT}" ]; then
      extra_flags+=(--cert "${FRONTEND_CERT}")
    fi
    if [ -n "${FRONTEND_KEY}" ]; then
      extra_flags+=(--key "${FRONTEND_KEY}")
    fi
  fi
  exec npm run dev -- "${extra_flags[@]}"
) &
FE_PID=$!

# Start backend dev server with matching CORS origins. Use exec so PID maps to uvicorn.
echo "Starting backend dev server on :$BACKEND_DEV_PORT..."
(
  cd backend
  export ALLOWED_ORIGIN_1=http://localhost:${FE_PORT}
  export ALLOWED_ORIGIN_2=http://127.0.0.1:${FE_PORT}
  if [ -n "${EXTERNAL_DEV_ORIGIN:-}" ]; then
    export ALLOWED_ORIGIN_3=${EXTERNAL_DEV_ORIGIN}
  fi
  export BACKEND_DEV_PORT=${BACKEND_DEV_PORT}
  exec ./dev.sh
) &
BE_PID=$!

cleanup() {
  echo "Shutting down dev servers..."
  # Try graceful first
  if kill -0 ${FE_PID} >/dev/null 2>&1; then kill ${FE_PID} 2>/dev/null || true; fi
  if kill -0 ${BE_PID} >/dev/null 2>&1; then kill ${BE_PID} 2>/dev/null || true; fi
  # Fallback force after short wait
  sleep 1
  if kill -0 ${FE_PID} >/dev/null 2>&1; then kill -9 ${FE_PID} 2>/dev/null || true; fi
  if kill -0 ${BE_PID} >/dev/null 2>&1; then kill -9 ${BE_PID} 2>/dev/null || true; fi
}

trap cleanup EXIT INT TERM HUP

# Wait for either to exit, then cleanup
wait_for_either() {
  # Modern Bash (>=4.3) supports wait -n; try it first.
  if wait -n "${FE_PID}" "${BE_PID}" 2>/dev/null; then
    return $?
  fi
  # Fallback for older shells: poll until one child exits.
  while true; do
    if ! kill -0 "${FE_PID}" >/dev/null 2>&1; then
      wait "${FE_PID}" 2>/dev/null
      return $?
    fi
    if ! kill -0 "${BE_PID}" >/dev/null 2>&1; then
      wait "${BE_PID}" 2>/dev/null
      return $?
    fi
    sleep 1
  done
}

wait_for_either
exit $?
