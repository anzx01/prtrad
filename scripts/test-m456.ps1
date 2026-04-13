$ErrorActionPreference = "Stop"

Write-Host "Running M4-M6 backend tests..." -ForegroundColor Yellow
python -m pytest `
  tests/test_db_migrations.py `
  tests/test_risk_service.py `
  tests/test_backtest_service.py `
  tests/test_shadow_service.py `
  tests/test_launch_review_service.py `
  tests/test_reports_service.py `
  tests/integration/test_api_risk.py `
  tests/integration/test_api_backtests.py `
  tests/integration/test_api_shadow.py `
  tests/integration/test_api_launch_review.py `
  tests/integration/test_api_reports.py `
  -q
if ($LASTEXITCODE -ne 0) { throw "m4-m6 pytest failed" }

Write-Host "Running web TypeScript check..." -ForegroundColor Yellow
npm --workspace apps/web exec tsc -- --noEmit
if ($LASTEXITCODE -ne 0) { throw "web typecheck failed" }

Write-Host "M4-M6 automation checks passed." -ForegroundColor Green
