$ErrorActionPreference = "Stop"

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

$directories = @(
    "var",
    "var\\data",
    "var\\celery"
)

foreach ($directory in $directories) {
    if (-not (Test-Path $directory)) {
        New-Item -ItemType Directory -Path $directory | Out-Null
    }
}

$python = Join-Path ".venv" "Scripts\\python.exe"
$pip = Join-Path ".venv" "Scripts\\pip.exe"

& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }

& $pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "dependency installation failed" }

npm install
if ($LASTEXITCODE -ne 0) { throw "npm install failed" }

Write-Host "Bootstrap complete. Activate with .\\.venv\\Scripts\\Activate.ps1 if needed."
