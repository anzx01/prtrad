# 环境变量说明

## 通用变量

- `APP_ENV`：运行环境，默认 `development`
- `APP_NAME`：应用名称，用于日志与界面显示
- `LOG_LEVEL`：日志级别，默认 `INFO`
- `LOG_JSON`：是否启用 JSON 日志
- `RULE_VERSION`：当前启用的规则或配置版本标识

## Web 端

- `NEXT_PUBLIC_APP_NAME`：前端应用标题
- `NEXT_PUBLIC_API_BASE_URL`：前端访问 API 的基础地址
- `WEB_PORT`：前端开发服务器端口；未设置时默认 `3001`

## API 端

- `API_HOST`：API 绑定地址
- `API_PORT`：API 监听端口
- `DATABASE_URL`：数据库连接串；本地开发默认使用 SQLite
- `TRADING_LIVE_MODE_ENABLED`：是否允许开启实盘闸门；默认 `false`
- `TRADING_DEFAULT_ORDER_SIZE`：默认下单数量；默认 `10`
- `TRADING_LIVE_BANKROLL_FRACTION`：实盘按可用资金比例自动下单；默认 `0.02`
- `TRADING_LIVE_MIN_NOTIONAL`：实盘最小下单额；默认 `5`
- `TRADING_LIVE_MAX_NOTIONAL`：实盘最大下单额；默认 `25`
- `TRADING_LIVE_DAILY_ORDER_LIMIT`：单日最多允许发出的实盘单数；默认 `3`
- `TRADING_LIVE_STATUS_POLL_ATTEMPTS`：挂单后自动查单次数；默认 `5`
- `TRADING_LIVE_STATUS_POLL_INTERVAL_SECONDS`：自动查单间隔秒数；默认 `2`
- `TRADING_LIVE_PRIVATE_KEY`：实盘钱包私钥
- `TRADING_LIVE_CHAIN_ID`：实盘链 ID，默认 `137`
- `TRADING_LIVE_SIGNATURE_TYPE`：签名类型，默认 `0`
- `TRADING_LIVE_FUNDER_ADDRESS`：funder 地址；签名类型不是 `0` 时建议显式配置
- `TRADING_LIVE_API_KEY`：可选，预先创建的 L2 API Key
- `TRADING_LIVE_API_SECRET`：可选，预先创建的 L2 API Secret
- `TRADING_LIVE_API_PASSPHRASE`：可选，预先创建的 L2 API Passphrase
- `TRADING_LIVE_USE_SERVER_TIME`：是否使用交易所时间签名，默认 `true`
- `TRADING_LIVE_RETRY_ON_ERROR`：实盘下单是否启用 SDK 重试，默认 `true`

## Worker 端

- `CELERY_BROKER_URL`：Celery broker 地址
- `CELERY_RESULT_BACKEND`：Celery 结果后端地址
- `CELERY_BEAT_SCHEDULE_DB`：本地 beat 调度持久化文件路径
- `POLYMARKET_GAMMA_API_URL`：Polymarket Gamma 接口根地址
- `POLYMARKET_CLOB_API_URL`：Polymarket CLOB 接口根地址
- `INGEST_HTTP_TIMEOUT_SECONDS`：市场采集与快照采集的 HTTP 超时秒数
- `INGEST_GAMMA_PAGE_SIZE`：单次拉取 Gamma `events` 的分页大小
- `INGEST_CLOB_BATCH_SIZE`：单次调用 CLOB `/books` 的 token 批量大小
- `INGEST_MARKET_SYNC_INTERVAL_SECONDS`：市场元数据同步频率
- `INGEST_SNAPSHOT_INTERVAL_SECONDS`：快照采样频率
- `INGEST_SNAPSHOT_TARGET_SIZE`：订单簿深度计算使用的目标份额
- `INGEST_SNAPSHOT_MARKET_LIMIT`：单次快照任务处理的市场上限
- `DQ_RULE_VERSION`：DQ 规则版本标识
- `DQ_RUN_INTERVAL_SECONDS`：DQ 定时扫描频率
- `DQ_MARKET_LIMIT`：单次 DQ 评估的市场上限
- `DQ_SNAPSHOT_STALE_AFTER_SECONDS`：快照过期阈值
- `DQ_SOURCE_STALE_AFTER_SECONDS`：源数据过期阈值
- `DQ_MAX_MID_PRICE_JUMP_ABS`：中间价跳变告警阈值
- `DQ_WARNING_SPREAD_THRESHOLD`：spread warning 阈值
- `DQ_SNAPSHOT_FUTURE_TOLERANCE_SECONDS`：未来时间漂移容忍窗口
- `TAGGING_RUN_INTERVAL_SECONDS`：自动分类定时任务频率
- `TAGGING_MARKET_LIMIT`：自动分类单次处理的市场上限
