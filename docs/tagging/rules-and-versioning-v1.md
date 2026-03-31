# 标签字典与规则版本底座 v1

本文档描述 `PKG-RISK-01` 交付的标签字典与规则配置底座，用于支撑后续 `M2-002` 自动分类引擎与 `M2-005` 标签/审核 API。

## 范围

本版本覆盖：

- 标签字典主数据（一级类别 / 风险因子 / 白灰黑名单桶）
- 规则版本（草稿、激活、被替换）与回滚版本（以新版本形式发布）
- 规则配置（匹配范围、匹配算子、动作类型、优先级、启停）
- 规则变更审计（写入 `audit_logs`）

非目标：

- 不实现自动分类计算逻辑（留给 `M2-002`）
- 不实现 Web UI 和 REST API（留给 `M2-005`）

## 设计原则

- 多标签而非单一类别：允许同时输出一级类别、多个风险因子与准入桶（白/灰/黑）。
- 版本化、可回滚、可审计：任何变更都必须形成明确版本与审计事件。
- 研究可复算：规则版本保存字典快照与规则配置快照，以便回放与复算一致。

## 数据模型（数据库表）

### 1) `tag_dictionary_entries`

用途：标签字典主数据。

关键字段：

- `tag_code`：标签代码（全局唯一），建议全大写，下划线分隔，例如 `CAT_NUMERIC`。
- `tag_type`：标签类型，v1 取值：`category` / `risk_factor` / `list_bucket`。
- `dimension`：维度，用于组织标签，例如 `primary_category`、`admission_bucket`。
- `aliases`：同义词与别名（用于后续匹配/展示），列表。
- `tag_metadata`：扩展元数据（例如 `exclusive_group`、`polarity`、`rank`）。
- `is_active`：是否启用。禁用后不会进入规则版本的 `dictionary_snapshot`。

约束与索引：

- `tag_code` 唯一约束
- `tag_type + dimension` 复合索引

### 2) `tag_rule_versions`

用途：规则版本对象，保存版本元数据与快照。

关键字段：

- `version_code`：版本标识（唯一），例如 `tag_v1_20260329_a`。
- `status`：版本状态，v1 使用：`draft` / `active` / `superseded`。
- `release_kind`：发布类型，v1 使用：`standard` / `rollback`。
- `base_version_id`：基于哪个版本派生（草稿继承或回滚来源）。
- `supersedes_version_id`：本版本替换的上一个 active 版本（用于追溯回滚链路）。
- `dictionary_snapshot`：激活时冻结的标签字典快照（用于复算一致）。
- `config_payload`：全局规则配置快照（匹配字段、冲突策略、review 策略等）。
- `checksum`：对快照内容计算的 SHA256（用于快速对比与篡改检测）。
- `activated_at/activated_by`、`retired_at`：激活/退役时间与操作者。

约束与索引：

- `version_code` 唯一约束
- `status + created_at` 复合索引（快速定位最近版本与 active 版本）

### 3) `tag_rules`

用途：规则明细，挂在某个 `tag_rule_versions` 下。

关键字段：

- `rule_code`：规则编号（在单版本内唯一）。
- `rule_kind`：规则类型，v1 允许：`keyword` / `regex` / `structured_match` / `manual_seed`。
- `action_type`：动作类型，v1 允许：
  - `assign_primary_category`：设置一级类别（互斥组）
  - `add_risk_factor`：添加风险因子（可多选）
  - `set_admission_bucket`：设置准入桶（白/灰/黑，通常互斥）
  - `require_review`：触发人工审核（用于低置信或冲突）
  - `attach_note`：附加说明备注（用于可解释性）
- `target_tag_code`：动作目标标签（部分 action 必填）。
- `priority`：优先级，数值越小越先执行。
- `enabled`：启停开关。
- `match_scope`：匹配作用域字段列表（例如 `question`、`description` 等）。
- `match_operator`：匹配算子，v1 允许：`contains_any` / `contains_all` / `exact` / `equals_any` / `regex`。
- `match_payload`：匹配参数（关键词列表、正则表达式、结构化条件等）。
- `effect_payload`：动作参数（置信度加权、解释文本等，留给后续引擎解释）。

约束与索引：

- `rule_version_id + rule_code` 唯一约束
- `rule_version_id + priority` 复合索引（按优先级执行）

## 版本生命周期与回滚策略

### 状态机

- `draft`：可创建与编辑，但不可作为系统“当前生效版本”。
- `active`：系统当前生效版本（目标是全局最多 1 个；当前通过服务层逻辑保证）。
- `superseded`：被新版本替换的历史版本。

### 回滚语义（重要）

回滚不是“把旧版本再激活”，而是：

- 选择一个历史版本作为 `target_version_code`
- 复制其规则与快照，创建一个新的 `release_kind=rollback` 版本并激活
- 新版本会替换当前 active 版本，形成可审计的回滚链路

这样做的好处：

- 保留时间线与操作者证据
- 避免“旧版本被重新写入”导致的审计歧义
- 支持在回滚版本上追加解释与影响评估

## 审计事件（`audit_logs`）

服务会写入以下审计对象：

- `tag_dictionary_catalog`：默认字典 seed
- `tag_dictionary_entry`：标签字典条目 create/update
- `tag_rule_version`：规则版本 create/activate/rollback

关键字段约定：

- `object_type`：如上
- `object_id`：建议使用 `tag_code` 或 `version_code`
- `action`：`seed/create/update/activate/rollback`
- `result`：`success`（失败时服务层会降级为日志，不阻塞主流程）

## 推荐工作流（研究阶段）

1. 先 seed 默认字典（或手工维护字典）。
2. 创建 `draft` 规则版本，写清楚 `change_reason`、`evidence_summary`、`rollback_plan`。
3. 激活该版本，系统会自动将旧 active 版本标为 `superseded`。
4. 发现问题时，以回滚形式发布新版本并激活（保留审计链路）。

