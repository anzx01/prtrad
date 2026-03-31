# 核心 Schema v1

## 目标

Wave 1 的 schema 主要覆盖：

- `markets`
- `market_snapshots`
- `data_quality_results`
- `decision_logs`
- `audit_logs`
- `tag_dictionary_entries`
- `tag_rule_versions`
- `tag_rules`
- `market_classification_results`
- `market_tag_assignments`
- `market_tag_explanations`
- `market_review_tasks`

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

## DQ 结果表说明

为支持 `PKG-DATA-03` 的幂等扫描，`data_quality_results` 额外采用：

- `(market_ref_id, checked_at, rule_version)` 唯一索引
- `result_details` 保存逐条规则结果、阻断原因码和快照摘要

## 标签规则底座表说明

为支持 `PKG-RISK-01` 的 `M2-001` 底座能力，新增三张规则治理表：

- `tag_dictionary_entries`
  - 存储标签字典主数据，覆盖一级类别、风险因子、白灰黑名单
  - `tag_code` 全局唯一
  - `tag_type` + `dimension` 支持按维度组织和检索
- `tag_rule_versions`
  - 存储规则版本元数据与快照（字典快照、规则配置、校验 checksum）
  - 支持 `draft/active/superseded` 状态流转
  - 通过 `base_version_id`、`supersedes_version_id` 记录继承与替换关系
- `tag_rules`
  - 存储规则明细（匹配范围、匹配算子、动作类型、优先级、启停状态）
  - `rule_version_id + rule_code` 唯一，保证单版本内部规则编号不冲突

## 自动分类结果表说明

为支持 `PKG-RISK-02` 的自动分类引擎，新增四张分类闭环表：

- `market_classification_results`
  - 单次分类结果汇总
  - 记录 `classification_status`、一级类别、准入桶、置信度、失败原因与 `result_details`
  - 采用 `(market_ref_id, rule_version, source_fingerprint)` 唯一索引保证幂等
- `market_tag_assignments`
  - 存储分类后实际分配到市场上的标签集合
  - 区分 `primary_category` / `risk_factor` / `admission_bucket`
- `market_tag_explanations`
  - 存储规则命中解释、系统冲突解释、低置信解释
  - 用于后续审核 UI 与可解释性回放
- `market_review_tasks`
  - 存储进入 `ReviewRequired` 或 `Blocked` 的人工复核待办
  - `classification_result_id` 唯一，确保每条分类结果最多生成一个待办

## 目标数据库

- 生产目标：PostgreSQL
- 本地 Wave 1 兜底：SQLite
