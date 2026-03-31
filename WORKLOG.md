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

## 2026-03-29 07:04:04 +08:00

1. 完成 `PKG-DATA-03`。
2. 新增 DQ 服务层：
   - `apps/api/services/dq/contracts.py`
   - `apps/api/services/dq/service.py`
3. 新增 DQ worker 任务：
   - `workers/worker/tasks/dq.py`
   - `workers/worker/celery_app.py` 增加 DQ dispatcher 调度
4. 扩展 schema 与迁移：
   - `apps/api/db/models.py`
   - `apps/api/db/migrations/versions/20260329_0003_dq_result_idempotency.py`
5. 新增与更新文档：
   - `docs/dq/rules-v1.md`
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
   - `python -m compileall apps/api workers` 成功
   - `npm run db:upgrade` 成功，Alembic 升级到 `20260329_0003`
   - 服务层验证成功：先执行 `capture_snapshots(market_limit=20)`，再执行 `evaluate_markets(market_limit=20)`，得到 `pass=11`、`fail=9`
   - DQ 幂等验证成功：同一 `checked_at` 重跑后 `skipped_existing=5`
   - worker 验证成功：`dispatch_snapshot_capture` 与 `dispatch_market_dq_scan` 均成功执行
   - DQ 结果已落库：当前 `data_quality_results=38`，状态分布为 `pass=16`、`fail=22`
   - beat 调度项已包含 `dispatch-market-dq-scan`
8. 修复与校正：
   - 为 DQ 结果增加 `(market_ref_id, checked_at, rule_version)` 唯一索引，保证重试幂等
   - 将 DQ 告警日志改为由 worker 输出，确保日志带 `task_id`
   - 对齐 ORM 模型与 SQLite 实际迁移结果，避免后续 schema 漂移
9. 当前 DQ v1 边界：
   - 默认只评估研究模式下的快照覆盖子集
   - `trade_count` 与 `last_trade_age_seconds` 尚未纳入硬性 DQ 规则
   - 重复市场识别当前仅为保守版签名检测
10. 下一执行包：
   - `PKG-PLAT-03`
   - `PKG-RISK-01`

## 2026-03-29 07:23:12 +08:00

1. 完成 `PKG-PLAT-03`。
2. 新增统一审计组件：
   - `apps/api/services/audit/contracts.py`
   - `apps/api/services/audit/service.py`
   - `workers/common/audit.py`
3. 新增 API 中间件：
   - `apps/api/middleware/request_context.py`
   - `apps/api/app/main.py` 接入请求上下文与请求审计
4. 更新 worker 任务链路：
   - `workers/worker/tasks/base.py` 新增重试/失败自动审计
   - `workers/worker/tasks/ingest.py` 新增市场同步与快照采集审计
   - `workers/worker/tasks/dq.py` 新增 DQ 派发与执行审计
5. 新增与更新文档：
   - `docs/audit/field-dictionary-v1.md`
   - `docs/audit/key-events-v1.md`
   - `docs/logging-fields.md`
   - `docs/runbooks/task-runtime.md`
6. 完成验证：
   - `python -m compileall apps/api workers` 成功
   - FastAPI `TestClient` 请求 `/health` 成功，并写入 `api_request` 审计记录
   - worker 快照任务成功执行，并写入 `market_snapshot_capture` 的 `dispatch/execute` 审计记录
   - worker DQ 任务成功执行，并写入 `market_dq_scan` 的 `dispatch/execute` 审计记录
   - 通过传入非法 `checked_at` 验证了 `worker_task` 的 `retry_scheduled` 与 `execute failed` 审计记录
   - 当前 `audit_logs=9`，对象分布：
     - `api_request=1`
     - `market_snapshot_capture=2`
     - `market_dq_scan=2`
     - `worker_task=4`
7. 修复与校正：
   - 将请求上下文生成逻辑从 `main.py` 提炼到中间件
   - 审计写入失败默认降级为日志，不阻塞主业务流程
   - 为任务失败和重试增加统一公共 helper，避免各任务重复实现
8. 下一执行包：
   - `PKG-RISK-01`

## 2026-03-29 09:15:31 +08:00

1. 完成 `PKG-RISK-01`。
2. 新增 tagging 服务层：
   - `apps/api/services/tagging/contracts.py`
   - `apps/api/services/tagging/service.py`
   - `apps/api/services/tagging/__init__.py`
3. 扩展 schema 与迁移：
   - `apps/api/db/models.py`
   - `apps/api/db/migrations/versions/20260329_0004_tagging_rule_foundation.py`
4. 新增与更新文档：
   - `docs/tagging/rules-and-versioning-v1.md`
   - `docs/tagging/default-dictionary-v1.md`
   - `docs/schema/core-schema-v1.md`
   - `docs/schema/index-strategy-v1.md`
5. 完成能力：
   - 标签字典模型（一级类别 / 风险因子 / 白灰黑名单桶）
   - 规则版本模型（`draft` / `active` / `superseded`）
   - 规则明细模型（匹配范围、匹配算子、动作类型、优先级、启停）
   - 默认标签字典 seed
   - 规则版本创建、激活、回滚与审计写入
6. 完成验证：
   - `python -m compileall apps/api` 成功
   - `npm run db:upgrade` 成功，Alembic 升级到 `20260329_0004`
   - 默认字典 seed 成功：`created=24`、`updated=0`
   - 规则版本烟测成功：
     - `tag_v1_20260329_smoke1` 创建并激活
     - `tag_v1_20260329_smoke2` 创建并激活
     - `tag_v1_20260329_rb1` 从 `tag_v1_20260329_smoke1` 回滚克隆并激活
   - 当前 active tagging 版本：`tag_v1_20260329_rb1`
   - 当前 `audit_logs=15`，新增对象分布：
     - `tag_dictionary_catalog=1`
     - `tag_rule_version=5`
7. 修复与校正：
   - 回滚采用“克隆新版本并激活”的方式，而不是直接重激活旧版本，避免审计链路歧义
   - 规则版本保存 `dictionary_snapshot` 与 `checksum`，保证后续分类复算一致性
   - active 版本切换由服务层统一处理，旧 active 版本自动转为 `superseded`
8. 下一执行包：
   - `PKG-RISK-02`

## 2026-03-29 09:47:06 +08:00

1. 完成 `PKG-RISK-02`。
2. 新增自动分类服务层：
   - `apps/api/services/tagging/classifier.py`
3. 扩展 schema 与迁移：
   - `apps/api/db/models.py`
   - `apps/api/db/migrations/versions/20260329_0005_market_auto_tagging_results.py`
4. 新增 worker 自动分类任务：
   - `workers/worker/tasks/tagging.py`
   - `workers/worker/celery_app.py` 接入 `worker.tasks.tagging` 与可选调度 `dispatch-market-auto-tagging`
5. 更新运行与环境文档：
   - `.env.example`
   - `package.json`
   - `README.md`
   - `docs/environment-variables.md`
   - `docs/runbooks/task-runtime.md`
   - `docs/schema/core-schema-v1.md`
   - `docs/schema/index-strategy-v1.md`
   - `docs/audit/field-dictionary-v1.md`
   - `docs/audit/key-events-v1.md`
   - `docs/tagging/auto-classification-v1.md`
6. 完成能力：
   - 自动分类结果落库（`market_classification_results`）
   - 标签分配落库（`market_tag_assignments`）
   - 分类解释落库（`market_tag_explanations`）
   - 人工复核待办落库（`market_review_tasks`）
   - worker 自动分类派发/执行任务与审计写入
7. 完成验证：
   - `python -m compileall apps/api workers` 成功
   - `npm run db:upgrade` 成功，Alembic 升级到 `20260329_0005`
   - `npm run db:current` 显示 `20260329_0005 (head)`
   - 服务层烟测成功：`market_limit=10` 时 `created=10`、`Tagged=2`、`ReviewRequired=8`、`review_tasks_created=8`
   - 幂等验证成功：
     - 服务层同一 `classified_at` 重跑：`created=0`、`skipped_existing=5`
     - worker 同一 `classified_at` 重跑：`created=0`、`skipped_existing=5`
   - 当前分类相关数据量：
     - `market_classification_results=10`
     - `market_tag_assignments=12`
     - `market_tag_explanations=28`
     - `market_review_tasks=8`
   - 当前 `audit_logs=19`，新增对象：`market_auto_tagging=3`
8. 修复与校正：
   - 修复自动分类任务在重试/并发下的唯一索引竞态：改为 nested transaction + `IntegrityError` 幂等降级为 `skipped_existing`
   - 自动分类定时调度默认关闭（`TAGGING_RUN_INTERVAL_SECONDS=0`），避免实验规则误触发大规模复核积压
9. 下一执行包：
   - `PKG-RISK-03`
