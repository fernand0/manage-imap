#!/bin/bash
set -euo pipefail

echo "Removing virtual environment..."
rm -rf .venv

echo "Removing uv.lock..."
rm -f uv.lock

echo "Removing __pycache__ directories and .pyc files..."
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

echo "Cleanup complete."
