# Windows (PowerShell): aplica as migrações no banco de $env:DATABASE_URL.
# Neon/Vercel: use a URL *direta* (DATABASE_URL_UNPOOLED, sem "-pooler").
$ErrorActionPreference = "Stop"
if (-not $env:DATABASE_URL) { throw "Defina DATABASE_URL" }
$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\backend"
if (-not (Test-Path .venv)) { py -3.12 -m venv .venv }
.\.venv\Scripts\pip install -q -e .
.\.venv\Scripts\alembic upgrade head
