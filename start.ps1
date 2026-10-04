# AI-based TRPG launcher
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\start.ps1        # use the configured port
#   powershell -ExecutionPolicy Bypass -File .\start.ps1 8090   # use a specific port
#
# Prefers the Python inside .venv when present, otherwise falls back to python on PATH.

$RepositoryRoot = $PSScriptRoot
Set-Location $RepositoryRoot

# Keep Python's UTF-8 output readable in the Windows console
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$venvPython = Join-Path $RepositoryRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
  $python = $venvPython
} else {
  $python = "python"
}

Write-Host "Starting AI-based TRPG (Python: $python)..." -ForegroundColor Cyan

& $python server.py @args
exit $LASTEXITCODE