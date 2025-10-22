#!/bin/bash
set -euo pipefail

# Stop dev servers by ports (fallback utility)
FE_PORT=${FRONTEND_DEV_PORT:-5173}
BE_PORT=${BACKEND_DEV_PORT:-8000}

kill_by_port() {
  local port=$1
  if command -v lsof >/dev/null 2>&1; then
    local pids=$(lsof -t -i :$port || true)
    if [ -n "$pids" ]; then
      echo "Killing processes on :$port -> $pids"
      kill $pids 2>/dev/null || true
      sleep 1
      kill -9 $pids 2>/dev/null || true
    fi
  else
    echo "lsof not found; skipping port kill for :$port"
  fi
}

kill_by_port "$FE_PORT"
kill_by_port "$BE_PORT"

echo "Done."

