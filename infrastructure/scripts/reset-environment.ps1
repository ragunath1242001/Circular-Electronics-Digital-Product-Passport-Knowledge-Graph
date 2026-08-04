param([switch]$Force)

$ErrorActionPreference = "Stop"
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")

if (-not $Force) {
    $answer = Read-Host "Delete all local DPP containers and data volumes? Type RESET to continue"
    if ($answer -ne "RESET") {
        Write-Host "Reset cancelled."
        exit 0
    }
}

docker compose --project-directory $projectRoot down --volumes --remove-orphans

