#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Check if .env file exists, if not, copy from example
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
fi

# Install/update dependencies
pip install -r requirements.txt --quiet

# Run the FastAPI server (exec to allow parent to manage the PID)
PORT=${BACKEND_DEV_PORT:-8000}
exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --reload
