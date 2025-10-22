#!/bin/bash
set -euo pipefail
#!/bin/bash

# Respect user-defined dev ports
FRONTEND_DEV_PORT=${FRONTEND_DEV_PORT:-5173}
BACKEND_DEV_PORT=${BACKEND_DEV_PORT:-8000}

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

# Start frontend dev server (use chosen free port). Use exec so PID is npm itself.
echo "Starting frontend dev server on :$FE_PORT..."
(
  cd frontend
  exec npm run dev -- --port ${FE_PORT} --strictPort
) &
FE_PID=$!

# Start backend dev server with matching CORS origins. Use exec so PID maps to uvicorn.
echo "Starting backend dev server on :$BACKEND_DEV_PORT..."
(
  cd backend
  export ALLOWED_ORIGIN_1=http://localhost:${FE_PORT}
  export ALLOWED_ORIGIN_2=http://127.0.0.1:${FE_PORT}
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
wait -n ${FE_PID} ${BE_PID}
exit $?
