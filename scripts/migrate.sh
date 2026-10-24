#!/usr/bin/env bash
# Aplica as migrações no banco de DATABASE_URL (local, Docker ou Neon).
# Neon/Vercel: use a URL *direta* (DATABASE_URL_UNPOOLED, sem "-pooler") para migrações.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root/backend"
: "${DATABASE_URL:?Defina DATABASE_URL}"
[ -d .venv ] || python3 -m venv .venv
[ -x .venv/bin/alembic ] || .venv/bin/python -m pip install -q -e .
.venv/bin/alembic upgrade head
