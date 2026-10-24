#!/usr/bin/env bash
# Executa lint, tipos e testes do backend e do frontend.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root/backend"
.venv/bin/ruff check app
.venv/bin/ruff format --check app
.venv/bin/mypy app --exclude app/tests
.venv/bin/pytest -q
cd "$root/frontend"
npm run typecheck
npm test
npm run build
