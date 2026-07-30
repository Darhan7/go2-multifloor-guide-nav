#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements-docs.txt
mkdocs build --clean --strict

echo "Built site/ successfully with strict link checking."
