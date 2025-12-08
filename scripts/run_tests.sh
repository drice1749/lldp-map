#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -d .venv ]]; then
  source .venv/bin/activate
fi

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

pytest "$@"
