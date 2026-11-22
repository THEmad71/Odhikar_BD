
param([string]$ProjectRoot='C:\Odhikar_Bd')

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path -LiteralPath $ProjectRoot).Path
$reportDir = Join-Path $root '_cleanup_audit'

New-Item -ItemType Directory -Path $reportDir -Force | Out-Null

$skip = @(
    '.venv',
    'venv',
    'node_modules',
    '.git',
    '__pycache__',
    '_cleanup_audit',
    '_cleanup_archive'
)

$stack = New-Object System.Collections.Stack
$stack.Push($root)

$files = New-Object 'System.Collections.Generic.List[object]'

while ($stack.Count -gt 0) {
    $here = [string]$stack.Pop()

    foreach ($item in (Get-ChildItem -LiteralPath $here -Force -ErrorAction SilentlyContinue)) {

        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            continue
        }

        if ($item.PSIsContainer) {
            if ($item.Name -notin $skip) {
                $stack.Push($item.FullName)
            }
        }
        elseif (
            $item.Length -gt 0 -and
            $item.Extension -in @('.pdf','.txt','.jsonl','.json','.png','.csv')
        ) {
            $files.Add($item)
        }
    }
}

# Hash files with matching sizes only
$results = foreach (
    $group in ($files | Group-Object Length | Where-Object Count -gt 1)
) {
    foreach ($file in $group.Group) {
        [pscustomobject]@{
            FullName = $file.FullName
            Bytes    = $file.Length
            SHA256   = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        }
    }
}

# Identify exact duplicates
$dupes = @(
    $results |
    Group-Object SHA256 |
    Where-Object Count -gt 1 |
    ForEach-Object {
        $digest = $_.Name

        foreach ($entry in $_.Group) {
            [pscustomobject]@{
                SHA256   = $digest
                FullName = $entry.FullName
                Bytes    = $entry.Bytes
            }
        }
    }
)

$output = Join-Path $reportDir 'exact_duplicates_SHA256.csv'

$dupes |
    Export-Csv -LiteralPath $output -NoTypeInformation -Encoding UTF8

Write-Host "Exact duplicate report: $output"
Write-Host "Duplicate instances: $($dupes.Count)"
Write-Host 'READ-ONLY: no files were moved or deleted.'
