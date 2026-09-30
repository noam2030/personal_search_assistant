#!/usr/bin/env bash
set -euo pipefail

# Locate project root (four levels up from this script directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

cd "${PROJECT_ROOT}"

echo "=================================================="
echo " Personal Search Assistant - Verification Runner"
echo "=================================================="

# Check virtual environment for pytest
if [ -f "venv/bin/pytest" ]; then
    PYTEST_BIN="venv/bin/pytest"
elif [ -f ".venv/bin/pytest" ]; then
    PYTEST_BIN=".venv/bin/pytest"
else
    echo "❌ Error: Virtual environment pytest not found. Please ensure venv/bin/pytest is installed."
    exit 1
fi

echo "Using Pytest: ${PYTEST_BIN}"

# Check .env existence
if [ -f ".env" ]; then
    echo "✓ Found .env file"
else
    echo "⚠️ Warning: .env file not found in ${PROJECT_ROOT}"
fi

# Run test suite via venv/bin/pytest
echo ""
echo "Running test suite via ${PYTEST_BIN}..."
echo "--------------------------------------------------"
"${PYTEST_BIN}" test_e2e.py

echo ""
echo "✓ All checks completed successfully."
