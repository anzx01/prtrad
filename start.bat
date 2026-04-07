@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo ========================================
echo Polymarket Tail Risk - 项目启动脚本
echo ========================================
echo.

where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Node.js，请先安装 Node.js 18+
    pause
    exit /b 1
)

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python，请先安装 Python 3.13+
    pause
    exit /b 1
)

echo [信息] Node.js 版本:
node --version
echo [信息] Python 版本:
python --version
echo.

if not exist "node_modules\" (
    echo [警告] 未找到 node_modules 目录
    echo [信息] 正在安装依赖...
    call npm install
    if %errorlevel% neq 0 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
    echo [成功] 依赖安装完成
    echo.
)

if not exist ".venv\" (
    echo [警告] 未找到 Python 虚拟环境
    echo [信息] 正在创建虚拟环境...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [错误] 虚拟环境创建失败
        pause
        exit /b 1
    )
    echo [成功] 虚拟环境创建完成
    echo.
)

echo [信息] 正在执行数据库迁移...
call npm run db:upgrade
if %errorlevel% neq 0 (
    echo [错误] 数据库迁移失败
    pause
    exit /b 1
)
echo [成功] 数据库已迁移到最新版本
if exist "var\data\ptr_dev.sqlite3" (
    echo [信息] 当前开发库: var\data\ptr_dev.sqlite3
)
echo.

echo ========================================
echo 正在启动所有服务...
echo ========================================
echo.
echo [信息] Web 前端: http://localhost:3000
echo [信息] API 后端: http://localhost:8000
echo [信息] API 文档: http://localhost:8000/docs
echo.
echo 按 Ctrl+C 停止所有服务
echo.

call npm run dev

endlocal
