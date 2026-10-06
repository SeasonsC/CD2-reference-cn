# CD2 Reference v2 - one-click build
# Usage: powershell -NoProfile -ExecutionPolicy Bypass -File tools\build.ps1
#
# NOTE: keep this file ASCII-only. Windows PowerShell 5.1 reads .ps1 as ANSI/GBK
# unless a UTF-8 BOM is present, which silently corrupts non-ASCII string literals.
$ErrorActionPreference = 'Stop'
# Python interpreter: set $env:CD2_PYTHON to override, else use 'python' from PATH.
$PY = if ($env:CD2_PYTHON) { $env:CD2_PYTHON } else { 'python' }
$ROOT = Split-Path -Parent $PSScriptRoot
$env:PYTHONIOENCODING = 'utf-8'

foreach ($step in @('extract.py', 'build_media.py', 'build_assets.py', 'render.py')) {
    Write-Host "`n=== $step ===" -ForegroundColor Cyan
    & $PY (Join-Path $PSScriptRoot $step)
    if ($LASTEXITCODE -ne 0) { throw "$step failed" }
}

Write-Host "`n=== verify.py ===" -ForegroundColor Cyan
& $PY (Join-Path $PSScriptRoot 'verify.py')

Write-Host "`nBuild finished. Publish source (GitHub Pages: main + /docs):" -ForegroundColor Green
Write-Host ("  {0}\docs" -f $ROOT)
Write-Host "Local preview:"
Write-Host ("  {0} -m http.server 8767 --bind 127.0.0.1 --directory `"{1}\docs`"" -f $PY, $ROOT)
