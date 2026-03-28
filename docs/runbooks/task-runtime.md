# 任务运行手册

## 本地命令

- `npm run dev:worker`
- `npm run dev:beat`
- `npm run task:market-sync`
- `npm run task:snapshot-sync`

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

## 死信策略

Wave 1 先将失败任务元数据保存在日志和结果后端中。
后续在引入 Redis 或 RabbitMQ 后，再补正式的死信队列。
