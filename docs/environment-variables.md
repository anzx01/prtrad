# 环境变量说明

## 通用变量

- `APP_ENV`：运行环境，默认值为 `development`
- `APP_NAME`：应用名称，用于日志与界面显示
- `LOG_LEVEL`：日志级别，默认值为 `INFO`
- `LOG_JSON`：本地开发时是否启用 JSON 日志
- `RULE_VERSION`：当前启用的规则或配置版本标识

## Web 端

- `NEXT_PUBLIC_APP_NAME`：前端应用标题
- `NEXT_PUBLIC_API_BASE_URL`：前端访问 API 的基础地址

## API 端

- `API_HOST`：API 绑定地址
- `API_PORT`：API 监听端口
- `DATABASE_URL`：SQLAlchemy 数据库连接串；目标环境使用 PostgreSQL，本地 Wave 1 使用 SQLite 兜底

## Worker 端

- `CELERY_BROKER_URL`：Celery broker 地址
- `CELERY_RESULT_BACKEND`：Celery 结果后端地址
- `CELERY_BEAT_SCHEDULE_DB`：本地 beat 调度持久化文件路径
- `POLYMARKET_GAMMA_API_URL`：Polymarket Gamma 市场元数据接口根地址
- `POLYMARKET_CLOB_API_URL`：Polymarket CLOB 订单簿接口根地址
- `INGEST_HTTP_TIMEOUT_SECONDS`：市场采集和快照采集的 HTTP 超时时间
- `INGEST_GAMMA_PAGE_SIZE`：单次拉取 Gamma `events` 的分页大小
- `INGEST_CLOB_BATCH_SIZE`：单次调用 CLOB `/books` 的 token 批量大小
- `INGEST_MARKET_SYNC_INTERVAL_SECONDS`：市场元数据同步调度频率，单位秒；默认值建议不低于 `900`
- `INGEST_SNAPSHOT_INTERVAL_SECONDS`：快照采样调度频率，单位秒
- `INGEST_SNAPSHOT_TARGET_SIZE`：NO 侧累计深度计算使用的目标份额
- `INGEST_SNAPSHOT_MARKET_LIMIT`：快照任务单次处理的市场上限；默认值建议保留在 `200` 左右，`0` 表示不限制
