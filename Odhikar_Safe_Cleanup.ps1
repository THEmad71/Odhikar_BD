
param(
    [string]$ProjectRoot = 'C:\Odhikar_Bd',
    [switch]$Apply
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$archiveRoot = Join-Path $ProjectRoot '_cleanup_archive'

$targets = @(
    'src\odhikar\graph.py.bak',
    'src\odhikar\graph.py.backup'
)

Write-Host "Project: $ProjectRoot"
Write-Host "Mode: $(if ($Apply) {'MOVE TO ARCHIVE'} else {'PREVIEW ONLY'})"

foreach ($relative in $targets) {
    $source = Join-Path $ProjectRoot $relative

    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        Write-Host "SKIP (not found): $relative"
        continue
    }

    $hash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash

    Write-Host "Candidate: $relative | SHA256: $hash"

    if ($Apply) {
        $destination = Join-Path $archiveRoot $relative
        $parent = Split-Path -Parent $destination

        New-Item -ItemType Directory -Force -Path $parent | Out-Null

        if (Test-Path -LiteralPath $destination) {
            throw "Archive destination already exists: $destination. No overwrite performed."
        }

        Move-Item -LiteralPath $source -Destination $destination

        Write-Host "ARCHIVED: $relative"
    }
}

Write-Host 'No source code, legal documents, database or active indexes deleted.'
