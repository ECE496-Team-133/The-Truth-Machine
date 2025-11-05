#!/bin/bash
# Start the FastAPI backend server

cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

