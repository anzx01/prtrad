# 关键审计动作清单 v1

## API

### HTTP 请求完成

- `object_type`: `api_request`
- `action`: `request.completed`
- `result`: `success` 或 `error`
- 负载：
  - `method`
  - `path`
  - `status_code`
  - `duration_ms`

### HTTP 请求异常

- `object_type`: `api_request`
- `action`: `request.exception`
- `result`: `error`

## Worker

### 市场同步派发

- `object_type`: `market_catalog_sync`
- `action`: `dispatch`
- `result`: `queued`

### 市场同步执行完成

- `object_type`: `market_catalog_sync`
- `action`: `execute`
- `result`: `success`
- 负载摘要：
  - `pages`
  - `fetched_markets`
  - `created`
  - `updated`
  - `skipped_unchanged`
  - `marked_inactive`

### 快照采集派发

- `object_type`: `market_snapshot_capture`
- `action`: `dispatch`
- `result`: `queued`

### 快照采集执行完成

- `object_type`: `market_snapshot_capture`
- `action`: `execute`
- `result`: `success`
- 负载摘要：
  - `selected_markets`
  - `created`
  - `skipped_existing`
  - `skipped_missing_mapping`
  - `skipped_missing_order_books`

### DQ 扫描派发

- `object_type`: `market_dq_scan`
- `action`: `dispatch`
- `result`: `queued`

### DQ 扫描执行完成

- `object_type`: `market_dq_scan`
- `action`: `execute`
- `result`: `success`
- 负载摘要：
  - `selected_markets`
  - `created`
  - `pass`
  - `warn`
  - `fail`
  - `alerts_emitted`

### 自动分类派发

- `object_type`: `market_auto_tagging`
- `action`: `dispatch`
- `result`: `queued`

### 自动分类执行完成

- `object_type`: `market_auto_tagging`
- `action`: `execute`
- `result`: `success`
- 负载摘要：
  - `selected_markets`
  - `created`
  - `skipped_existing`
  - `tagged`
  - `review_required`
  - `blocked`
  - `classification_failed`
  - `review_tasks_created`

### 任务重试

- `object_type`: `worker_task`
- `action`: `retry_scheduled`
- `result`: `retry`

### 任务失败

- `object_type`: `worker_task`
- `action`: `execute`
- `result`: `failed`
- 负载摘要：
  - `task_name`
  - `reason`
  - `kwargs_keys`

## Tagging 配置治理

### 默认字典 seed

- `object_type`: `tag_dictionary_catalog`
- `action`: `seed`
- `result`: `success`

### 标签字典条目变更

- `object_type`: `tag_dictionary_entry`
- `action`: `create` 或 `update`
- `result`: `success`

### 规则版本创建 / 激活 / 回滚

- `object_type`: `tag_rule_version`
- `action`: `create` / `activate` / `rollback`
- `result`: `success`
