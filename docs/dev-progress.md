# 开发进度

## 2026-04-09

### 今日完成

- 修复 Review Queue 历史状态兼容问题：
  - open 状态统一按 pending 处理。
  - review API 返回前统一归一化 queue_status。
  - monitoring 统计将历史 open 归并到 pending。
- 修复 tagging 分类落库问题：
  - 新建 review task 时统一写入 pending。
  - 修正 MarketTagAssignment 字段名，使用 ssignment_entry_metadata。
- 打通真实开发库的 Review Queue 数据链路：
  - 已在开发库中存在默认字典数据与激活中的 tagging rule version。
  - 执行市场自动分类后，成功生成 review task。
- 统一按仓库现实使用 docs/ 目录记录文档。
  - AGENTS.md 前文存在 doc/ 表述，但第 9 节与仓库实际结构均为 docs/，本项目后续以 docs/ 为准。

### 验证结果

- 真实开发库 ar/data/ptr_dev.sqlite3 当前结果：
  - market_classification_results = 285
  - market_review_tasks = 285
  - market_review_tasks.queue_status = pending: 285
- API 验证：
  - /review/queue?queue_status=pending&page=1&page_size=3 可返回任务数据。
  - /monitoring/metrics 中 
eview_queue.pending = 285。
- 自动化测试：
  - python -m pytest tests/integration/test_api_review.py tests/integration/test_api_monitoring.py tests/integration/test_api_tagging.py -q
  - 结果：12 passed
  - python -m pytest tests/test_calibration_service.py tests/test_netev_service.py tests/integration/test_api_calibration.py tests/integration/test_api_netev.py -q
  - 结果：8 passed

### 当前状态

- Review Queue 空列表的后端根因已排除：
  - 代码兼容逻辑已补齐。
  - 真实开发库已有 pending review task 数据。
- 当前本机未运行开发服务：
  - http://localhost:8000 未启动。
  - http://localhost:3000 未启动。
  - 若需要在浏览器中直接查看结果，需先启动本地 API 与 Web。

### 下一步

- 启动本地开发服务并在浏览器中复核 Review Queue 与 Monitoring 页面。
- 将当前 bootstrap 用的最小 tagging rule version 替换为正式分类规则，减少全部落入 ReviewRequired 的临时状态。
- 继续推进 M3 相关联调与页面验收。
### 补充更新

- 修复 `/review/queue` 的 `total` 字段，改为返回全部匹配任务数，而不是当前页条数。
- 新增分页回归测试，覆盖 `pending` 过滤下历史 `open` 与当前 `pending` 混合场景的总数统计。
- 补充验证：
  - `python -m pytest tests/integration/test_api_review.py -q`
  - 结果：`4 passed`
  - `python -m pytest tests/integration/test_api_monitoring.py tests/integration/test_api_tagging.py -q`
  - 结果：`9 passed`

### ?????Tagging ???????

- ???????????`apps/api/services/tagging/default_rules.py`
- ??????????`scripts/seed_tagging_defaults.py`
- ???????`TaggingRuleService.seed_default_rule_version()`
- ?????????
  - `npm run seed:tagging-defaults`
  - `npm run dev:prepare` ?????? tagging ?????
- ???????????
  - ?????????????? classification result ??????????? review task ?? `cancelled`
  - ?????? `review_payload.cancelled_reason = superseded_by_reclassification`
- ????????????????
  - `tag_default_v1` -> `active`
  - `bootstrap_review_queue_v1` -> `superseded`
- ????????????
  - `Tagged = 153`
  - `Blocked = 132`
  - `ReviewRequired = 0`
  - `market_review_tasks.cancelled = 285`
  - `market_review_tasks.pending = 132`
- ?????`tests/test_tagging_defaults.py`
- ?????
  - `python -m pytest tests/test_tagging_defaults.py -q`
  - ???`3 passed`
  - `python -m pytest tests/integration/test_api_review.py tests/integration/test_api_monitoring.py tests/integration/test_api_tagging.py -q`
  - ???`13 passed`
  - `npm run dev:prepare`
  - ??????? `db:upgrade` ? `seed:tagging-defaults`

