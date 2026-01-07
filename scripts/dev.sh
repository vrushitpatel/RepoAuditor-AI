#!/bin/bash

# Development server script for RepoAuditor AI

set -e

echo "=== RepoAuditor AI Development Server ==="
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Activating virtual environment..."
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        source venv/Scripts/activate
    else
        source venv/bin/activate
    fi
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found"
    echo "Please run 'bash scripts/setup.sh' first"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Start development server
echo "Starting development server..."
echo "Server will be available at http://localhost:${PORT:-8000}"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn app.main:app --reload --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}" --log-level "${LOG_LEVEL:-info}"
