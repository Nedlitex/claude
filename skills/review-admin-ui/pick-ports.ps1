# Find a FREE (frontend, backend) port pair for an isolated admin-UI review run,
# so the review never collides with a dev portal on the default 3000/8000.
#
# Scans the high "review" band (frontend 3090..3099, backend 8090..8099) and
# returns the first pair where BOTH ports are free. Prints two lines the caller
# parses:
#     FPORT=3090
#     BPORT=8090
#
# Usage:  pwsh .claude/skills/review-admin-ui/pick-ports.ps1
#         pwsh .claude/skills/review-admin-ui/pick-ports.ps1 -FrontStart 3110 -BackStart 8110

param(
    [int]$FrontStart = 3090,
    [int]$BackStart  = 8090,
    [int]$Span       = 10
)

$ErrorActionPreference = "SilentlyContinue"

function Test-PortFree([int]$port) {
    $conn = Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue
    return ($null -eq $conn)
}

$fport = $null
$bport = $null
for ($i = 0; $i -lt $Span; $i++) {
    $f = $FrontStart + $i
    $b = $BackStart + $i
    if ((Test-PortFree $f) -and (Test-PortFree $b)) {
        $fport = $f
        $bport = $b
        break
    }
}

if ($null -eq $fport) {
    Write-Error "[pick-ports] no free (frontend,backend) pair found in $FrontStart..$($FrontStart+$Span-1) / $BackStart..$($BackStart+$Span-1). Free some ports or pass -FrontStart/-BackStart."
    exit 1
}

Write-Host "FPORT=$fport"
Write-Host "BPORT=$bport"
