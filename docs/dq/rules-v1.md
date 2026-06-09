# DQ 规则引擎 v1

## 目标

Wave 1 的 DQ v1 负责为研究模式下的市场子集产出可追溯的质量状态，覆盖：

- 缺失
- 过期
- 异常
- 重复
- 时间逻辑错误

输出统一落入 `data_quality_results`，并在 `result_details` 中写入规则详情、最新快照摘要和阻断原因码。

## 当前评估范围

Wave 1 默认按以下顺序选取市场：

1. 只评估 `active_accepting_orders`、`active_open`、`active_paused`
2. 按 `source_updated_at DESC, updated_at DESC` 排序
3. 取 `DQ_MARKET_LIMIT` 条

这样做的原因是：

- 当前快照任务默认只覆盖研究模式下的前 `200` 个活跃市场
- 若 DQ 对全量 `59k+` 活跃市场同时运行，大量市场会因为未采样而统一失败，噪声过大

## 规则清单

### 1. 关键市场字段缺失

- 编码：`DQ_MARKET_REQUIRED_FIELDS_MISSING`
- 类型：阻断
- 原因码：`REJ_DATA_INCOMPLETE`
- 检查字段：
  - `question`
  - `description`
  - `close_time`
  - `outcomes`
  - `clob_token_ids`

### 2. 市场时间逻辑错误

- 类型：阻断
- 原因码：`REJ_DATA_LEAK_RISK`
- 检查项：
  - `creation_time > open_time`
  - `open_time > close_time`
  - `resolution_time < creation_time`

### 3. 市场元数据陈旧

- 编码：`DQ_SOURCE_STALE`
- 类型：告警
- 原因码：`REJ_DATA_STALE`
- 说明：`source_updated_at` 超过 `DQ_SOURCE_STALE_AFTER_SECONDS`

### 4. 重复市场签名

- 编码：`DQ_DUPLICATE_MARKET_SIGNATURE`
- 类型：告警
- 原因码：`REJ_DATA_ANOMALY`
- 说明：同一 `event_id + question + close_time` 在活跃市场中出现多条记录

### 5. 最新快照缺失

- 编码：`DQ_SNAPSHOT_MISSING`
- 类型：阻断
- 原因码：`REJ_DATA_STALE`

### 6. 最新快照关键字段缺失

- 编码：`DQ_SNAPSHOT_REQUIRED_FIELDS_MISSING`
- 类型：阻断
- 原因码：`REJ_DATA_INCOMPLETE`
- 检查字段：
  - `best_bid_no`
  - `best_ask_no`
  - `best_bid_yes`
  - `best_ask_yes`
  - `spread`
  - `top_of_book_depth`
  - `cumulative_depth_at_target_size`
  - `traded_volume`

### 7. 最新快照过期

- 编码：`DQ_SNAPSHOT_STALE`
- 类型：阻断
- 原因码：`REJ_DATA_STALE`
- 说明：`checked_at - snapshot_time > DQ_SNAPSHOT_STALE_AFTER_SECONDS`

### 8. 快照未来泄漏风险

- 类型：阻断
- 原因码：`REJ_DATA_LEAK_RISK`
- 检查项：
  - `snapshot_time > checked_at + DQ_SNAPSHOT_FUTURE_TOLERANCE_SECONDS`

### 9. 盘口一致性异常

- 类型：阻断
- 原因码：`REJ_DATA_ANOMALY`
- 检查项：
  - `best_bid_no > best_ask_no`
  - `best_bid_yes > best_ask_yes`
  - `spread < 0`
  - `top_of_book_depth < 0`
  - `cumulative_depth_at_target_size < 0`
  - `traded_volume < 0`

### 10. 宽 spread 与价格跳变告警

- 类型：告警
- 说明：
  - `spread > DQ_WARNING_SPREAD_THRESHOLD`
  - 相邻两条快照的 NO 中间价绝对跳变超过 `DQ_MAX_MID_PRICE_JUMP_ABS`

## 状态与评分

### 状态

- `pass`：无阻断，也无 warning
- `warn`：无阻断，但存在 warning
- `fail`：存在至少一个阻断规则

### 评分

- 初始值为 `1.0`
- 每个阻断项扣 `0.20`
- 每个 warning 扣 `0.05`
- 下限为 `0.0`

评分仅用于排序和可视化，不替代阻断判断。

## 下游使用约定

- 只要 `status=fail`，下游信号或页面都应视为“不可交易”
- 下游应优先读取 `blocking_reason_codes`
- 若 `status=warn`，表示仍可研究，但建议人工复核

## 已知边界

### 1. 当前只正式覆盖快照子集

默认不会直接对全量活跃市场做高频 DQ。

### 2. `trade_count` 和 `last_trade_age_seconds` 暂未纳入硬性规则

因为 Wave 1 的公共数据源尚未稳定提供低成本批量值。

### 3. 重复市场识别仍是保守版本

当前只做“同事件、同问题、同 close_time”的重复签名识别，尚未实现更高级的镜像市场和语义近重复识别。
