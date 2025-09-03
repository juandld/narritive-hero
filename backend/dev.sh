#!/usr/bin/env bash
set -a
# Load env variables from backend/.env if exists
source .env 2>/dev/null || true
set +a

# Activate venv
source venv/bin/activate

# Figure out project root (one level up from backend/)
PROJECT_ROOT="$(dirname "$(pwd)")"

# Set dynamic folders
export VOICE_NOTES_DIR="$PROJECT_ROOT/voice_notes"
export NARRATIVES_DIR="$PROJECT_ROOT/narratives"

# Auto-create if missing
mkdir -p "$VOICE_NOTES_DIR" "$NARRATIVES_DIR"

echo "VOICE_NOTES_DIR=$VOICE_NOTES_DIR"
echo "NARRATIVES_DIR=$NARRATIVES_DIR"


# Start FastAPI with autoreload
uvicorn main:app --reload

