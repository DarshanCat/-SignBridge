# One-time setup (Windows PowerShell). Run from the repository root:  .\scripts\setup.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Push-Location "$root\backend"
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
# CPU build of PyTorch (the API imports it) plus MediaPipe/OpenCV for dataset preprocessing
.\.venv\Scripts\python -m pip install -r requirements-ml.txt --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple
Pop-Location

Push-Location "$root\frontend"
npm install
Pop-Location

Write-Host "Setup complete. Run .\scripts\test.ps1 to verify, .\scripts\dev.ps1 to start."
