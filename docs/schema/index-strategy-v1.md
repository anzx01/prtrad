# 索引策略 v1

## 目标

Wave 1 的索引主要优化以下查询：

- 按外部 `market_id` 查市场
- 按 `event_id` 和 `market_status` 做过滤
- 按市场和时间查快照
- 按市场和检查时间查 DQ 结果
- 按对象、请求、任务上下文查 decision/audit 日志

## 索引分组

### Markets

- `market_id`
- `event_id`
- `condition_id`（普通索引，不假设全局唯一）
- `market_status`

### Market snapshots

- `market_ref_id + snapshot_time` 复合索引
- `market_ref_id + snapshot_time` 唯一约束

### Data quality results

- `status`
- `rule_version`
- `market_ref_id + checked_at` 复合索引

### Decision logs

- `signal_id`
- `decision_type`
- `decision_status`
- `rule_version`
- `request_id`
- `task_id`
- `market_ref_id + created_at` 复合索引

### Audit logs

- `actor_id`
- `object_type`
- `object_id`
- `action`
- `result`
- `request_id`
- `task_id`
- `object_type + object_id` 复合索引
