# 任务运行手册

## 本地命令

- `npm run dev:worker`
- `npm run dev:beat`
- `npm run task:market-sync`
- `npm run task:snapshot-sync`
- `npm run task:dq-run`
- `npm run task:tagging-run`

## 本地传输方案

Wave 1 当前使用：

- broker：基于 SQLite 的 Celery SQLAlchemy transport
- result backend：基于 SQLite 的结果后端

这样做的目的是让 worker 和 beat 在没有 Redis 的工作站环境中也能正常运行。

## 重试策略

- 短暂失败的 ingest 和 DQ 任务应启用自动重试
- 每个任务必须显式定义重试次数和退避策略
- 每次重试都应记录 task id 和失败原因

## 幂等策略

- 写入类任务必须接收或推导出 idempotency key
- 重复执行不能产生重复业务记录
- 优先使用 upsert 或唯一约束保证写入安全

当前 Wave 1 的具体做法：

- 市场同步任务对 `markets.market_id` 做 upsert，并以 `source_updated_at` 作为本地 watermark
- 快照任务由 dispatcher 先生成固定 `triggered_at`，再交给执行任务写入
- `market_snapshots` 依赖 `(market_ref_id, snapshot_time)` 唯一约束防止重试脏写
- DQ 任务由 dispatcher 先生成固定 `checked_at`，再交给执行任务写入
- `data_quality_results` 依赖 `(market_ref_id, checked_at, rule_version)` 唯一索引防止重试重复落库
- 自动分类结果依赖 `(market_ref_id, rule_version, source_fingerprint)` 唯一索引防止相同市场内容重复落库

## DQ 调度建议

- DQ 默认评估研究模式下的快照覆盖子集，而不是全量 `59k+` 活跃市场
- 建议保持 `DQ_MARKET_LIMIT` 与 `INGEST_SNAPSHOT_MARKET_LIMIT` 一致
- 若快照任务未先覆盖对应市场，DQ 会以 `REJ_DATA_STALE` 或 `REJ_DATA_INCOMPLETE` 输出失败结果

## 自动分类调度建议

- 默认 `TAGGING_RUN_INTERVAL_SECONDS=0`，避免在规则版本仍是实验态时自动刷出大量 `ReviewRequired`
- 建议先手动运行 `npm run task:tagging-run` 验证 active tagging 规则版本，再决定是否打开定时调度
- 自动分类当前默认只扫描研究模式下的活跃市场子集，并以 active tagging 规则版本作为唯一执行基线

## 死信策略

Wave 1 先将失败任务元数据保存在日志和结果后端中。
后续在引入 Redis 或 RabbitMQ 后，再补正式的死信队列。

## 审计联动

- 关键 worker 动作会同步写入 `audit_logs`
- 重试和失败会由 `BaseTask` 自动追加审计记录
- 业务任务成功摘要由各任务模块显式写入审计记录
