# 开发进度

## 2026-04-13
<<<<<<< HEAD

### 今日完成

- 按上次记录继续执行 DQ 健康检查，完成了“全量快照 + 全量 DQ”复核闭环。
- 全量快照（异步）执行成功：
  - `dispatch`: `1d8ec0fc-3658-40f3-8fc7-6c244fc44b80`
  - `execute`: `17bd85f2-e789-41d8-a637-d8bba176742c`
  - 结果：`selected_markets=200`，`created=193`，`skipped_missing_order_books=7`
- 全量 DQ（异步）执行成功：
  - `dispatch`: `c2529b89-b387-4f02-8778-464a771320cb`
  - `execute`: `57cd19d0-1c5a-4cda-ae13-7637746675bf`
  - 结果：`selected_markets=200`，`pass=0`，`warn=108`，`fail=92`
- 发现并确认一个可观测性缺口：`market_snapshot_capture` 的 `execute` 审计 payload 缺少 `book_fetch_failed_tokens` 与 `created_from_source_payload`。
- 已完成最小补丁（`workers/worker/tasks/ingest.py`）：将上述两个字段写入审计 payload。
- 发现队列积压场景：`dq-run` 在队列里延迟执行会导致批次回到 `stale`（出现 `fail=200` 的假性退化）。
- 为避免被队列延迟污染结论，补充执行了“全量同步基线检查（200 市场）”收敛当日结果：
  - 快照：`selected_markets=200`，`created=193`，`book_fetch_failed_tokens=0`，`created_from_source_payload=80`
  - DQ：`selected_markets=200`，`pass=0`，`warn=108`，`fail=92`

### 验证结果

- 自动化测试：
  - `python -m pytest tests/test_ingest_snapshot_resilience.py -q` -> `3 passed`
- 审计日志验证（补丁生效后）：
  - `market_snapshot_capture.execute` payload 已包含：
    - `book_fetch_failed_tokens`
    - `created_from_source_payload`
- `/dq/summary?limit=20` 最新返回（2026-04-13）：
  - `latest_checked_at`: `2026-04-13T02:38:35`
  - `latest_snapshot_time`: `2026-04-13T02:38:28`
  - `status_distribution`: `fail=92, warn=108`
  - `snapshot_age_seconds`: `7`
  - `freshness_status`: `fresh`
  - `top_blocking_reasons`: `REJ_DATA_LEAK_RISK=83, REJ_DATA_STALE=7, REJ_DATA_INCOMPLETE=3`

### 当前状态

- 主链路可运行；DQ 当日全量基线已完成并可复验。
- `book_fetch_failed_tokens` 与 `created_from_source_payload` 已可通过审计日志直接观察。
- 当前主要风险从“全量 stale”转为“规则层 fail/warn 偏高（尤其 `REJ_DATA_LEAK_RISK`）”。
- 队列积压会放大“假性 stale”，需要与真实数据质量问题区分。

### 下一步

- 优先排查 `REJ_DATA_LEAK_RISK` Top 样本（按 market_id 聚焦规则触发明细），确认是规则阈值问题还是源数据时序问题。
- 继续重点观察：
  - `book_fetch_failed_tokens`
  - `market_snapshot_capture` 审计日志中的 execute 结果与 payload
- 补一条脚本化健康检查入口（`scripts/`），把“快照 -> DQ -> summary 校验”固化为单命令，降低队列时序影响。

## 2026-04-10
=======
>>>>>>> 8475d74df45d02c0108b05063356955b5b69a720

### 今日完成

- 继续收口昨天未完成的“先判断、再操作”页面改造：
  - `/risk` 新增系统判断层，补齐“当前优先事项”“系统建议先看这里”“当前最该解释的越限簇 / 接近门槛簇”。
  - `/launch-review` 新增 Go/NoGo 判断层，补齐“当前判断”“系统建议先看这里”“当前 Go 阻塞项”。
- `/launch-review` 页面完成进一步拆分，降低页级复杂度：
  - 新增 `types.ts`
  - 新增 `constants.ts`
  - 新增 `insights.ts`
  - 新增 `summary-panels.tsx`
  - 新增 `record-panels.tsx`
  - 新增 `forms-section.tsx`
- `/launch-review` 交互与文案继续收口：
  - checklist 英文化标签统一补充为中文业务解释，避免用户看到 `Latest backtest recommendation is go/watch` 这类原始语句还要自己翻译。
  - 阶段评审证据的 `report_type=stage_review:M4/M5/M6` 统一解释为中文阶段评审标题，避免原始持久化值直接暴露到界面。
  - Go 被阻止时，反馈会直接展示中文化的门槛缺口，而不是只显示原始 checklist label。
- `/risk` 页面继续结构整理：
  - 风险判断逻辑抽到 `apps/web/app/risk/insights.ts`
  - 初始化表单状态与错误解析抽回 `constants.ts`
  - `page.tsx` 控制在 300 行附近，降低继续扩展时的维护压力
- 自动化脚本补齐统一入口：
  - 新增 `scripts/refresh-evidence-pack.ps1`
  - 新增 `npm run task:refresh-evidence-pack`
  - 脚本与首页一键证据包动作保持同一顺序：重算风险暴露 -> 重算长窗口校准 -> 回测 -> shadow -> 日报 -> 周报 -> `M4/M5/M6` 阶段评审
  - 为脚本补齐日志文件落盘到 `logs/`
  - 为兼容 Windows PowerShell 5.1 与仓库 UTF-8 无 BOM 约束，脚本文案使用 ASCII，避免中文脚本在 `powershell -File` 下被错误按本地代码页解析
- README 同步补充一键证据包脚本入口，以及 `/risk`、`/launch-review` 两个工作台的最新使用方式说明。

### 当前状态

- `/risk` 已不再只是暴露表和阈值表堆叠，而是会先告诉用户“该先处理 kill-switch、越限簇，还是只是例行观察”。
- `/launch-review` 已不再只靠用户自己读 checklist 推断能不能 Go，而是会先给出当前判断、阻塞项和下一步动作。
- 首页一键证据包的自动化链路现在已有 `scripts/` 层统一入口，后续可脱离前端直接执行。
- README 已同步到当前产品形态，能直接说明这两页为什么要先判断、再操作。

### 验证结果

- `npm --workspace apps/web exec tsc -- --noEmit` -> `passed`
- `powershell -ExecutionPolicy Bypass -File .\scripts\refresh-evidence-pack.ps1 -DryRun` -> `passed`
- `Invoke-WebRequest http://localhost:3000/risk` -> `200`
- `Invoke-WebRequest http://localhost:3000/launch-review` -> `200`

### 关键判断

- 当前用户成本最大的点，已经不只是“功能有没有”，而是“系统能不能先把当前结论说清楚”。这次改动继续把这层解释前移到页面本身。
- `/launch-review` 原先最容易造成误判的，不是按钮能不能点，而是 checklist 与证据摘要过于原始；中文化和判断层补齐后，这类误解会明显下降。
- 首页自动化动作如果只存在前端按钮里，仍然不够稳定；补齐 `scripts/refresh-evidence-pack.ps1` 后，重复执行链路终于有了统一脚本入口。

### 明日优先级

1. 继续检查还有哪些页面仍然是“字段已经有了，但系统没有先给结论”，优先考虑：
   - `/state-alerts`
   - `/calibration`
2. 评估是否要继续把首页单步自动化动作也逐步沉淀到 `scripts/`，而不只是一键证据包。
3. 看是否需要处理 `apps/web/tsconfig.tsbuildinfo` 这类验证过程中产生的跟踪文件噪音。

### 风险与备注

- 当前工作树仍是脏的，已继续避免回滚其他已有改动。
- `apps/web/tsconfig.tsbuildinfo` 在本次 `tsc` 验证后发生更新，这是当前验证命令带出的跟踪文件变更，不影响业务代码本身。
- `scripts/refresh-evidence-pack.ps1` 当前已做 `DryRun` 自检；真实执行仍依赖本地 API 服务可用。

## 2026-04-12

### 今日完成

- 将首页 `/` 从静态导航页重做为“智能驾驶舱”。
- 首页新增自动并行汇总能力，统一读取：
  - `/monitoring/metrics`
  - `/dq/summary`
  - `/review/queue`
  - `/risk/state`
  - `/risk/exposures`
  - `/risk/kill-switch?status=pending`
  - `/calibration/units?include_inactive=true`
  - `/backtests`
  - `/shadow`
  - `/launch-review`
  - `/reports`
- 首页新增三类核心输出：
  - 系统当前判断
  - 下一步建议
  - 主链路状态与 M4/M5/M6 阶段状态
- 首页新增一键动作中心：
  - 重算风险暴露
  - 重算长窗口校准
  - 运行回测
  - 运行 shadow
  - 生成日报
  - 生成周报
  - 生成 M4/M5/M6 阶段评审
  - 一键刷新完整证据包
- 首页新增动作日志，解决“点了没反应”的不确定感。
- 首页自动化对 SQLite 偶发 `database is locked` 增加有限次短重试。
- 结构整理：
  - 新增 `apps/web/app/home/`
  - 拆分 `types.ts`
  - 拆分 `automation.ts`
  - 拆分 `summary-core.ts`
  - 拆分 `summary-readouts.ts`
  - 拆分 `summary-shared.ts`
  - 拆分 `dashboard-sections.tsx`
  - 拆分 `action-panels.tsx`
- `/reports` 页面完成二次重构：
  - 顶部新增“智能速读”，直接说明当前该先看哪份报告
  - 新增“系统建议先看这里”，把阅读顺序和原因解释清楚
  - 新增 `M4 / M5 / M6` 门槛概览，区分“没报告”和“有报告但真没过”
  - 保留归档与详情，但改成左选右读的工作台结构
  - `stage_review` 的中文解读补充为“最新回测本身是 NoGo”这类更贴近实际的解释
  - 报表前端进一步拆分为：
    - `report-dashboard.ts`
    - `report-overview.tsx`
    - `report-detail-views.tsx`
- `/review` 页面补齐审核台能力：
  - 队列页支持单条“开始审核 / 通过 / 拒绝”快捷操作
  - 队列页支持勾选、多选、全选本页、批量通过、批量拒绝、批量开始审核
  - 队列页补充“全选当前筛选 N 条”与“一键开始审核已选 / 一键通过已选 / 一键拒绝已选”
  - 后端新增 `/review/bulk-action` 批量审核接口
  - `pending/open` 任务在批量通过或拒绝时可自动领取为 `in_progress` 再完成审核
- 修复前端 hydration mismatch：
  - 定位到导航 `ApiStatus` 刷新按钮容易被浏览器扩展/翻译注入属性，导致服务端与客户端首屏不一致
  - 将刷新按钮从纯文本字符改为稳定 SVG 图标
  - 为按钮增加 `suppressHydrationWarning` 与 `translate="no"`
  - 同步清理 `ApiStatus` 组件中文乱码
- 重写并清理文档乱码：
  - `README.md`
  - `docs/dev-progress.md`
- README 进一步补充：
  - `/reports` 报表工作台的阅读方式与门槛解释
  - `/review` 审核工作台的单条/批量操作说明

### 当前状态

- `M4`：主链路可用，风险、状态机、Kill-switch、阈值维护可运行。
- `M5`：回测、日报、周报、阶段评审主链路可用，首页已能把报告与阶段评审转成更易理解的入口。
- `M6`：shadow、launch review、Go/NoGo 门槛可用，首页已能直接提示为什么当前不能 Go。
- 智能化方向已落第一版：不再让用户先背全系统，再自己拼流程。

### 验证结果

- `npm --workspace apps/web exec tsc -- --noEmit` -> `passed`
- `python -m pytest tests/integration/test_api_review.py -q` -> `7 passed`
- `Invoke-WebRequest http://localhost:3000` -> `200`
- `Invoke-WebRequest http://localhost:3000/reports` -> `200`
- `apps/web/app/review/page.tsx`、`apps/web/app/components/ApiStatus.tsx`、`README.md`、`docs/dev-progress.md` 已按 UTF-8 字节读取复核
- 最新一次 `npm run build:web` 在 Windows 下被 `apps/web/.next/trace` 文件锁阻塞，报 `EPERM`；当前 `tsc` 通过，说明本次代码改动本身未引入 TypeScript 编译错误
- 首页自动汇总数据基于本地实际 API 返回，而不是写死样例。

### 关键判断

- 当前项目的主要学习成本，不再是“页面长得不够好看”，而是用户需要自己理解链路、判断卡点、手动拼动作。
- 第一版智能驾驶舱已经把这件事前移到系统层处理。
- 当前最大的人工瓶颈仍然是审核队列，系统会明确暴露这一点，但不会假装自动替代人工审核。

### 明日优先级

1. 评估是否要把首页自动化动作进一步脚本化，沉淀为 `scripts/` 层面的统一入口。
2. 继续梳理首页以外仍然“需要先学习再操作”的页面，优先处理：
   - `/launch-review`
   - `/risk`
3. 继续收口页面层的编码与渲染稳定性问题，避免再出现 hydration / 乱码 / 热更新中断带来的误判。

### 风险与备注

- 当前工作树本身是脏的，已避免回滚其他已有改动。
- 首页自动化虽然做了 SQLite 锁重试，但数据库本质仍是 SQLite；高频并发写入时仍需保持谨慎。
- 文档乱码问题已通过整体重写规避；后续新增文档继续保持 UTF-8 中文。

## 2026-04-11

### 当日完成摘要

- 修复 SQLite 历史库在 M3 迁移 `8f9a8414a637` 上的兼容问题。
- 修复 calibration / resolved 样本链路，使 Calibration Units 不再长期全 0。
- 修复 Review Queue `pending=0` 的运行态缺口，恢复 tagging 自动分类后可正常出数。
- 修正 Launch Review 创建后容易误导的交互语义：
  - `Create Review` 成功不等于 checklist 全通过
  - `Go` 被禁用通常表示证据门槛未满足，不是创建失败
- 补齐多轮后端与前端验证，`test:m456` 通过。

### 核心结论

- Calibration 全 0 的主要根因是历史 resolved 样本缺失 `final_resolution`，以及同步链路只盯 active catalog。
- Review Queue 全 0 的主要根因是本地 tagging 调度未持续运行。
- Launch Review “点不动”的主要根因是证据链未通过，不是按钮失效。

## 2026-04-10

### 当日完成摘要

- 收口 DQ `pass=0` 问题。
- 为快照抓取与 DQ 排障补齐更明确的诊断字段与脚本入口：
  - `book_fetch_failed_tokens`
  - source payload 降级快照
  - `/dq` 页面快照诊断
  - `npm run health:dq`
- 修复 `scripts/test-m456.ps1` 与 `scripts/test-risk.ps1` 的 TypeScript 调用参数问题。

### 核心结论

- `pass=0` 更常见的是快照链路陈旧，不是前端页面本身坏掉。
- 后续所有类似问题都应优先走“链路健康检查”，而不是先猜 UI。

## 2026-04-09

### 当日完成摘要

- 修复 Review Queue 历史状态兼容问题。
- 修复 tagging 分类落库与 review task 状态更新逻辑。
- 补齐 tagging 默认基线种子脚本与联调用例。
