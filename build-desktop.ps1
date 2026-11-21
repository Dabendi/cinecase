#requires -Version 5.1
# Build the optional Windows desktop app (pywebview + WebView2).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$venv = Join-Path $root ".venv"
$py = Join-Path $venv "Scripts\python.exe"

if (-not (Test-Path $py)) {
    python -m venv $venv
}

& $py -m pip install --upgrade pip
& $py -m pip install -r (Join-Path $root "requirements-desktop.txt")

& $py -m PyInstaller --noconfirm --clean --windowed --onedir --name CineCase `
    --icon (Join-Path $root "assets\cinecase.ico") `
    --add-data "web;web" `
    --add-data "config.example.json;." `
    --add-data "assets;assets" `
    --hidden-import server `
    --hidden-import scan `
    --hidden-import webview.platforms.edgechromium `
    --collect-all webview `
    (Join-Path $root "desktop.py")

Write-Host ""
Write-Host "Built: $(Join-Path $root 'dist\CineCase\CineCase.exe')"
