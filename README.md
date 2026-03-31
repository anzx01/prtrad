# Polymarket Tail Risk

这是 Polymarket Tail Risk Web 应用的 Wave 1 最小可运行骨架。

## 目录结构

- `apps/web`：Next.js Web 控制台
- `apps/api`：FastAPI 服务
- `workers`：Celery Worker 入口
- `infra`：基础设施说明与后续部署预留
- `docs`：环境变量、日志、迁移、运行手册等文档
- `scripts`：本地启动与辅助脚本

## 快速开始

1. 运行 `npm install`
2. 运行 `powershell -ExecutionPolicy Bypass -File ./scripts/bootstrap.ps1`
3. 运行 `npm run dev`

当前 Wave 1 使用基于 SQLite 的 Celery broker/result backend，因此在本地无需 Redis 也能启动 worker 和 beat。

## 服务端口

- Web：`http://localhost:3000`
- API：`http://localhost:8000`

## 数据库辅助命令

- `npm run db:upgrade`
- `npm run db:downgrade`
- `npm run db:current`

## 采集辅助命令

- `npm run task:market-sync`
- `npm run task:snapshot-sync`
- `npm run task:dq-run`
- `npm run task:tagging-run`
