#!/usr/bin/env bash
# Inicia backend (porta 8000) e frontend (porta 5173) para desenvolvimento.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root/backend"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload --port 8000 &
trap 'kill %1' EXIT
cd "$root/frontend"
[ -d node_modules ] || npm ci
npm run dev
