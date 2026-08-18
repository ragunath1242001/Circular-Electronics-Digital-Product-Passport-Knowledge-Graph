param([switch]$Start)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
if ($Start) {
    & docker compose --project-directory $projectRoot up -d --build --wait --wait-timeout 180
    if ($LASTEXITCODE) { throw "The observatory stack did not start." }
}

$container = (& docker compose --project-directory $projectRoot ps -q backend).Trim()
if (-not $container) { throw "The backend container is not running. Use -Start." }

& docker exec $container mkdir -p /eval/scripts /eval/data/synthetic/generated /eval/artifacts
$copies = @(
    @("scripts/__init__.py", "/eval/scripts/__init__.py"),
    @("scripts/generate_synthetic.py", "/eval/scripts/generate_synthetic.py"),
    @("scripts/evaluate_observatory.py", "/eval/scripts/evaluate_observatory.py"),
    @("data/detectors.json", "/eval/data/detectors.json"),
    @("data/synthetic/scenario.json", "/eval/data/synthetic/scenario.json"),
    @("data/synthetic/generated/ground-truth.jsonl", "/eval/data/synthetic/generated/ground-truth.jsonl"),
    @("data/synthetic/generated/summary.json", "/eval/data/synthetic/generated/summary.json")
)
foreach ($copy in $copies) {
    & docker cp (Join-Path $projectRoot $copy[0]) "${container}:$($copy[1])"
    if ($LASTEXITCODE) { throw "Could not stage $($copy[0]) for evaluation." }
}

& docker exec -w /eval $container python -m scripts.evaluate_observatory `
    --base-url http://localhost:8000
if ($LASTEXITCODE) { throw "The observatory evaluation failed." }

$artifacts = Join-Path $projectRoot "artifacts"
New-Item -ItemType Directory -Force -Path $artifacts | Out-Null
& docker cp "${container}:/eval/artifacts/observatory-evaluation.json" `
    (Join-Path $artifacts "observatory-evaluation.json")
& docker cp "${container}:/eval/artifacts/observatory-evaluation.md" `
    (Join-Path $artifacts "observatory-evaluation.md")
if ($LASTEXITCODE) { throw "Could not copy the evaluation report." }

Write-Host "Semantic Observatory evaluation passed"
Write-Host "Reports: $artifacts"
