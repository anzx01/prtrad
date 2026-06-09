param(
  [int]$Port = 0
)

$ErrorActionPreference = "Stop"

if ($Port -le 0) {
  $envPort = $env:WEB_PORT
  if ($envPort -match '^\d+$') {
    $Port = [int]$envPort
  } else {
    $Port = 3001
  }
}

Write-Host ("启动前端开发服务器，端口: {0}" -f $Port) -ForegroundColor Green
$repoRoot = Split-Path -Parent $PSScriptRoot
$nextBin = Join-Path $repoRoot "node_modules/.bin/next.cmd"
if (-not (Test-Path $nextBin)) {
  throw "Next.js executable not found. Run npm install first."
}

Push-Location (Join-Path $repoRoot "apps/web")
try {
  & $nextBin dev --port $Port
} finally {
  Pop-Location
}
