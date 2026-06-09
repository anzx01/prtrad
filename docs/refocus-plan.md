# Polymarket 套利验证闭环重聚焦计划

## 结论

当前项目的主链路已经具备市场接入、DQ、标签、评分、校准、NetEV、风控、回测、shadow 与上线评审等模块，但实现重心偏向“上线审批与证据包”，还没有真正回答最核心的问题：

> 当前市场里是否存在可执行的有效套利机会，以及按当前策略模拟执行后是否真的能捕获收益。

因此后续开发应优先补齐最短交易验证闭环：

`市场快照 -> NetEV 准入候选 -> 模拟开仓 -> 持仓盯市 -> 平仓/PnL -> 交易验证报告`

## 当前项目研究结果

### 已可复用的能力

- `apps/api/services/ingest/`：已有 Polymarket 市场与订单簿快照接入。
- `apps/api/services/dq/`：已有数据质量检查，能识别 stale、缺字段和异常数据。
- `apps/api/services/tagging/` 与 `apps/api/services/scoring/`：已有分类与准入前评分。
- `apps/api/services/calibration/`：已有校准单元，用于估计历史 edge。
- `apps/api/services/netev/service.py`：已有 NetEV 候选生成和 `admit/reject` 决策。
- `apps/api/services/risk/`：已有风险簇聚合和状态机，但当前暴露来源是 NetEV 候选，不是真实持仓。
- `apps/api/services/backtests/`：已有回测归档结构，但当前更像候选统计和压力折扣，不是逐快照交易路径回放。
- `apps/api/services/shadow/`：已有 shadow run，但它实际是上线前门禁检查，不是模拟交易。
- `apps/api/services/trading/` 与 `apps/api/services/execution/`：已有交易开关和纸交易订单记录，可以生成 filled 纸订单，但原本没有持仓和 PnL 跟踪。

### 核心缺口

- 原有纸交易停在订单记录，无法知道系统“模拟持有什么、何时退出、收益如何”。
- NetEV 准入后没有独立的持仓验证入口。
- 缺少 PnL 与胜率统计，无法验证策略是否捕获了 edge。
- 风控暴露应逐步从“候选暴露”迁移到“持仓暴露”。
- 前端首页和工作台缺少“当前可交易机会 / 当前模拟持仓 / 交易表现”的直接入口。

## 开发计划

### Phase 1：最小模拟交易闭环

目标：让一个 `admit` 的 NetEV 候选可以进入模拟仓位，并能随最新快照更新 PnL。

交付：

- 新增 `paper_positions` 表。
- 新增 `PaperTradingService`：
  - 从最新 `NetEVCandidate(admit)` 中选择尚未开仓的市场。
  - 以 NO 侧可执行价格模拟开仓。
  - 将已有 filled 纸交易订单同步为模拟持仓。
  - 更新开放持仓的 mark price 与 unrealized PnL。
  - 对关闭或已结算市场自动平仓。
- 新增 `/paper-trading` API：
  - `GET /paper-trading/positions`
  - `GET /paper-trading/summary`
  - `POST /paper-trading/evaluate`
  - `POST /paper-trading/mark`

验收：

- 能通过 API 从已准入候选创建模拟持仓。
- 再写入一条新快照后，持仓 PnL 会变化。
- 市场关闭或结算后，持仓会转为 closed 并记录 realized PnL。

### Phase 2：交易表现工作台

目标：前端能直接看到模拟交易闭环，而不是只看上线证据。

交付：

- 新增 `/paper-trading` 页面：
  - 当前表现摘要：开放持仓数、已平仓数、未实现 PnL、已实现 PnL、胜率。
  - 操作入口：评估准入候选、刷新盯市。
  - 开放持仓列表。
  - 已平仓交易列表。
- 导航新增“模拟交易”入口。

验收：

- 页面可加载 summary 和 positions。
- 点击评估按钮能调用后端并刷新结果。
- 页面文案聚焦交易验证，不再把 shadow/run/GoNoGo 当主叙事。

### Phase 3：验证与 e2e

目标：用自动化测试证明最小闭环真实可跑。

交付：

- 单元测试覆盖：
  - 自动开仓。
  - 重复候选不重复开仓。
  - mark-to-market 更新 PnL。
  - 市场关闭自动平仓。
- 集成测试覆盖：
  - `/paper-trading/evaluate`
  - `/paper-trading/mark`
  - `/paper-trading/summary`
  - `/paper-trading/positions`
- e2e 脚本：
  - 初始化测试数据。
  - 调用 API 完成候选准入、模拟开仓、盯市、平仓。
  - 输出关键断言结果。

验收：

- `python -m pytest tests/test_paper_trading_service.py tests/integration/test_api_paper_trading.py -q` 通过。
- `npm --workspace apps/web exec tsc -- --noEmit` 通过。
- `powershell -ExecutionPolicy Bypass -File .\scripts\e2e-paper-trading.ps1` 通过。

当前状态：

- Phase 1 已完成。
- Phase 2 已完成。
- Phase 3 已完成。

## 取舍说明

- 暂不删除已有上线评审、报告和 shadow 功能，避免破坏当前可运行链路。
- 本阶段只新增最小持仓验证层，不改真实下单、不改钱包、不处理链上结算。
- 模拟成交价格先使用 NO 侧价格：
  - 开仓优先使用 `best_ask_no`，缺失时保守回退到 `last_trade_price_no`。
  - 盯市/平仓优先使用 `best_bid_no`，缺失时回退到 `last_trade_price_no`。
- PnL 先按 NO 份额计算：
  - `unrealized_pnl = (mark_price - entry_price) * size`
  - `realized_pnl = (exit_price - entry_price) * size`
- 当前持仓层支持 YES/NO 双向标记；直接从 NetEV 候选评估时默认创建 NO 侧持仓，已有纸交易订单会按订单方向同步。
- 后续如果要支持订单簿深度滑点、部分成交、资金曲线和最大回撤，应在这个闭环验证通过后继续扩展。

## 当前优先级

1. 先证明 NetEV 准入候选可以转成模拟持仓。
2. 再证明模拟持仓能随市场价格变化产生 PnL。
3. 最后用 e2e 固化这条链路，作为后续策略迭代和真实回测增强的基线。

**更新日期：2026-06-09**
