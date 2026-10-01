#!/usr/bin/env bash
set -euo pipefail

# Locate project root (four levels up from this script directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

cd "${PROJECT_ROOT}"

echo "=================================================="
echo " Personal Search Assistant - Verification Runner"
echo "=================================================="

# Check for uv or .venv pytest
if command -v uv >/dev/null 2>&1 && [ -f ".venv/bin/pytest" ]; then
    PYTEST_CMD=(uv run pytest)
elif [ -f ".venv/bin/pytest" ]; then
    PYTEST_CMD=(.venv/bin/pytest)
else
    echo "❌ Error: Virtual environment pytest not found in .venv/. Please install dependencies via uv."
    exit 1
fi

echo "Using Pytest: ${PYTEST_CMD[*]}"

# Check .env existence
if [ -f ".env" ]; then
    echo "✓ Found .env file"
else
    echo "⚠️ Warning: .env file not found in ${PROJECT_ROOT}"
fi

# Run test suite via uv or .venv
echo ""
echo "Running test suite via ${PYTEST_CMD[*]}..."
echo "--------------------------------------------------"
"${PYTEST_CMD[@]}" test_e2e.py

echo ""
echo "✓ All checks completed successfully."
