# Polymarket 公共数据源说明 v1

## 目标

本说明用于约束 `PKG-DATA-02` 在 Wave 1 阶段使用的公开数据源、字段映射和已知限制，避免后续实现偏离。

## 数据源选择

### 1. Gamma API

用途：

- 拉取市场元数据
- 拉取事件级标签与主题信息
- 获取 `updatedAt`、`bestBid`、`bestAsk`、`volume24hrClob` 等补充字段

当前接入方式：

- 入口：`/events`
- 过滤条件：`active=true&closed=false&archived=false`
- 分页方式：`limit + offset`
- 排序方式：`order=id&ascending=true`

选择理由：

- 单次事件响应里已带 `markets` 数组，能同时得到事件标签和市场详情
- 公开接口稳定，适合在本地 SQLite 方案下先跑通 M1 主链路

### 2. CLOB API

用途：

- 拉取 `Yes/No` token 的订单簿
- 计算最优 bid/ask、NO 侧盘口深度、目标规模累计深度

当前接入方式：

- 入口：`/books`
- 请求体：`[{\"token_id\": \"...\"}, ...]`
- 输出核心字段：`asset_id`、`bids`、`asks`、`last_trade_price`

选择理由：

- 相比逐个请求 `/book`，批量 `/books` 更适合定时快照
- 订单簿返回里直接包含 `last_trade_price`，可补齐 NO 侧最近成交价

## 字段映射

### 市场主表 `markets`

- `market_id` <- Gamma `market.id`
- `event_id` <- Gamma `event.id`
- `condition_id` <- Gamma `market.conditionId`
- `question` <- Gamma `market.question`
- `description` <- Gamma `market.description`
- `resolution_criteria` <- `market.resolutionSource`，为空时回退到 `event.resolutionSource`
- `creation_time` <- `market.createdAt`
- `open_time` <- `market.startDate`，为空时回退到 `acceptingOrdersTimestamp`
- `close_time` <- `market.closedTime`，为空时回退到 `market.endDate`
- `resolution_time` <- `market.umaEndDate`
- `market_status` <- 本地状态机映射
- `category_raw` <- 首个事件标签；若缺失则回退到事件标题
- `related_tags` <- 事件标签精简结构
- `outcomes` <- 解析后的 `market.outcomes`
- `clob_token_ids` <- 解析后的 `market.clobTokenIds`
- `source_updated_at` <- `market.updatedAt`
- `source_payload` <- 事件与市场的扩展补充字段

### 快照表 `market_snapshots`

- `best_bid_yes` / `best_ask_yes` <- Yes token 订单簿最优价
- `best_bid_no` / `best_ask_no` <- No token 订单簿最优价
- `last_trade_price_no` <- No token 订单簿 `last_trade_price`
- `spread` <- `best_ask_no - best_bid_no`
- `top_of_book_depth` <- NO 侧最优 bid 和最优 ask 对应挂单量之和
- `cumulative_depth_at_target_size` <- NO 侧 ask 盘口按价格优先累计到目标份额的可成交量
- `traded_volume` <- 优先取 Gamma `volume24hrClob`，缺失时回退到 `volumeClob`

## 本地状态映射

- `archived=true` -> `archived`
- `closed=true && umaResolutionStatus=resolved` -> `resolved`
- `closed=true` -> `closed`
- `active=true && acceptingOrders=true` -> `active_accepting_orders`
- `active=true && acceptingOrders!=true` -> `active_open`
- 其他 -> `active_paused`

另外：

- 若某个本地活跃市场在完整一次同步中不再出现在公开活跃 feed，会被标记为 `inactive_from_feed`
- 该标记仅表示“当前公开活跃 feed 不再返回”，不直接等价于“已正式结算”

## 已知限制

### 1. 这不是严格意义上的上游增量拉取

公开 Gamma 接口当前未在 Wave 1 接入中使用 `updated_after` 一类过滤器，因此本实现采用：

- 全量扫描当前活跃事件
- 本地以 `source_updated_at` 做跳过

这属于“本地增量 upsert”，优点是简单稳健，缺点是扫描成本会随活跃市场数量上升。

### 2. `trade_count` 暂时为空

当前 Wave 1 只接入 Gamma + CLOB 公共接口，不额外引入更高成本的逐市场成交流水查询，因此 `trade_count` 暂置空值。

### 3. `last_trade_age_seconds` 暂时为空

当前选定接口能稳定得到 `last_trade_price`，但不能在低成本批量模式下稳定得到“该成交价对应的真实成交时间”，因此该字段保留为后续增强项。

### 4. 当前只正式支持二元 `Yes/No` 市场

若 `outcomes` 与 `clob_token_ids` 不是严格二元映射，快照任务会跳过该市场，避免写入含义不明确的数据。

### 5. 本地默认调度做了“可运行性守卫”

基于 2026-03-28 的一次真实活跃 feed 采样：

- 全量活跃事件扫描约 `99` 页
- 对应市场记录约 `5.9 万`
- 本地 SQLite + 公共 API 环境下，全量市场同步耗时约 `4` 分钟

因此 Wave 1 默认值采用：

- `INGEST_MARKET_SYNC_INTERVAL_SECONDS=900`
- `INGEST_SNAPSHOT_MARKET_LIMIT=200`

如果要扩展为全市场高频快照，必须在后续版本引入更强的筛选层、缓存层或流式数据通道。
