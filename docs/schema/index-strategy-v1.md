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
- `market_ref_id + checked_at + rule_version` 唯一索引（用于 DQ 结果幂等）

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

### Tagging

- `tag_dictionary_entries.tag_code` 唯一约束
- `tag_dictionary_entries.tag_type + dimension` 复合索引（按维度查询标签字典）
- `tag_rule_versions.version_code` 唯一约束
- `tag_rule_versions.status + created_at` 复合索引（快速定位最近版本与 active 版本）
- `tag_rules.rule_version_id + rule_code` 唯一约束（单版本内部规则编号不冲突）
- `tag_rules.rule_version_id + priority` 复合索引（按优先级顺序执行）
- `market_classification_results.market_ref_id + rule_version + source_fingerprint` 唯一索引（分类幂等）
- `market_classification_results.status + classified_at` 复合索引（最近分类状态查询）
- `market_tag_assignments.market_ref_id + tag_code` 复合索引（按市场或标签查询）
- `market_tag_explanations.classification_result_id + rule_code` 复合索引（按结果回放解释）
- `market_review_tasks.queue_status + created_at` 复合索引（审核队列拉取）
