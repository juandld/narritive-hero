#!/bin/bash

# Start frontend dev server
echo "Starting frontend dev server..."
(cd frontend && npm run dev) &

# Start backend dev server
echo "Starting backend dev server..."
(cd backend && ./dev.sh)
