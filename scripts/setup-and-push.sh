#!/bin/bash
# Run this after: sudo apt-get install -y git python3-pip python3.12-venv
set -e

cd /home/oc01/.openclaw/workspace/duckguard

# 1. Set up Python venv
echo "=== Setting up Python venv ==="
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev]"

# 2. Run tests
echo "=== Running test suite ==="
pytest tests/ -v --tb=short 2>&1 | tee test-results.txt

# 3. Run linting
echo "=== Running linter ==="
ruff check src/ 2>&1 | tee lint-results.txt || true

# 4. Build and verify package
echo "=== Building package ==="
pip install build twine
python -m build
twine check dist/*

# 5. Build docs site
echo "=== Building docs ==="
pip install mkdocs-material mkdocstrings[python] pymdown-extensions
mkdocs build

echo "=== All done! ==="
echo "Next: git add, commit, push"
