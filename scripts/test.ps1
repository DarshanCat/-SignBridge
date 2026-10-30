# Run every automated check. Stop the frontend dev server first: `next build` and `next dev` share the .next folder.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Push-Location "$root\backend"
.\.venv\Scripts\python -m pytest -q
$backend = $LASTEXITCODE
Pop-Location

Push-Location "$root\frontend"
npx tsc --noEmit;  $tsc = $LASTEXITCODE
npm run lint;      $lint = $LASTEXITCODE
npm test;          $unit = $LASTEXITCODE
npm run build;     $build = $LASTEXITCODE
Pop-Location

"backend pytest=$backend  tsc=$tsc  lint=$lint  vitest=$unit  build=$build  (0 means passed)"
if (($backend + $tsc + $lint + $unit + $build) -ne 0) { exit 1 }
