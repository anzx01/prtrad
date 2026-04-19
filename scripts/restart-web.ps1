# 重启前端开发服务器（解决 Windows EPERM .next/trace 锁文件问题）

Write-Host "停止所有 node 进程..." -ForegroundColor Yellow
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force

Start-Sleep -Seconds 2

Write-Host "清理 .next 目录..." -ForegroundColor Yellow
Remove-Item -Path "$PSScriptRoot\..\apps\web\.next" -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "启动前端开发服务器..." -ForegroundColor Green
powershell -ExecutionPolicy Bypass -File "$PSScriptRoot\dev-web.ps1"
