#requires -Version 5.1
# Build the optional Windows desktop app (pywebview + WebView2 + bundled ffmpeg).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

function Get-Download([string]$url, [string]$out) {
    if (Test-Path $out) { return }
    New-Item -ItemType Directory -Force (Split-Path -Parent $out) | Out-Null
    Write-Host "Downloading $url"
    if (Get-Command curl.exe -ErrorAction SilentlyContinue) {
        & curl.exe -L --fail -o $out $url
        if ($LASTEXITCODE -ne 0) { throw "Download failed: $url" }
    } else {
        Invoke-WebRequest -Uri $url -OutFile $out
    }
}

$ffmpegUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-lgpl-shared.zip"
$webview2Url = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
$ffmpegDir = Join-Path $root "vendor\ffmpeg"

if (-not (Test-Path (Join-Path $ffmpegDir "ffmpeg.exe"))) {
    $stage = Join-Path $root "vendor\_ffmpeg_build"
    $zip = Join-Path $stage "ffmpeg.zip"
    Get-Download $ffmpegUrl $zip
    $extract = Join-Path $stage "extract"
    if (-not (Test-Path $extract)) {
        Expand-Archive -Path $zip -DestinationPath $extract -Force
    }
    $bin = Get-ChildItem $extract -Recurse -Directory -Filter bin | Select-Object -First 1
    if (-not $bin) { throw "ffmpeg bin directory not found" }
    New-Item -ItemType Directory -Force $ffmpegDir | Out-Null
    Copy-Item (Join-Path $bin.FullName "*") $ffmpegDir -Force
    Remove-Item (Join-Path $ffmpegDir "ffplay.exe") -Force -ErrorAction SilentlyContinue
    $license = Get-ChildItem $extract -Recurse -File -Filter "LICENSE.txt" | Select-Object -First 1
    if ($license) { Copy-Item $license.FullName (Join-Path $ffmpegDir "LICENSE.txt") -Force }
}

$webview2Dir = Join-Path $root "vendor\webview2"
$webview2 = Join-Path $webview2Dir "MicrosoftEdgeWebView2Setup.exe"
Get-Download $webview2Url $webview2
$sig = Get-AuthenticodeSignature $webview2
if ($sig.Status -ne "Valid") {
    throw "WebView2 bootstrapper signature is not valid: $($sig.Status)"
}

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
    --add-data "vendor\ffmpeg;ffmpeg" `
    --add-data "vendor\webview2;webview2" `
    --hidden-import server `
    --hidden-import scan `
    --hidden-import webview.platforms.edgechromium `
    --collect-all webview `
    (Join-Path $root "desktop.py")

$dist = Join-Path $root "dist\CineCase"
Copy-Item (Join-Path $root "README-FIRST.txt") $dist -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $root "THIRD_PARTY_NOTICES.md") $dist -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $root "config.example.json") $dist -Force

Write-Host ""
Write-Host "Built: $(Join-Path $dist 'CineCase.exe')"
