# 开发进度

## 2026-04-10

### 今日完成

- 完成 Review Queue 列表页分页补齐：
  - 前端接入 `/review/queue` 返回的 `total`、`page`、`page_size`。
  - 新增页码、总数、上一页 / 下一页控件。
  - 抽出 `apps/web/lib/review.ts`，统一列表页和详情页的 review 类型。
- 推进 M4 风控最短可用链路：
  - 新增风险阈值 upsert 能力，支持按 `cluster_code + metric_name` 创建或更新阈值配置。
  - 新增风险阈值停用能力，停用后自动回退到默认阈值。
  - 收紧风险暴露聚合口径：
    - 每个市场只使用最新一条 NetEV 评估记录，避免历史 admitted 结果重复计入暴露。
    - 风险簇优先使用最新分类结果中的结构化一级类别，并在存在代表性风险因子时拼接更细的簇码。
  - 为阈值配置补充基础校验：
    - `threshold_value > 0`
    - `utilization_*` 阈值必须位于 `(0, 1]`
    - `metric_name` 限制为 `utilization_caution` / `utilization_risk_off` / `max_exposure` / `max_positions`
  - Risk 页面新增阈值维护表单和“Use Default”按钮，可直接写入、覆盖或停用当前生效阈值。
  - 完成 M4 风控代码轻量拆分，未改业务行为：
    - 前端 `apps/web/app/risk/page.tsx` 拆出总览、暴露、阈值、kill-switch 等区块组件，以及共享类型与常量。
    - 后端 `apps/api/services/risk/service.py` 拆出 `clustering.py`，收敛“最新 admitted 候选去重 + 分类聚类解析”辅助逻辑。
    - 后端 `apps/api/app/routes/risk.py` 拆出 `app/risk_api.py`，集中放置风控路由 schema 与序列化辅助函数。
  - 补齐 M4 风控自动化测试入口：
    - 新增 `scripts/test-risk.ps1`，统一执行风控后端测试与 Web TypeScript 检查。
    - 根 `package.json` 新增 `npm run test:risk`，后续可作为 M4 默认回归入口。
  - 补充 M4 风控边界测试：
    - 覆盖 `/risk/state/history` 返回事件明细。
    - 覆盖 kill-switch 非法请求类型校验。
    - 覆盖 utilization 阈值非法值校验。
    - 覆盖停用不存在阈值的 404 返回。
    - 覆盖 cluster 阈值覆盖 global 阈值的优先级。
- 修复并同步相关文档：
  - 重写 `docs/tagging/default-bootstrap-v1.md`，恢复 UTF-8 中文内容。
  - 更新 `docs/tagging/auto-classification-v1.md` 中 review task 状态说明。
  - 更新本进度文档，记录 M4 本轮推进结果。

### 验证结果

- M4 风控相关测试：
  - `python -m pytest tests/test_risk_service.py tests/integration/test_api_risk.py -q`
  - 结果：`20 passed`
- Web 类型检查：
  - `npm --workspace apps/web exec -- tsc -- --noEmit`
  - 结果：通过
- M4 风控自动化测试脚本：
  - `npm run test:risk`
  - 结果：通过

### 当前状态

- M3 主链路当前可以视为已基本跑通，后续主要剩页面联调与验收。
- M4 已从“只读监控”推进到“可维护阈值 + 可见状态 + kill-switch 审批”的基础可用状态。
- M4 本轮已完成轻量重构，核心风险页面与服务文件规模已回到更可维护的范围，后续可继续做联调验收。
- `risk` 路由层本轮也已完成收敛，当前更适合进入浏览器联调和交互验收，而不是继续做结构拆分。
- M4 已具备可重复执行的最小自动化回归入口，后续每轮改动都可以直接复跑 `npm run test:risk`。

### 下一步

- 启动本地服务，对 `/risk` 页面做浏览器侧验收。
- 如需继续推进 M4，优先考虑：
  - 启动前后端联调，确认阈值维护、暴露重算、kill-switch 审批在页面上的实际体验。
  - 视验收情况再决定是否继续细化风险簇口径，或补充 kill-switch 目标范围约束。

## 2026-04-09

### 今日完成

- 修复 Review Queue 历史状态兼容问题：
  - 历史 `open` 状态统一按 `pending` 处理。
  - review API 返回前统一归一化 `queue_status`。
  - monitoring 统计将历史 `open` 归并到 `pending`。
- 修复 tagging 分类落库问题：
  - 新建 review task 时统一写入 `pending`。
  - 修正 `MarketTagAssignment` 字段名，使用 `assignment_entry_metadata`。
- 打通真实开发库的 Review Queue 数据链路：
  - 开发库已存在默认字典数据与激活中的 tagging rule version。
  - 执行市场自动分类后，成功生成 review task。
- 新增默认 tagging 基线：
  - 新增 `apps/api/services/tagging/default_rules.py`。
  - 新增 `scripts/seed_tagging_defaults.py`。
  - 新增 `TaggingRuleService.seed_default_rule_version()`。
  - 支持通过 `npm run seed:tagging-defaults` 和 `npm run dev:prepare` 初始化默认 tagging 规则。
- 打通规则切换后的待办收敛：
  - 新分类结果如果覆盖旧 bootstrap 结果，会把旧 review task 标记为 `cancelled`。
  - `review_payload.cancelled_reason = superseded_by_reclassification`。
- 修复 `/review/queue` 的 `total` 字段：
  - 返回全部匹配任务数，而不是当前页条数。
  - 新增分页回归测试，覆盖历史 `open` 与当前 `pending` 混合场景。

### 验证结果

- 真实开发库 `var/data/ptr_dev.sqlite3` 当时结果：
  - `market_classification_results = 285`
  - `market_review_tasks = 285`
  - `market_review_tasks.queue_status = pending: 285`
- 默认 tagging 基线替换 bootstrap 后的开发库结果：
  - active rule version: `tag_default_v1`
  - superseded rule version: `bootstrap_review_queue_v1`
  - 分类结果：
    - `Tagged = 153`
    - `Blocked = 132`
    - `ReviewRequired = 0`
  - review task：
    - `cancelled = 285`
    - `pending = 132`
- API 验证：
  - `/review/queue?queue_status=pending&page=1&page_size=3` 可返回任务数据。
  - `/monitoring/metrics` 中 `review_queue.pending = 285`。
- 自动化测试：
  - `python -m pytest tests/integration/test_api_review.py -q` -> `4 passed`
  - `python -m pytest tests/integration/test_api_monitoring.py tests/integration/test_api_tagging.py -q` -> `9 passed`
  - `python -m pytest tests/test_tagging_defaults.py -q` -> `3 passed`

### 当前状态

- Review Queue 空列表的后端根因已排除。
- 本机当时未启动开发服务，尚未做浏览器侧复核。

### 下一步

- 启动本地开发服务并复核 Review Queue 与 Monitoring 页面。
- 继续推进 M3 相关联调与页面验收。
