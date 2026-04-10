# 开发进度

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
