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
npm --workspace apps/web run dev -- --port $Port
