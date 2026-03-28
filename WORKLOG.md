# 工作日志

## 2026-03-28 14:16:41 +08:00

1. 完成项目文档栈：
   - `polymarket_tail_risk_system_v4_research_prd.md`
   - `polymarket_tail_risk_web_app_architecture_plan.md`
   - `polymarket_tail_risk_m1_m2_backlog.md`
   - `polymarket_tail_risk_wave1_execution_packages.md`
2. 创建可抗断连的 checkpoint 机制：
   - `SESSION_STATUS.md`
   - `SESSION_STATUS.json`
   - `WORKLOG.md`
3. 将下一执行包设为 `PKG-PLAT-01`。

## 2026-03-28 14:32:15 +08:00

1. 完成 `PKG-PLAT-01`。
2. 新增根骨架文件：
   - `.gitignore`
   - `package.json`
   - `requirements.txt`
   - `.env.example`
   - `README.md`
3. 新增本地 bootstrap 脚本：
   - `scripts/bootstrap.ps1`
4. 新增 Wave 1 文档：
   - `docs/environment-variables.md`
   - `docs/logging-fields.md`
   - `infra/README.md`
5. 新增最小可运行服务：
   - `apps/web/*`
   - `apps/api/*`
   - `workers/*`
6. 通过 bootstrap 脚本安装依赖。
7. 验证结果：
   - Web 在 `3000` 端口返回 HTTP 200
   - API `/health` 在 `8000` 端口返回 HTTP 200
   - Celery worker 成功启动
8. 验证后清理生成缓存。
9. 下一执行包：
   - `PKG-DATA-01`
   - `PKG-PLAT-02`

## 2026-03-28 20:46:30 +08:00

1. 完成 `PKG-DATA-01`。
2. 新增数据库基础层：
   - `apps/api/db/base.py`
   - `apps/api/db/session.py`
   - `apps/api/db/models.py`
   - `apps/api/alembic.ini`
   - `apps/api/db/migrations/*`
3. 新增 schema 与迁移文档：
   - `docs/schema/core-schema-v1.md`
   - `docs/schema/index-strategy-v1.md`
   - `docs/runbooks/database-migrations.md`
4. 完成迁移生命周期验证：
   - `upgrade head` 成功
   - `downgrade base` 成功
   - 再次 `upgrade head` 成功
   - 在本地 SQLite 兜底 DB 中确认核心表已创建
5. 完成 `PKG-PLAT-02`。
6. 新增任务运行时基础层：
   - `workers/worker/tasks/base.py`
   - `workers/worker/tasks/system.py`
   - `docs/runbooks/task-runtime.md`
7. 更新运行脚本与环境变量默认值，覆盖：
   - Celery worker
   - Celery beat
   - `db upgrade/downgrade/current`
8. 完成运行时验证：
   - 手动派发 `worker.system.heartbeat` 成功执行
   - Celery beat 启动并成功发送定时心跳任务
   - 根命令 `npm run dev` 验证通过，`web=200`、`api=200`
9. 修复过程中遇到的问题：
   - Alembic 路径解析问题
   - Python 3.14 下 `psycopg[binary]` 兼容版本问题
   - bootstrap 脚本退出码处理问题
   - Celery 任务发现路径问题
10. 下一执行包：
   - `PKG-DATA-02`

## 2026-03-28 21:57:10 +08:00

1. 完成 `PKG-DATA-02`。
2. 新增 Polymarket 采集服务层：
   - `apps/api/services/ingest/contracts.py`
   - `apps/api/services/ingest/polymarket_client.py`
   - `apps/api/services/ingest/service.py`
3. 新增 worker 采集任务：
   - `workers/worker/tasks/ingest.py`
   - `workers/worker/celery_app.py` 增加市场同步与快照调度
4. 扩展 schema 与迁移：
   - `apps/api/db/models.py`
   - `apps/api/db/migrations/versions/20260328_0002_market_ingest_metadata.py`
5. 新增与更新文档：
   - `docs/data-sources/polymarket-public-apis-v1.md`
   - `docs/environment-variables.md`
   - `docs/runbooks/task-runtime.md`
   - `docs/schema/core-schema-v1.md`
   - `docs/schema/index-strategy-v1.md`
   - `README.md`
6. 更新运行脚本与环境变量：
   - `package.json`
   - `.env.example`
   - `apps/api/app/config.py`
   - `workers/worker/config.py`
7. 完成验证：
   - `pip install -r requirements.txt` 成功
   - `python -m compileall apps/api workers` 成功
   - `npm run db:upgrade` 成功，Alembic 升级到 `20260328_0002`
   - 服务层小样本验证成功：`limit_pages=1` 时写入 `1817` 个市场，`market_limit=5` 时写入 `5` 条快照
   - 快照幂等验证成功：同一 `triggered_at` 重跑后 `skipped_existing=5`
   - 全量活跃 feed 同步成功：`pages=99`、`fetched_markets=59148`、`created=8050`、`updated=1149`
   - worker 验证成功：`run_market_catalog_sync(limit_pages=1)` 与 `dispatch_snapshot_capture` 均成功执行
8. 修复与校正：
   - 处理 SQLite 不支持 `ALTER TABLE ADD CONSTRAINT UNIQUE` 的迁移兼容问题
   - 修复 SQLite 读回无时区时间导致的 aware/naive 比较错误
   - 根据真实数据修正 `condition_id` 不应强制唯一的假设
   - 根据真实全量同步耗时，下调默认市场同步频率并为快照任务增加默认市场上限
9. 下一执行包：
   - `PKG-DATA-03`
   - `PKG-PLAT-03`
