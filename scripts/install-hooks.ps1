# Point git at the versioned hooks in scripts/hooks (run once per clone).
$root = Split-Path -Parent $PSScriptRoot
git -C $root config core.hooksPath scripts/hooks
"core.hooksPath = scripts/hooks"
