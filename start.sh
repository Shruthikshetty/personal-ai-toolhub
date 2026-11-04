#!/usr/bin/env bash

# ==============================================================================
# Custom AI API Server — Production Startup Script (Linux / Raspberry Pi)
# ==============================================================================

# Exit immediately if a command exits with a non-zero status
set -e

# Change directory to the folder where this script resides
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "  Starting Custom AI API (Production)"
echo "========================================"

# Check for virtual environment
if [ ! -d "venv" ]; then
    echo "[!] Virtual environment 'venv' not found."
    echo "    Creating new virtual environment..."
    python3 -m venv venv
    echo "    Installing dependencies..."
    venv/bin/pip install --upgrade pip
    venv/bin/pip install -r requirements.txt
fi

# Activate virtual environment
source venv/bin/activate

# Fetch local IP address for convenience display
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo "----------------------------------------"
echo "  Server running in PRODUCTION mode"
echo "  Local access:    http://localhost:8080"
echo "  Network access:  http://${LOCAL_IP}:8080"
echo "  API Docs:        http://${LOCAL_IP}:8080/docs"
echo "----------------------------------------"
echo "Press Ctrl+C to stop the server."
echo ""

# Run Uvicorn directly without dev overhead:
# - No file watchers / reloaders (--reload omitted)
# - Binds to 0.0.0.0 to be accessible across local network
# - Uses 2 workers for handling concurrent requests cleanly
exec uvicorn app:create_app \
    --factory \
    --host 0.0.0.0 \
    --port 8080 \
    --workers 2 \
    --no-access-log

