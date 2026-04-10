$ErrorActionPreference = "Stop"

Write-Host "Running worker smoke tests..." -ForegroundColor Yellow
.\.venv\Scripts\python.exe workers/test_new_tasks.py
if ($LASTEXITCODE -ne 0) { throw "worker smoke test failed" }

Write-Host "Worker smoke checks passed." -ForegroundColor Green
