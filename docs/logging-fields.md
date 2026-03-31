# 日志字段规范

每个服务的日志在条件允许时都应包含以下字段：

- `timestamp`
- `level`
- `service`
- `environment`
- `request_id`
- `task_id`
- `rule_version`
- `message`

推荐的可选字段：

- `actor_id`
- `market_id`
- `signal_id`
- `event_type`
- `result`
- `object_type`
- `object_id`
- `action`
