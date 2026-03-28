# 核心 Schema v1

## 目标

Wave 1 的 schema 主要覆盖：

- `markets`
- `market_snapshots`
- `data_quality_results`
- `decision_logs`
- `audit_logs`

## 说明

- `markets.market_id` 保存外部 Polymarket 市场标识
- `markets.condition_id` 保存 CLOB / Data API 使用的链上条件标识，并建立普通索引
- 内部主键统一使用 UUID
- 研究阶段为保持灵活性，部分扩展字段使用 JSON
- 时间字段优先使用带时区的时间类型

## 市场表扩展字段

为支持 `PKG-DATA-02` 的市场元数据与快照采集，`markets` 新增以下字段：

- `condition_id`：用于关联 CLOB 订单簿和后续 Data API
- `outcomes`：标准化后的 outcome 标签列表，当前重点支持 `Yes/No`
- `clob_token_ids`：与 `outcomes` 对齐的 token id 列表
- `source_payload`：保留事件标题、标签、盘口补充字段等扩展信息

## 目标数据库

- 生产目标：PostgreSQL
- 本地 Wave 1 兜底：SQLite
