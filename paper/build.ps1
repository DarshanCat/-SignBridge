# Build paper\main.pdf with the MiKTeX that is installed for this user (pdfLaTeX, BibTeX, pdfLaTeX twice). Run from the repository root:  .\paper\build.ps1
$ErrorActionPreference = "Stop"
$bin = "$env:LOCALAPPDATA\Programs\MiKTeX\miktex\bin\x64"
Set-Location (Join-Path $PSScriptRoot ".")
& "$PSScriptRoot\..\backend\.venv\Scripts\python.exe" "$PSScriptRoot\figures\make_figures.py"
& "$bin\miktex-pdftex.exe" -undump=pdflatex -interaction=nonstopmode main.tex | Out-Null
& "$bin\miktex-bibtex.exe" main | Out-Null
& "$bin\miktex-pdftex.exe" -undump=pdflatex -interaction=nonstopmode main.tex | Out-Null
& "$bin\miktex-pdftex.exe" -undump=pdflatex -interaction=nonstopmode main.tex | Select-String "Output written"
