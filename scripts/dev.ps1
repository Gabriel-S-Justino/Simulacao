# Windows (PowerShell): inicia backend (8000) e frontend (5173).
$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\backend"
if (-not (Test-Path .venv)) { py -3.12 -m venv .venv }
.\.venv\Scripts\pip install -q -e ".[dev]"
$api = Start-Process -PassThru -NoNewWindow .\.venv\Scripts\uvicorn -ArgumentList "app.main:app","--reload","--port","8000"
try {
  Set-Location "$root\frontend"
  if (-not (Test-Path node_modules)) { npm ci }
  npm run dev
} finally { Stop-Process -Id $api.Id }
