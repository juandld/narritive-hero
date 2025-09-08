#!/usr/bin/env bash

# Exit on error
set -e

# Check if venv exists, if not create it and install dependencies
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
    echo "Virtual environment created."
    
    echo "Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
    echo "Dependencies installed."
else
    # Activate existing venv
    source venv/bin/activate
fi

set -a
# Load env variables from backend/.env if exists
source .env 2>/dev/null || true
set +a

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

