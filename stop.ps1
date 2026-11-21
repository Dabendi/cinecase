# 片匣 stop

$ErrorActionPreference = "SilentlyContinue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$port = 8765
$configPath = Join-Path $root "config.json"
if (Test-Path $configPath) {
    try {
        $cfg = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($cfg.port) { $port = [int]$cfg.port }
    } catch {}
}

function Stop-PidFile([string]$file) {
    if (-not (Test-Path $file)) { return }
    $targetPid = Get-Content $file -Raw
    if (-not $targetPid) { return }
    $proc = Get-Process -Id ([int]$targetPid.Trim()) -ErrorAction SilentlyContinue
    if ($proc -and $proc.ProcessName -like "python*") {
        Stop-Process -Id $proc.Id -Force
        Write-Host "已停止 $($proc.ProcessName) (PID $($proc.Id))"
    }
    Remove-Item $file -Force
}

Stop-PidFile "$root\data\scanner.pid"
Stop-PidFile "$root\data\server.pid"

$conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    if ($proc -and $proc.ProcessName -like "python*") {
        Stop-Process -Id $proc.Id -Force
        Write-Host "已停止监听 $port 的服务 (PID $($proc.Id))"
    }
}
Write-Host "片匣已停止。"
