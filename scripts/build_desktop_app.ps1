param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if ($Clean) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue ".\build", ".\dist"
}

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    py -3 -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[gui,build]"
.\.venv\Scripts\python.exe -m PyInstaller `
    --name spritegen `
    --windowed `
    --onefile `
    --collect-all PySide6 `
    ".\src\spritegen\desktop.py"

Write-Host "Built dist\spritegen.exe"
