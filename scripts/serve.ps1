# Production style run (recommended): builds the frontend once, then serves it with `next start` next to the API.
# Usage:  .\scripts\serve.ps1 [-ApiPort 8000] [-WebPort 3000] [-SkipBuild]
# NEXT_PUBLIC_API_URL is baked in at build time, so a changed ApiPort needs a rebuild (do not pass -SkipBuild then).
param([int]$ApiPort = 8000, [int]$WebPort = 3000, [switch]$SkipBuild)
$root = Split-Path -Parent $PSScriptRoot

$env:SIGNBRIDGE_CORS_ORIGINS = '["http://localhost:' + $WebPort + '","http://127.0.0.1:' + $WebPort + '"]'
$env:NEXT_PUBLIC_API_URL = "http://127.0.0.1:$ApiPort"

if (-not $SkipBuild) {
    Push-Location "$root\frontend"
    npm run build
    if ($LASTEXITCODE -ne 0) { Pop-Location; throw "frontend build failed" }
    Pop-Location
}
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; .\.venv\Scripts\python -m uvicorn app.main:app --port $ApiPort"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm start -- -p $WebPort"
Write-Host "API: http://127.0.0.1:$ApiPort (docs at /docs)   Web: http://localhost:$WebPort   (the API needs about 15 s to start: it loads spaCy and the model)"
