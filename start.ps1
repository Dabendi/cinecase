# 片匣 start / stop

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$port = 8765
$configPath = Join-Path $root "config.json"
if (Test-Path $configPath) {
    try {
        $cfg = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($cfg.port) { $port = [int]$cfg.port }
    } catch {}
}
$python = (Get-Command python).Source

function Test-Server {
    try {
        $null = Invoke-RestMethod "http://127.0.0.1:$port/api/health" -TimeoutSec 1
        return $true
    } catch {
        return $false
    }
}

if (-not (Test-Server)) {
    Start-Process -FilePath $python `
        -ArgumentList @("-X", "utf8", "server.py", "--port", "$port") `
        -WorkingDirectory $root -WindowStyle Hidden `
        -RedirectStandardOutput "$root\data\logs\server.out.log" `
        -RedirectStandardError "$root\data\logs\server.err.log"
    Write-Host "已启动 Web 服务: http://127.0.0.1:$port"
} else {
    Write-Host "Web 服务已在运行: http://127.0.0.1:$port"
}

$scannerRunning = $false
if (Test-Path "$root\data\scanner.pid") {
    $scannerPid = Get-Content "$root\data\scanner.pid" -ErrorAction SilentlyContinue
    if ($scannerPid) {
        $proc = Get-Process -Id $scannerPid -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -like "python*") {
            $scannerRunning = $true
        }
    }
}
if (-not $scannerRunning -and (Test-Path "$root\data\status.json")) {
    try {
        $status = Get-Content "$root\data\status.json" -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($status.pid) {
            $proc = Get-Process -Id ([int]$status.pid) -ErrorAction SilentlyContinue
            if ($proc -and $proc.ProcessName -like "python*") {
                $scannerRunning = $true
            }
        }
    } catch {}
}

if (-not $scannerRunning) {
    Start-Process -FilePath $python `
        -ArgumentList @("-X", "utf8", "scan.py", "--watch", "--no-initial") `
        -WorkingDirectory $root -WindowStyle Hidden `
        -RedirectStandardOutput "$root\data\logs\scanner.out.log" `
        -RedirectStandardError "$root\data\logs\scanner.err.log"
    Write-Host "已启动后台索引器（只读扫描，低优先级）"
} else {
    Write-Host "后台索引器已在运行"
}

Start-Sleep -Milliseconds 900
Start-Process "http://127.0.0.1:$port/"
