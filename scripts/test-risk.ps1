$ErrorActionPreference = "Stop"

Write-Host "Running M4 risk backend tests..." -ForegroundColor Yellow
python -m pytest tests/test_risk_service.py tests/integration/test_api_risk.py -q
if ($LASTEXITCODE -ne 0) { throw "risk pytest failed" }

Write-Host "Running web TypeScript check..." -ForegroundColor Yellow
npm --workspace apps/web exec tsc -- --noEmit
if ($LASTEXITCODE -ne 0) { throw "web typecheck failed" }

Write-Host "M4 risk automation checks passed." -ForegroundColor Green
