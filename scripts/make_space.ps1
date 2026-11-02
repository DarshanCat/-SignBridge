<#
Assemble the Hugging Face Space folder (build\hf-space) from the repository: deploy\huggingface-space plus the backend packages the API imports.
No weights, clips or data are copied: the Space downloads them from a private Hugging Face repository at start (docs\DEPLOYMENT.md).
Usage:  .\scripts\make_space.ps1
#>
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root "build\hf-space"
New-Item -ItemType Directory -Force $out | Out-Null
Get-ChildItem $out -Force | Remove-Item -Recurse -Force  # empty it but keep the folder itself (an editor or Docker may hold it open)
Copy-Item "$root\deploy\huggingface-space\*" $out -Recurse
foreach ($d in "app", "nlp", "retarget", "config") { Copy-Item "$root\backend\$d" "$out\$d" -Recurse }
Get-ChildItem $out -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Remove-Item "$out\config\signer_roles.json" -ErrorAction SilentlyContinue  # training-only
Write-Host "Space folder ready: $out"
