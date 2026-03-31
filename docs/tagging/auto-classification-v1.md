# 自动分类引擎 v1

本文档描述 `PKG-RISK-02` 交付的自动分类引擎 v1。

## 目标

在 active tagging 规则版本存在的前提下，针对研究模式下的活跃市场：

- 输出一级类别
- 输出风险因子集合
- 输出准入桶（白 / 灰 / 黑）
- 输出分类置信度
- 输出命中解释与失败原因
- 对低置信、冲突或黑名单市场生成人工复核待办

## 输入

- `markets` 表中的标准化市场文本字段
- active `tag_rule_versions`
- active 版本下的 `tag_rules`

## 输出

- `market_classification_results`
- `market_tag_assignments`
- `market_tag_explanations`
- `market_review_tasks`

## 当前处理范围

- 默认只扫描活跃市场状态：`active_accepting_orders` / `active_open` / `active_paused`
- 默认市场上限受 `TAGGING_MARKET_LIMIT` 控制
- 默认不自动调度；需显式设置 `TAGGING_RUN_INTERVAL_SECONDS > 0`

## 分类状态

v1 当前输出以下状态：

- `Tagged`：分类完成，且未进入复核
- `ReviewRequired`：低置信、无类别、规则冲突、灰名单或显式要求复核
- `Blocked`：命中黑名单桶
- `ClassificationFailed`：保留给系统异常场景；正常规则路径优先落为 `ReviewRequired`

## 解释类型

`market_tag_explanations.explanation_type` 当前使用：

- `rule_match`：命中具体规则
- `conflict`：类别或准入桶冲突
- `default_bucket`：未命中准入桶时默认落灰名单
- `review_decision`：因低置信或无类别而进入复核

## 幂等策略

- `market_classification_results` 使用 `(market_ref_id, rule_version, source_fingerprint)` 唯一索引
- 相同市场、相同规则版本、相同市场文本内容重复执行时会被跳过
- `source_fingerprint` 基于问题文本、描述、结算规则、原始类别、相关标签与上游更新时间计算

## 关键限制

- v1 仅支持基于规则的文本分类，不引入模型推断
- `structured_match` 当前主要作为规则类型占位，实际匹配仍以 scope + operator 为主
- active 规则版本必须存在，否则自动分类任务会直接失败并重试
- 当前 review task 仅创建 `open` 待办，不处理人工结论回写（留给后续包）

