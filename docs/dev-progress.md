# 开发进度

## 2026-04-13

### 今日完成

- 按上次记录继续执行 DQ 健康检查，完成了“全量快照 + 全量 DQ”复核闭环。
- 全量快照（异步）执行成功：
  - `dispatch`: `1d8ec0fc-3658-40f3-8fc7-6c244fc44b80`
  - `execute`: `17bd85f2-e789-41d8-a637-d8bba176742c`
  - 结果：`selected_markets=200`，`created=193`，`skipped_missing_order_books=7`
- 全量 DQ（异步）执行成功：
  - `dispatch`: `c2529b89-b387-4f02-8778-464a771320cb`
  - `execute`: `57cd19d0-1c5a-4cda-ae13-7637746675bf`
  - 结果：`selected_markets=200`，`pass=0`，`warn=108`，`fail=92`
- 发现并确认一个可观测性缺口：`market_snapshot_capture` 的 `execute` 审计 payload 缺少 `book_fetch_failed_tokens` 与 `created_from_source_payload`。
- 已完成最小补丁（`workers/worker/tasks/ingest.py`）：将上述两个字段写入审计 payload。
- 发现队列积压场景：`dq-run` 在队列里延迟执行会导致批次回到 `stale`（出现 `fail=200` 的假性退化）。
- 为避免被队列延迟污染结论，补充执行了“全量同步基线检查（200 市场）”收敛当日结果：
  - 快照：`selected_markets=200`，`created=193`，`book_fetch_failed_tokens=0`，`created_from_source_payload=80`
  - DQ：`selected_markets=200`，`pass=0`，`warn=108`，`fail=92`

### 验证结果

- 自动化测试：
  - `python -m pytest tests/test_ingest_snapshot_resilience.py -q` -> `3 passed`
- 审计日志验证（补丁生效后）：
  - `market_snapshot_capture.execute` payload 已包含：
    - `book_fetch_failed_tokens`
    - `created_from_source_payload`
- `/dq/summary?limit=20` 最新返回（2026-04-13）：
  - `latest_checked_at`: `2026-04-13T02:38:35`
  - `latest_snapshot_time`: `2026-04-13T02:38:28`
  - `status_distribution`: `fail=92, warn=108`
  - `snapshot_age_seconds`: `7`
  - `freshness_status`: `fresh`
  - `top_blocking_reasons`: `REJ_DATA_LEAK_RISK=83, REJ_DATA_STALE=7, REJ_DATA_INCOMPLETE=3`

### 当前状态

- 主链路可运行；DQ 当日全量基线已完成并可复验。
- `book_fetch_failed_tokens` 与 `created_from_source_payload` 已可通过审计日志直接观察。
- 当前主要风险从“全量 stale”转为“规则层 fail/warn 偏高（尤其 `REJ_DATA_LEAK_RISK`）”。
- 队列积压会放大“假性 stale”，需要与真实数据质量问题区分。

### 下一步

- 优先排查 `REJ_DATA_LEAK_RISK` Top 样本（按 market_id 聚焦规则触发明细），确认是规则阈值问题还是源数据时序问题。
- 继续重点观察：
  - `book_fetch_failed_tokens`
  - `market_snapshot_capture` 审计日志中的 execute 结果与 payload
- 补一条脚本化健康检查入口（`scripts/`），把“快照 -> DQ -> summary 校验”固化为单命令，降低队列时序影响。

## 2026-04-10

### 今日完成

- M4-M6 主链路保持可运行，继续做了 DQ 零通过率排障收口。
- 定位到 `Data Quality Dashboard` 中 `pass=0` 的直接原因：
  - 快照抓取链路在 CLOB 网络不稳定时失败，导致 DQ 连续命中 `DQ_SNAPSHOT_STALE`。
- 已完成后端修复（最小可落地，不做过度设计）：
  - `capture_snapshots` 增加容错统计：`book_fetch_failed_tokens`
  - CLOB 失败场景新增 source payload 降级快照能力
  - 新增配置：`INGEST_ALLOW_SOURCE_PAYLOAD_FALLBACK`（默认 `true`）
  - Worker 重启后，快照与 DQ 恢复出数，不再全量 stale
- 修复并重写了乱码文档：
  - `README.md`
  - `docs/dev-progress.md`

### 验证结果

- 自动化测试：
  - `python -m pytest tests/test_ingest_snapshot_resilience.py -q` -> `3 passed`
  - `python -m pytest tests/test_dq_service.py tests/integration/test_api_dq.py -q` -> `12 passed`
  - `npm run test:m456` -> `35 passed`
- 运行态验证：
  - `/dq/summary` 返回：
    - `status_distribution`: `warn=154, pass=25, fail=21`
    - `snapshot_age_seconds`: `16`
    - `freshness_status`: `fresh`
- 网络连通性快速检查（收工前）：
  - 本机 API 正常
  - Gamma/CLOB 当前可连通（HTTP 200，延迟约 0.7s~1.5s）

### 当前状态

- M4：可用
- M5：可用
- M6：可用
- DQ 看板：已从 `pass=0` 恢复

### 下一步

- 下次开始前先做一次快速健康检查：
  - `npm run task:snapshot-sync`
  - `npm run task:dq-run`
  - 检查 `/dq/summary` 的 `freshness_status` 与 `status_distribution`
- 若外网再次抖动，优先观察：
  - `book_fetch_failed_tokens`
  - `market_snapshot_capture` 审计日志

## 2026-04-09

### 今日完成（摘要）

- 修复 Review Queue 历史状态兼容问题（`open` 归并到 `pending`）。
- 修复 tagging 分类落库与 review task 状态更新逻辑。
- 补齐 tagging 默认基线种子脚本与联调用例。

### 验证结果（摘要）

- `python -m pytest tests/integration/test_api_review.py -q` -> `4 passed`
- `python -m pytest tests/integration/test_api_monitoring.py tests/integration/test_api_tagging.py -q` -> `9 passed`
