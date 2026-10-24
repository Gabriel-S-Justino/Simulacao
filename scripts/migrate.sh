#!/usr/bin/env bash
# Aplica as migrações no banco de DATABASE_URL (local, Docker ou Neon).
# Neon/Vercel: use a URL *direta* (sem "-pooler") para migrações.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root/backend"
: "${DATABASE_URL:?Defina DATABASE_URL}"
.venv/bin/alembic upgrade head
