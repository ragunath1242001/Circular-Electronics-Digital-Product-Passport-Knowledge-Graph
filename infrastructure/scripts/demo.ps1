param([switch]$Start)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
$baseUrl = "http://localhost:8000"
if ($Start) {
    & docker compose --project-directory $projectRoot up -d --build --wait --wait-timeout 120
    if ($LASTEXITCODE) { throw "The demo stack did not start." }
}

$health = Invoke-RestMethod "$baseUrl/health"
if ($health.status -ne "ok") { throw "Backend health check failed." }
$seed = (Get-Content -Raw -LiteralPath (Join-Path $projectRoot "data/seed/smartphones.json") | ConvertFrom-Json)[0]
try {
    Invoke-RestMethod "$baseUrl/api/v1/products" -Method Post -ContentType "application/json" -Body ($seed | ConvertTo-Json -Depth 5) | Out-Null
} catch {
    if ([int]$_.Exception.Response.StatusCode -ne 409) { throw }
}
$products = Invoke-RestMethod "$baseUrl/api/v1/products?limit=200"
$product = $products | Where-Object product_identifier -eq $seed.product_identifier | Select-Object -First 1
if (-not $product) { throw "The demo product could not be resolved." }
try {
    $passport = Invoke-RestMethod "$baseUrl/api/v1/products/$($product.id)/passport"
} catch {
    if ([int]$_.Exception.Response.StatusCode -ne 404) { throw }
    $passport = Invoke-RestMethod "$baseUrl/api/v1/passports" -Method Post -ContentType "application/json" -Body (@{ product_id = $product.id } | ConvertTo-Json)
}
$validation = Invoke-RestMethod "$baseUrl/api/v1/passports/$($passport.id)/validate" -Method Post
$templates = Invoke-RestMethod "$baseUrl/api/v1/sparql/templates"
$query = Invoke-RestMethod "$baseUrl/api/v1/sparql/query" -Method Post -ContentType "application/json" -Body (@{ query = $templates[0].query; limit = 20 } | ConvertTo-Json)
$graph = Invoke-RestMethod "$baseUrl/api/v1/sparql/graph?product_id=$($product.id)"
$metrics = Invoke-RestMethod "$baseUrl/api/v1/observability/metrics"
$report = Invoke-RestMethod "$baseUrl/api/v1/reports" -Method Post -ContentType "application/json" -Body (@{ report_type = "sustainability" } | ConvertTo-Json)
$artifacts = Join-Path $projectRoot "artifacts"
New-Item -ItemType Directory -Force -Path $artifacts | Out-Null
$reportPath = Join-Path $artifacts "demo-sustainability-report.csv"
$curl = (Get-Command curl.exe -ErrorAction SilentlyContinue).Source
if (-not $curl) { $curl = (Get-Command curl -ErrorAction Stop).Source }
& $curl -fsS "$baseUrl/api/v1/reports/$($report.id)/download" -o $reportPath
if ($LASTEXITCODE) { throw "Demo report download failed." }

Write-Host "DPP portfolio demo passed"
Write-Host "Product: $($product.product_name)"
Write-Host "Passport: $($passport.id), SHACL conforms: $($validation.conforms)"
Write-Host "SPARQL templates: $($templates.Count), sample rows: $($query.rows.Count)"
Write-Host "Graph: $($graph.nodes.Count) nodes / $($graph.edges.Count) edges"
Write-Host "Semantic quality: $($metrics.quality_score)"
Write-Host "Cited report: $reportPath"
