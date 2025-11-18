#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$ROOT_DIR/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[deploy] Missing .env file in repo root. Copy .env.example and set the Appwrite/LLM keys first." >&2
  exit 1
fi

# Load env vars (Appwrite credentials, ports, etc.)
set -a
source "$ENV_FILE"
set +a

APPWRITE_ADMIN_KEY="${APPWRITE_ADMIN_KEY:-$APPWRITE_API_KEY}"
if [[ -z "${APPWRITE_ENDPOINT:-}" || -z "${APPWRITE_PROJECT_ID:-}" || -z "${APPWRITE_DATABASE_ID:-}" || -z "${APPWRITE_API_KEY:-}" ]]; then
  echo "[deploy] APPWRITE_* variables must be set in .env before running this script." >&2
  exit 1
fi

cd "$ROOT_DIR"

echo "[deploy] Starting Appwrite core services..."
docker compose up -d mariadb redis smtp clamav appwrite appwrite-worker-databases

echo "[deploy] Bootstrapping Appwrite schema..."
(
  cd backend
  export PYTHONPATH=.
  APPWRITE_ADMIN_KEY="$APPWRITE_ADMIN_KEY" python3 scripts/setup_appwrite_schema.py
)

echo "[deploy] Migrating existing filesystem data into Appwrite..."
(
  cd backend
  export PYTHONPATH=.
  python3 scripts/migrate_to_appwrite.py
)

echo "[deploy] Building and starting Narrative Hero services..."
docker compose up -d --build backend frontend

echo "[deploy] Deployment complete. Frontend is on http://localhost (or your configured FRONTEND_PORT)."
