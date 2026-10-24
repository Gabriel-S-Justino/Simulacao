# Windows (PowerShell): aplica as migrações no banco de $env:DATABASE_URL.
# Neon/Vercel: use a URL *direta* (DATABASE_URL_UNPOOLED, sem "-pooler").
$ErrorActionPreference = "Stop"
if (-not $env:DATABASE_URL) { throw "Defina DATABASE_URL" }
$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\backend"
# Usa o Python 3 mais recente instalado (o projeto exige 3.12 ou mais novo).
if (-not (Test-Path .venv)) { py -3 -m venv .venv }
if (-not (Test-Path .\.venv\Scripts\alembic.exe)) { .\.venv\Scripts\python -m pip install -q -e . }
.\.venv\Scripts\alembic upgrade head
