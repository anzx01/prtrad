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
- 继续把这次 DQ 排障收口为可复用运维能力：
  - 修复 `market_snapshot_capture` 审计日志缺少 `book_fetch_failed_tokens` / `created_from_source_payload` 的问题
  - `/dq/summary` 新增最近一次快照抓取诊断信息，便于直接查看 fallback 与抓取失败情况
  - `Data Quality Dashboard` 新增快照诊断区与操作检查项
  - 修复 `Data Quality Dashboard` 首次加载后不再刷新的问题，新增 30 秒自动刷新与手动刷新按钮，避免页面长时间停留在旧批次
  - 新增 `scripts/check-dq-health.ps1` 与 `npm run health:dq`，把快速健康检查收敛成统一脚本入口
  - 修复 `scripts/test-m456.ps1` 与 `scripts/test-risk.ps1` 中 `npm exec tsc` 参数写法，恢复统一脚本入口可用性
- 排查并临时恢复了 Calibration 页面：
  - 症状：`Calibration Units` 页面提示无法连接 `http://localhost:8000`
  - 直接原因：本机 API 进程未监听 `8000`
  - 深层原因：本地 SQLite 仍停留在 Alembic revision `20260404_0010`，访问 `/calibration/units` 时缺少 `calibration_units` 表
  - 尝试执行 `npm run db:upgrade` 后，定位到 M3 迁移 `8f9a8414a637` 在 SQLite 上会因为 `tag_quality_metrics.metric_date` 的 `DATE -> DATETIME` batch cast 触发唯一约束冲突
  - 当前已临时恢复：重新拉起 API 后，`/calibration/units` 可返回 `200`；页面不再是连通性错误，但当前单位列表为空
- 修复并重写了乱码文档：
  - `README.md`
  - `docs/dev-progress.md`

### 验证结果

- 自动化测试：
  - `python -m pytest tests/test_ingest_snapshot_resilience.py -q` -> `3 passed`
  - `python -m pytest tests/test_dq_service.py tests/integration/test_api_dq.py -q` -> `12 passed`
  - `npm run test:m456` -> `35 passed`
  - `npm run test:risk` -> `22 passed`
  - `python -m pytest tests/integration/test_api_dq.py tests/test_ingest_snapshot_resilience.py -q` -> `12 passed`
  - `npm --workspace apps/web exec tsc -- --noEmit` -> `passed`
  - `powershell -ExecutionPolicy Bypass -File ./scripts/check-dq-health.ps1 -ApiBaseUrl http://127.0.0.1:8766`（mock `/dq/summary`）-> `passed`
  - 本机运行态复核（2026-04-10 22:40 左右）：
    - `http://localhost:8000/dq/summary` -> `pass=16, warn=176, fail=8`
    - `freshness_status=fresh`
  - Calibration 运行态复核（2026-04-10 22:51 左右）：
    - `http://localhost:8000/health` -> `200 ok`
    - `http://localhost:8000/calibration/units?include_inactive=true` -> `200 []`
    - `POST /calibration/recompute-all?window_type=long` -> `total_units=0`
  - 数据库迁移复核：
    - `npm run db:current` -> `20260404_0010`
    - `npm run db:upgrade` -> 失败，阻塞点为 `8f9a8414a637`
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
- Calibration 页面：API 连通性已恢复，但本地历史库迁移仍未补齐到 head，当前为“接口可打开、数据为空、迁移待修复”

### 下一步

- 下次开始前先做一次快速健康检查：
  - `npm run task:snapshot-sync`
  - `npm run task:dq-run`
  - `npm run health:dq`
- 优先修复 SQLite 历史库的迁移链路：
  - 处理 `8f9a8414a637` 对 `tag_quality_metrics.metric_date` 的 SQLite cast 问题
  - 清理本次失败迁移留下的半升级状态，再继续 `npm run db:upgrade`
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
