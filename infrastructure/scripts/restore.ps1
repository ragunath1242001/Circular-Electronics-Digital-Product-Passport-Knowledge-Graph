param(
    [Parameter(Mandatory = $true)][string]$BackupDirectory,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$backupPath = (Resolve-Path -LiteralPath $BackupDirectory).Path
$postgresBackup = Join-Path $backupPath "postgres.sql"
$fusekiBackup = Join-Path $backupPath "fuseki.tar.gz"
$manifestPath = Join-Path $backupPath "manifest.json"
foreach ($path in @($postgresBackup, $fusekiBackup, $manifestPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing backup file: $path" }
}
$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $postgresBackup).Hash -ne $manifest.postgres_sha256 -or
    (Get-FileHash -Algorithm SHA256 -LiteralPath $fusekiBackup).Hash -ne $manifest.fuseki_sha256) {
    throw "Backup integrity check failed."
}
if (-not $Force) {
    $answer = Read-Host "Replace the current PostgreSQL and Fuseki data? Type RESTORE to continue"
    if ($answer -ne "RESTORE") { Write-Host "Restore cancelled."; exit 0 }
}

$postgresId = (& docker compose --project-directory $projectRoot ps -q postgres).Trim()
$fusekiId = (& docker compose --project-directory $projectRoot ps -q fuseki).Trim()
if (-not $postgresId -or -not $fusekiId) {
    throw "PostgreSQL and Fuseki must be running before restore."
}
$fusekiInspect = & docker inspect $fusekiId | ConvertFrom-Json
$fusekiVolume = ($fusekiInspect[0].Mounts | Where-Object Destination -eq "/fuseki/databases").Name
if (-not $fusekiVolume) { throw "The Fuseki database volume could not be resolved." }

& docker compose --project-directory $projectRoot stop frontend backend fuseki
try {
    & docker cp $postgresBackup "${postgresId}:/tmp/dpp-restore.sql"
    if ($LASTEXITCODE) { throw "PostgreSQL restore copy failed." }
    & docker compose --project-directory $projectRoot exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /tmp/dpp-restore.sql'
    if ($LASTEXITCODE) { throw "PostgreSQL restore failed." }
    & docker compose --project-directory $projectRoot exec -T postgres rm -f /tmp/dpp-restore.sql

    & docker run --rm --volume "${fusekiVolume}:/data" --volume "${backupPath}:/backup:ro" alpine:3.20 sh -c 'find /data -mindepth 1 -delete && tar -xzf /backup/fuseki.tar.gz -C /data'
    if ($LASTEXITCODE) { throw "Fuseki restore failed." }
} finally {
    & docker compose --project-directory $projectRoot up -d --wait --wait-timeout 120
}
Write-Host "Restore completed from: $backupPath"
