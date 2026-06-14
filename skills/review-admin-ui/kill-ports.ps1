# Kill whatever is listening on the given TCP ports. The review skill calls this
# on its CHOSEN review pair (from pick-ports.ps1) for a clean slate before start
# and for teardown after. Defaults to the review band's first pair, NOT 3000/8000,
# so an accidental bare run never kills the user's dev portal.
#
# Usage:  pwsh .claude/skills/review-admin-ui/kill-ports.ps1 -Ports 3090,8090
param([int[]]$Ports = @(3090, 8090))

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

Start-Sleep -Milliseconds 800
Write-Host "[kill-ports] done"
