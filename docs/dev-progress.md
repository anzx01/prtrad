# 开发进度

## 2026-04-13

### 今日完成

- 继续收口昨天未完成的“先判断、再操作”页面改造：
  - `/risk` 新增系统判断层，补齐“当前优先事项”“系统建议先看这里”“当前最该解释的越限簇 / 接近门槛簇”
  - `/launch-review` 新增 Go/NoGo 判断层，补齐“当前判断”“系统建议先看这里”“当前 Go 阻塞项”
- `/launch-review` 页面完成进一步拆分，降低页级复杂度：
  - 新增 `types.ts`
  - 新增 `constants.ts`
  - 新增 `insights.ts`
  - 新增 `summary-panels.tsx`
  - 新增 `record-panels.tsx`
  - 新增 `forms-section.tsx`
- `/launch-review` 交互与文案继续收口：
  - checklist 英文化标签统一补充为中文业务解释
  - 阶段评审证据的 `report_type=stage_review:M4/M5/M6` 统一解释为中文阶段评审标题
  - Go 被阻止时，反馈直接展示中文化的门槛缺口，而不是原始 checklist label
- `/risk` 页面继续结构整理：
  - 风险判断逻辑抽到 `apps/web/app/risk/insights.ts`
  - 初始化表单状态与错误解析抽回 `constants.ts`
  - `page.tsx` 控制在 300 行附近
- 自动化脚本补齐统一入口：
  - 新增 `scripts/refresh-evidence-pack.ps1`
  - 新增 `npm run task:refresh-evidence-pack`
  - 脚本与首页一键证据包动作保持同一顺序：重算风险暴露 -> 重算长窗口校准 -> 回测 -> shadow -> 日报 -> 周报 -> `M4/M5/M6` 阶段评审
  - 为脚本补齐日志文件落盘到 `logs/`
  - 为兼容 Windows PowerShell 5.1 与仓库 UTF-8 无 BOM 约束，脚本文案使用 ASCII
- README 同步补充一键证据包脚本入口，以及 `/risk`、`/launch-review` 两个工作台的最新使用方式说明
- 完成了 DQ 健康检查与链路收口，主要包含：
  - 补齐 `market_snapshot_capture.execute` 审计 payload 的 `book_fetch_failed_tokens` 与 `created_from_source_payload`
  - 快照与 DQ 在选择 active 市场时，排除 `close_time` 已过的市场，避免“状态滞后但交易窗口已结束”的市场污染主链路
  - 为 source payload 单边报价场景补齐保守推导逻辑
  - 为真实订单簿单边报价场景补齐二元互补推导逻辑
- 200 市场同步基线最终收敛为：
  - 快照：`selected_markets=200`，`created=200`，`book_fetch_failed_tokens=0`，`created_from_source_payload=2`
  - DQ：`selected_markets=200`，`pass=0`，`warn=200`，`fail=0`

### 验证结果

- 前端与脚本：
  - `npm --workspace apps/web exec tsc -- --noEmit` -> `passed`
  - `powershell -ExecutionPolicy Bypass -File .\scripts\refresh-evidence-pack.ps1 -DryRun` -> `passed`
  - `Invoke-WebRequest http://localhost:3000/risk` -> `200`
  - `Invoke-WebRequest http://localhost:3000/launch-review` -> `200`
- DQ / 快照链路：
  - `python -m pytest tests/test_ingest_snapshot_resilience.py tests/test_dq_service.py tests/integration/test_api_dq.py -q` -> `20 passed`
  - 同步 200 市场基线最新结果：
    - `status_distribution`: `warn=200`
    - `freshness_status`: 同步检查下等价为 `fresh`
    - 当前 warning 原因分布：`REJ_DATA_STALE=200`，`REJ_DATA_ANOMALY=1`
- 审计日志验证：
  - `market_snapshot_capture.execute` payload 已包含：
    - `book_fetch_failed_tokens`
    - `created_from_source_payload`

### 当前状态

- `/risk` 已不再只是暴露表和阈值表堆叠，而是会先告诉用户“该先处理 kill-switch、越限簇，还是只是例行观察”
- `/launch-review` 已不再只靠用户自己读 checklist 推断能不能 Go，而是会先给出当前判断、阻塞项和下一步动作
- 首页一键证据包的自动化链路现在已有 `scripts/` 层统一入口，后续可脱离前端直接执行
- DQ 主链路已从“过期 active 市场导致大量 `REJ_DATA_LEAK_RISK` fail”收敛到“无 blocking fail，仅剩全量 stale warning”
- 当前最主要的 DQ 剩余问题已经从“阻断失败”变成“`source_updated_at` 整体偏老，导致 `pass=0` 但仍可出 fresh warn 批次”

### 关键判断

- 当前用户成本最大的点，已经不只是“功能有没有”，而是“系统能不能先把当前结论说清楚”；这次页面改造继续把解释前移到了页面本身
- 本轮 DQ 排障证明，之前的主要问题不是规则本身坏了，而是“过期 active 市场 + 单边盘口快照缺口”共同放大了 fail
- 在去掉这两类噪声后，当前 DQ 剩余信号更接近真实问题：上游市场元数据整体过旧
- 队列积压仍会放大“假性 stale”，后续健康检查更适合优先走同步基线或脚本化顺序执行

### 下一步

- 优先排查 `REJ_DATA_STALE` / `pass=0`：
  - 确认是本地市场目录长期未刷新，还是 Gamma 返回的 `updatedAt` 本身就长期不变
  - 评估是否需要补一轮更明确的 market sync / closed sync 健康检查
- 补一条脚本化健康检查入口（`scripts/`），把“快照 -> DQ -> summary 校验”固化为单命令，降低队列时序影响
- 继续检查还有哪些页面仍然是“字段已经有了，但系统没有先给结论”，优先考虑：
  - `/state-alerts`
  - `/calibration`

## 2026-04-12

### 今日完成

- 将首页 `/` 从静态导航页重做为“智能驾驶舱”
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
- 首页新增动作日志，解决“点了没反应”的不确定感
- 首页自动化对 SQLite 偶发 `database is locked` 增加有限次短重试
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

- `M4`：主链路可用，风险、状态机、Kill-switch、阈值维护可运行
- `M5`：回测、日报、周报、阶段评审主链路可用，首页已能把报告与阶段评审转成更易理解的入口
- `M6`：shadow、launch review、Go/NoGo 门槛可用，首页已能直接提示为什么当前不能 Go
- 智能化方向已落第一版：不再让用户先背全系统，再自己拼流程

### 验证结果

- `npm --workspace apps/web exec tsc -- --noEmit` -> `passed`
- `python -m pytest tests/integration/test_api_review.py -q` -> `7 passed`
- `Invoke-WebRequest http://localhost:3000` -> `200`
- `Invoke-WebRequest http://localhost:3000/reports` -> `200`
- `apps/web/app/review/page.tsx`、`apps/web/app/components/ApiStatus.tsx`、`README.md`、`docs/dev-progress.md` 已按 UTF-8 字节读取复核
- 最新一次 `npm run build:web` 在 Windows 下被 `apps/web/.next/trace` 文件锁阻塞，报 `EPERM`；当前 `tsc` 通过，说明本次代码改动本身未引入 TypeScript 编译错误
- 首页自动汇总数据基于本地实际 API 返回，而不是写死样例

### 关键判断

- 当前项目的主要学习成本，不再是“页面长得不够好看”，而是用户需要自己理解链路、判断卡点、手动拼动作
- 第一版智能驾驶舱已经把这件事前移到系统层处理
- 当前最大的人工瓶颈仍然是审核队列，系统会明确暴露这一点，但不会假装自动替代人工审核

### 明日优先级

1. 评估是否要把首页自动化动作进一步脚本化，沉淀为 `scripts/` 层面的统一入口
2. 继续梳理首页以外仍然“需要先学习再操作”的页面，优先处理：
   - `/launch-review`
   - `/risk`
3. 继续收口页面层的编码与渲染稳定性问题，避免再出现 hydration / 乱码 / 热更新中断带来的误判

### 风险与备注

- 当前工作树本身是脏的，已避免回滚其他已有改动
- 首页自动化虽然做了 SQLite 锁重试，但数据库本质仍是 SQLite；高频并发写入时仍需保持谨慎
- 文档乱码问题已通过整体重写规避；后续新增文档继续保持 UTF-8 中文

## 2026-04-11

### 当日完成摘要

- 修复 SQLite 历史库在 M3 迁移 `8f9a8414a637` 上的兼容问题
- 修复 calibration / resolved 样本链路，使 Calibration Units 不再长期全 0
- 修复 Review Queue `pending=0` 的运行态缺口，恢复 tagging 自动分类后可正常出数
- 修正 Launch Review 创建后容易误导的交互语义：
  - `Create Review` 成功不等于 checklist 全通过
  - `Go` 被禁用通常表示证据门槛未满足，不是创建失败
- 补齐多轮后端与前端验证，`test:m456` 通过

### 核心结论

- Calibration 全 0 的主要根因是历史 resolved 样本缺失 `final_resolution`，以及同步链路只盯 active catalog
- Review Queue 全 0 的主要根因是本地 tagging 调度未持续运行
- Launch Review “点不动”的主要根因是证据链未通过，不是按钮失效

## 2026-04-10

### 当日完成摘要

- 收口 DQ `pass=0` 问题
- 为快照抓取与 DQ 排障补齐更明确的诊断字段与脚本入口：
  - `book_fetch_failed_tokens`
  - source payload 降级快照
  - `/dq` 页面快照诊断
  - `npm run health:dq`
- 修复 `scripts/test-m456.ps1` 与 `scripts/test-risk.ps1` 的 TypeScript 调用参数问题

### 核心结论

- `pass=0` 更常见的是快照链路陈旧，不是前端页面本身坏掉
- 后续所有类似问题都应优先走“链路健康检查”，而不是先猜 UI

## 2026-04-09

### 当日完成摘要

- 修复 Review Queue 历史状态兼容问题
- 修复 tagging 分类落库与 review task 状态更新逻辑
- 补齐 tagging 默认基线种子脚本与联调用例
