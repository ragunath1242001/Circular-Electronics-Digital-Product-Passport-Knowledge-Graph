$ErrorActionPreference = "Stop"
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$environmentFile = Join-Path $projectRoot ".env"

if (-not (Test-Path -LiteralPath $environmentFile)) {
    Copy-Item -LiteralPath (Join-Path $projectRoot ".env.example") -Destination $environmentFile
    Write-Host "Created .env from .env.example. Change the placeholder secrets before deployment."
}

docker compose --project-directory $projectRoot up --build

