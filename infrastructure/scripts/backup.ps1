param([string]$OutputDirectory)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path (Join-Path $projectRoot "backups") (Get-Date -Format "yyyyMMdd-HHmmss")
}
if (Test-Path -LiteralPath $OutputDirectory) {
    if (Get-ChildItem -LiteralPath $OutputDirectory -Force) {
        throw "Backup directory must be empty: $OutputDirectory"
    }
} else {
    New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
}
$backupPath = (Resolve-Path -LiteralPath $OutputDirectory).Path
$postgresId = (& docker compose --project-directory $projectRoot ps -q postgres).Trim()
$fusekiId = (& docker compose --project-directory $projectRoot ps -q fuseki).Trim()
if (-not $postgresId -or -not $fusekiId) {
    throw "PostgreSQL and Fuseki must be running before backup."
}
$fusekiInspect = & docker inspect $fusekiId | ConvertFrom-Json
$fusekiVolume = ($fusekiInspect[0].Mounts | Where-Object Destination -eq "/fuseki/databases").Name
if (-not $fusekiVolume) {
    throw "The Fuseki database volume could not be resolved."
}

& docker compose --project-directory $projectRoot exec -T postgres sh -c 'pg_dump --clean --if-exists --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /tmp/dpp-backup.sql'
if ($LASTEXITCODE) { throw "PostgreSQL backup failed." }
& docker cp "${postgresId}:/tmp/dpp-backup.sql" (Join-Path $backupPath "postgres.sql")
if ($LASTEXITCODE) { throw "PostgreSQL backup copy failed." }
& docker compose --project-directory $projectRoot exec -T postgres rm -f /tmp/dpp-backup.sql

& docker compose --project-directory $projectRoot stop fuseki
try {
    & docker run --rm --volume "${fusekiVolume}:/data:ro" --volume "${backupPath}:/backup" alpine:3.20 tar -czf /backup/fuseki.tar.gz -C /data .
    if ($LASTEXITCODE) { throw "Fuseki backup failed." }
} finally {
    & docker compose --project-directory $projectRoot up -d fuseki
}

$manifest = @{
    format_version = 1
    created_at = (Get-Date).ToUniversalTime().ToString("o")
    postgres_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $backupPath "postgres.sql")).Hash
    fuseki_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $backupPath "fuseki.tar.gz")).Hash
}
$manifest | ConvertTo-Json | Set-Content -Encoding utf8 -LiteralPath (Join-Path $backupPath "manifest.json")
Write-Host "Backup completed: $backupPath"
