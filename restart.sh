#!/bin/bash
# Restart script for The Truth Machine

echo "Stopping servers..."

# Kill processes on ports 8000 and 5173
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

# Wait a moment for processes to fully stop
sleep 2

echo "Starting servers..."
./start.sh
