# 审计字段字典 v1

## 目标

本字典用于约束 `audit_logs` 的字段含义和取值方向，确保后续 API、worker、规则系统的关键动作能统一追溯。

## 主字段

### `actor_id`

- 含义：动作发起者标识
- API 场景：优先来自请求头 `x-actor-id`
- Worker 场景：通常写入任务名，例如 `worker.ingest.run_market_catalog_sync`

### `actor_type`

- 含义：发起者类型
- 典型值：
  - `user`
  - `service`
  - `system`

Wave 1 中：

- API 请求默认透传请求头 `x-actor-type`
- Worker 任务统一写为 `system`

### `object_type`

- 含义：被操作对象类型
- Wave 1 已启用值：
  - `api_request`
  - `market_catalog_sync`
  - `market_snapshot_capture`
  - `market_dq_scan`
  - `market_auto_tagging`
  - `tag_dictionary_catalog`
  - `tag_dictionary_entry`
  - `tag_rule_version`
  - `worker_task`

### `object_id`

- 含义：对象实例标识
- API 请求：`METHOD + path`
- 任务运行：通常使用 `triggered_at` / `checked_at`
- 任务失败兜底：使用 `task_id`

### `action`

- 含义：动作类型
- Wave 1 已启用值：
  - `request.completed`
  - `request.exception`
  - `dispatch`
  - `execute`
  - `retry_scheduled`

### `result`

- 含义：动作结果
- 典型值：
  - `success`
  - `error`
  - `queued`
  - `failed`
  - `retry`

### `request_id`

- 含义：HTTP 请求上下文标识
- 来源：请求头 `x-request-id`，缺失时自动生成 UUID

### `task_id`

- 含义：Celery 任务上下文标识
- 来源：Celery runtime task id

### `event_payload`

- 含义：与动作相关的结构化上下文
- 示例：
  - HTTP 状态码、请求耗时
  - 市场同步的分页数、写入条数
  - DQ 扫描的 pass/fail 统计
  - 自动分类的 Tagged/ReviewRequired/Blocked 统计
  - tagging 规则版本激活/回滚摘要
  - 失败任务的异常原因与参数键列表

## 使用约束

1. 审计写入失败不得阻塞主业务流程。
2. `object_type / object_id / action / result` 必须可读且稳定。
3. 事件负载优先写摘要，不直接写超大原始数据。
4. 请求与任务都应尽量带上 `request_id` 或 `task_id`，便于串联链路。
