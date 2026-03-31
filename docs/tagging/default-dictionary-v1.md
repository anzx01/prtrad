# 默认标签字典 v1

本文档描述 `PKG-RISK-01` 内置的默认标签字典（用于快速启动 `M2` 标签体系）。

来源：

- PRD 第 8 节“市场标签体系”
- `apps/api/services/tagging/service.py` 中的 `DEFAULT_TAG_DEFINITIONS`

说明：

- 代码是权威来源；本文档用于快速浏览与讨论。
- `tag_code` 建议作为跨系统引用主键，不建议随意修改。

## 一级类别（tag_type=category, dimension=primary_category）

- `CAT_NUMERIC`：Numeric
- `CAT_TIME`：Time
- `CAT_STATISTICAL`：Statistical
- `CAT_PERSON`：Person
- `CAT_MACRO`：Macro
- `CAT_GEOPOLITICAL`：GeoPolitical
- `CAT_DISASTER`：Disaster
- `CAT_SPORTS`：Sports
- `CAT_CRYPTO_ASSET`：CryptoAsset
- `CAT_OTHER`：Other（兜底）

## 风险因子（tag_type=risk_factor）

- `RF_OBJECTIVE_RESOLUTION`（dimension=resolution_objectivity）：客观结算
- `RF_SOURCE_AUTHORITY_CLEAR`（dimension=source_authority）：权威数据源清晰
- `RF_SOURCE_COUNT_MULTIPLE`（dimension=source_count）：多数据源交叉验证
- `RF_MANUAL_INTERPRETATION_REQUIRED`（dimension=interpretation_dependency）：依赖人工解释
- `RF_SINGLE_EVENT_DEPENDENT`（dimension=single_event_dependency）：依赖单一新闻事件
- `RF_SINGLE_ASSET_CORRELATED`（dimension=single_asset_dependency）：与单一资产强相关
- `RF_MACRO_CORRELATED`（dimension=macro_dependency）：与宏观风险强相关
- `RF_DISPUTE_TEMPLATE_SIMILAR`（dimension=dispute_template）：存在历史争议模板相似性
- `RF_PRE_CLOSE_INFORMATION_JUMP`（dimension=pre_close_information_jump）：到期前信息跳变风险
- `RF_LIQUIDITY_THIN`（dimension=liquidity_tier）：流动性偏薄
- `RF_THEME_CLUSTERED`（dimension=theme_cluster）：主题聚类集中

备注：

- 风险因子维度是可扩展的；v1 只定义最小集合，便于后续快速增量。

## 白灰黑名单桶（tag_type=list_bucket, dimension=admission_bucket）

- `LIST_WHITE`：白名单
- `LIST_GREY`：灰名单
- `LIST_BLACK`：黑名单

