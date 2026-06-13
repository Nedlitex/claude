# Kill whatever is listening on the given TCP ports (default: the admin
# frontend 3000 + backend 8000). Used by the `verify-admin` skill to guarantee
# a clean slate before (re)starting the servers — a stale uvicorn/next dev on
# the port would otherwise make `reuseExistingServer` serve OLD code and the
# browser verification would test the wrong build.
#
# Usage:  pwsh .claude/skills/verify-admin/kill-ports.ps1 [-Ports 3000,8000]
param([int[]]$Ports = @(3000, 8000))

$ErrorActionPreference = "SilentlyContinue"

foreach ($port in $Ports) {
    $conns = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    $pids = @($conns | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -and $_ -ne 0 })
    if ($pids.Count -eq 0) {
        Write-Host "[kill-ports] port $port : nothing listening"
        continue
    }
    foreach ($procId in $pids) {
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        $name = if ($proc) { $proc.ProcessName } else { "?" }
        Write-Host "[kill-ports] port $port : killing PID $procId ($name)"
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
}

# Give the OS a moment to release the sockets.
Start-Sleep -Milliseconds 800
Write-Host "[kill-ports] done"
