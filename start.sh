#!/bin/bash

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "Polymarket Tail Risk - 项目启动脚本"
echo "========================================"
echo ""

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}[错误] 未找到 Node.js，请先安装 Node.js 18+${NC}"
    exit 1
fi

# 检查 Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}[错误] 未找到 Python，请先安装 Python 3.14+${NC}"
    exit 1
fi

# 设置 Python 命令
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
else
    PYTHON_CMD=python
fi

# 显示版本信息
echo -e "${BLUE}[信息] Node.js 版本:${NC}"
node --version
echo -e "${BLUE}[信息] Python 版本:${NC}"
$PYTHON_CMD --version
echo ""

# 检查是否已安装依赖
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}[警告] 未找到 node_modules 目录${NC}"
    echo -e "${BLUE}[信息] 正在安装依赖...${NC}"
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}[错误] 依赖安装失败${NC}"
        exit 1
    fi
    echo -e "${GREEN}[成功] 依赖安装完成${NC}"
    echo ""
fi

# 检查 Python 虚拟环境
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}[警告] 未找到 Python 虚拟环境${NC}"
    echo -e "${BLUE}[信息] 正在创建虚拟环境...${NC}"
    $PYTHON_CMD -m venv .venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}[错误] 虚拟环境创建失败${NC}"
        exit 1
    fi
    echo -e "${GREEN}[成功] 虚拟环境创建完成${NC}"
    echo ""
fi

# 检查数据库
if [ ! -f "apps/api/var/data/ptr_dev.sqlite3" ]; then
    echo -e "${YELLOW}[警告] 未找到数据库文件${NC}"
    echo -e "${BLUE}[信息] 正在运行数据库迁移...${NC}"
    npm run db:upgrade
    if [ $? -ne 0 ]; then
        echo -e "${RED}[错误] 数据库迁移失败${NC}"
        exit 1
    fi
    echo -e "${GREEN}[成功] 数据库迁移完成${NC}"
    echo ""
fi

# 启动服务
echo "========================================"
echo "正在启动所有服务..."
echo "========================================"
echo ""
echo -e "${GREEN}[信息] Web 前端: http://localhost:3000${NC}"
echo -e "${GREEN}[信息] API 后端: http://localhost:8000${NC}"
echo -e "${GREEN}[信息] API 文档: http://localhost:8000/docs${NC}"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

npm run dev
