# Start backend and frontend in two windows. Usage:  .\scripts\dev.ps1 [-ApiPort 8000] [-WebPort 3000]
# Pick other ports if these are busy; CORS and the API URL are set to match (child windows inherit these variables).
param([int]$ApiPort = 8000, [int]$WebPort = 3000)
$root = Split-Path -Parent $PSScriptRoot

$env:SIGNBRIDGE_CORS_ORIGINS = '["http://localhost:' + $WebPort + '"]'
$env:NEXT_PUBLIC_API_URL = "http://localhost:$ApiPort"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\backend'; .\.venv\Scripts\python -m uvicorn app.main:app --port $ApiPort"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev -- -p $WebPort"
Write-Host "Backend: http://localhost:$ApiPort (docs at /docs)   Frontend: http://localhost:$WebPort"
