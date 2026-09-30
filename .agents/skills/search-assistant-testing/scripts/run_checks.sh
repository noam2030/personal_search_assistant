#!/usr/bin/env bash
set -euo pipefail

# Locate project root (four levels up from this script directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

cd "${PROJECT_ROOT}"

echo "=================================================="
echo " Personal Search Assistant - Verification Runner"
echo "=================================================="

# Check virtual environment
if [ -f ".venv/bin/python" ]; then
    PYTHON_BIN=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
else
    echo "❌ Error: Python binary not found."
    exit 1
fi

echo "Using Python: ${PYTHON_BIN}"

# Check .env existence
if [ -f ".env" ]; then
    echo "✓ Found .env file"
else
    echo "⚠️ Warning: .env file not found in ${PROJECT_ROOT}"
fi

# Run E2E test suite
echo ""
echo "Running E2E test suite (test_e2e.py)..."
echo "--------------------------------------------------"
"${PYTHON_BIN}" test_e2e.py

echo ""
echo "✓ All checks completed successfully."
