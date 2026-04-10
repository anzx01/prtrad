# Tagging 默认基线 v1

## 背景

为保证 M3 阶段的本地开发和联调能够稳定复现，仓库当前提供一套默认 tagging 基线：

- 自动写入默认标签字典
- 自动创建或恢复默认规则版本 `tag_default_v1`
- 可选地对开发库中的市场立即执行一次自动分类

这套基线用于替换早期的 bootstrap review fallback，避免所有市场都先落入 `ReviewRequired` 的临时状态。

## 使用方式

推荐直接执行：

```bash
npm run dev:prepare
```

该命令会依次执行：

1. `npm run db:upgrade`
2. `npm run seed:tagging-defaults`

如需单独恢复默认 tagging 基线，可执行：

```bash
npm run seed:tagging-defaults
```

如需在 seed 完成后立刻对开发库执行一次分类，可执行：

```bash
.\.venv\Scripts\python.exe scripts/seed_tagging_defaults.py --classify --market-limit 1000
```

## 规则覆盖范围

当前默认规则版本由 `apps/api/services/tagging/default_rules.py` 维护，共 13 条规则，主要覆盖以下场景：

- Crypto Up/Down、Crypto Prices
  - 主类别归到 `CAT_NUMERIC`
  - 准入桶默认归到 `LIST_WHITE`
  - 补充客观结算、权威来源、单资产相关、临近收盘信息跳变等风险因子
- Sports、Esports
  - 主类别归到 `CAT_SPORTS`
  - 准入桶默认归到 `LIST_BLACK`
  - 补充 `RF_MANUAL_INTERPRETATION_REQUIRED`
- Politics、Macro、War、Disaster 等高争议主题
  - 直接归到 `LIST_BLACK`
  - 补充 `RF_DISPUTE_TEMPLATE_SIMILAR`

## 规则版本行为

`TaggingRuleService.seed_default_rule_version()` 的行为如下：

- 如果 `tag_default_v1` 不存在，则创建新版本
- 如果 `tag_default_v1` 仍是 `draft`，则直接激活
- 如果 `tag_default_v1` 已被 superseded，但需要恢复默认基线，则自动创建 rollback 版本并激活

因此，`npm run seed:tagging-defaults` 既可以做首次初始化，也可以在实验规则之后恢复到默认基线。

## 与 Review Queue 的关系

默认基线替换 bootstrap fallback 后，分类结果会更接近真实业务意图：

- `Tagged` 市场不会创建 review task
- `Blocked` 市场通常直接进入黑名单准入结果，也不会继续挂在 Review Queue
- 只有确实需要人工介入的结果才会创建 `pending` review task

如果某个市场之前已经因为 bootstrap fallback 生成过 review task，而新的默认基线重新分类后不再需要人工审核，则旧待办会被自动收敛：

- `queue_status` 更新为 `cancelled`
- `review_payload.cancelled_reason = superseded_by_reclassification`
- 同时补充：
  - `superseded_at`
  - `superseded_by_classification_result_id`
  - `superseded_rule_version`

这样可以避免历史 bootstrap 待办长期残留在 Review Queue 中。

## 2026-04-09 开发库验证快照

开发库 `var/data/ptr_dev.sqlite3` 在默认基线生效后的结果：

- active rule version: `tag_default_v1`
- superseded rule version: `bootstrap_review_queue_v1`
- 分类结果：
  - `Tagged = 153`
  - `Blocked = 132`
  - `ReviewRequired = 0`
- review task：
  - `cancelled = 285`
  - `pending = 132`

## 验证命令

```bash
python -m pytest tests/test_tagging_defaults.py -q
python -m pytest tests/integration/test_api_review.py tests/integration/test_api_monitoring.py tests/integration/test_api_tagging.py -q
```

已知验证结果：

- `tests/test_tagging_defaults.py`：`3 passed`
- review / monitoring / tagging 相关集成测试：`13 passed`
