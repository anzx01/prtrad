# Polymarket Tail Risk Console

用于研究、准入、风控、回测、影子验证与交易开关控制的单页控制台。

## 当前默认入口

- 唯一入口：`/`
- 旧入口如 `/markets`、`/launch-review`、`/review`、`/dq`、`/tagging`、`/monitoring`、`/risk`、`/reports` 会自动跳回 `/`
- 人工审核默认关闭
- 自动分类无法可靠放行的市场，会直接自动拦截，不再进入人工审核队列

## 当前主链路

`市场数据 -> 数据质量 DQ -> 标签分类 -> 自动拦截/放行 -> NetEV / 校准 -> 组合风控 -> 回测 -> 影子验证 -> 交易开关 / 自动上线`

## 本地启动

1. 安装依赖

```powershell
npm install
```

2. 初始化环境

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1
```

3. 升级数据库

```powershell
npm run db:upgrade
```

4. 启动开发环境

```powershell
npm run dev
```

默认地址：

- Web：`http://localhost:3001`
- API：`http://localhost:8000`
- API Docs：`http://localhost:8000/docs`

如需确认 API 是否存活：

```powershell
Invoke-RestMethod http://localhost:8000/health
```

## 常用命令

开发：

```powershell
npm run dev
npm run dev:web
npm run dev:api
npm run dev:worker
npm run dev:beat
npm run build:web
```

说明：

- 前端开发服务器默认使用 `3001`
- 如需改端口，可运行：`powershell -ExecutionPolicy Bypass -File .\scripts\dev-web.ps1 -Port 3002`
- 或先设置环境变量：`$env:WEB_PORT=3002`

数据库：

```powershell
npm run db:upgrade
npm run db:downgrade
npm run db:current
```

主链路任务：

```powershell
npm run task:market-sync
npm run task:snapshot-sync
npm run task:dq-run
npm run task:tagging-run
npm run task:refresh-evidence-pack
npm run task:trading -- -Action state
npm run task:trading -- -Action start-paper
npm run task:trading -- -Action start-live
npm run task:trading -- -Action stop
npm run task:trading -- -Action execute-next
npm run task:trading -- -Action orders
```

测试：

```powershell
npm run test:risk
npm run test:m456
npm run test:worker
python -m pytest -q
```

## 单页控制台

根路径 `/` 是唯一需要看的页面。

页面保留 3 个核心区块：

- `自动动作`
- `市场总表`
- `自动上线`

页面会自动并行汇总：

- `/monitoring/metrics`
- `/markets`
- `/risk/kill-switch?status=pending`
- `/backtests`
- `/shadow`
- `/reports`
- `/trading/state`

首页支持的自动动作：

- `刷新自动证据包`
- `仅重跑影子`
- `重新生成报告`

说明：

- 自动动作按顺序串行执行，避免并发写库
- 如需脱离前端直接执行同一套证据刷新链路，可运行 `npm run task:refresh-evidence-pack`
- 脚本日志会写入 `logs/refresh-evidence-pack-*.log`
- 市场总表默认只显示 `LIST_WHITE / 已自动放行` 的市场

## 交易开关

首页 `/` 的“自动上线”区块现在直接提供：

- `开始纸交易`
- `开始实盘`
- `立即停止`

当前实现重点先放在“能不能开、开了后会不会自动停”，并补上最小可追踪执行闭环：

- `开始纸交易` 会自动生成第一笔模拟订单
- 纸交易运行中再次点击同一个按钮，会继续再跑一笔模拟订单
- 页面会直接展示最近一笔订单的市场、状态、价格、金额和失败原因
- `开始实盘` 在配置齐全时，会通过官方 CLOB v2 SDK 发出第一笔真实订单

纸交易要求：

- 当前有可执行市场
- 没有待处理 kill-switch
- 最新回测不是 `nogo`
- 最新 shadow 不是 `block`
- 风险状态不是 `RiskOff / Frozen`

实盘在以上基础上进一步要求：

- 最新回测为 `go`
- 最新 shadow 为 `go`
- 风险状态为 `Normal`
- `TRADING_LIVE_MODE_ENABLED=true`
- `TRADING_LIVE_PRIVATE_KEY` 已配置

实盘当前接法：

- 使用官方 `py_clob_client_v2`
- 先用私钥创建或派生 L2 API 凭证
- 再按当前系统选出的最优可执行市场，发出一笔 YES 方向限价单
- 实盘下单额不再写死，而是按可用资金比例自动计算
- 系统会限制单日实盘发单次数，避免连续误发
- 挂单后会自动轮询成交状态；长时间未成交时会自动撤单
- 实盘前会先检查资金钱包的可用余额和授权额度

自动停机规则：

- 如果运行中出现待处理 kill-switch
- 或风险状态切到 `RiskOff / Frozen`
- 或最新回测 / shadow 结果转差

系统会在下一次读取交易状态时自动切回 `stopped`，并记录最后一次停止原因。

当前新增的交易接口：

- `/trading/state`
- `/trading/start`
- `/trading/stop`
- `/trading/execute-next`
- `/trading/orders`
- `/trading/orders/{order_id}`

命令行统一入口：

```powershell
npm run task:trading -- -Action state
npm run task:trading -- -Action start-paper
npm run task:trading -- -Action start-live
npm run task:trading -- -Action stop
npm run task:trading -- -Action execute-next
npm run task:trading -- -Action orders
```

相关环境变量：

- `TRADING_LIVE_MODE_ENABLED`
  - 默认值为 `false`
  - 只有确认私钥、funder 与资金钱包都配置正确后再开启
- `TRADING_DEFAULT_ORDER_SIZE`
  - 默认值为 `10`
  - 用于纸交易默认下单数量
- `TRADING_LIVE_BANKROLL_FRACTION`
  - 默认值为 `0.02`
  - 实盘按可用资金的这个比例自动计算下单额
- `TRADING_LIVE_MIN_NOTIONAL`
  - 默认值为 `5`
  - 实盘最小下单额
- `TRADING_LIVE_MAX_NOTIONAL`
  - 默认值为 `25`
  - 实盘最大下单额
- `TRADING_LIVE_DAILY_ORDER_LIMIT`
  - 默认值为 `3`
  - 单日最多允许发出的实盘单数
- `TRADING_LIVE_STATUS_POLL_ATTEMPTS`
  - 默认值为 `5`
  - 挂单后自动查单次数
- `TRADING_LIVE_STATUS_POLL_INTERVAL_SECONDS`
  - 默认值为 `2`
  - 每次自动查单之间的等待秒数
- `TRADING_LIVE_PRIVATE_KEY`
  - 实盘钱包私钥
- `TRADING_LIVE_CHAIN_ID`
  - 默认 `137`
- `TRADING_LIVE_SIGNATURE_TYPE`
  - 默认 `0`
  - 可选 `0/1/2/3`
- `TRADING_LIVE_FUNDER_ADDRESS`
  - 当签名类型不是 `0` 时必填
- `TRADING_LIVE_API_KEY`
- `TRADING_LIVE_API_SECRET`
- `TRADING_LIVE_API_PASSPHRASE`
  - 可选；如果不填，系统会尝试按私钥自动创建或派生 L2 API 凭证
- `TRADING_LIVE_USE_SERVER_TIME`
  - 默认 `true`
- `TRADING_LIVE_RETRY_ON_ERROR`
  - 默认 `true`

## Gamma API 接入约束

- `/markets`：`300 次 / 10 秒`
- `/events`：`500 次 / 10 秒`
- 所有 Gamma API 端点共享：`4000 次 / 10 秒`
- 拉全量时统一使用 `limit + offset`
- 已内置对 `429 / 500 / 502 / 503 / 504` 的指数退避重试
- 如果上游返回 `Retry-After`，优先按该值等待

## 关键文档

- 开发进度：[docs/dev-progress.md](docs/dev-progress.md)
- 环境变量：[docs/environment-variables.md](docs/environment-variables.md)
- Tagging 默认基线：[docs/tagging/default-bootstrap-v1.md](docs/tagging/default-bootstrap-v1.md)

## 协作约定

- 统一遵循仓库根目录下 `AGENTS.md`
- 文档、说明、注释默认使用中文
- 文本文件统一使用 UTF-8
- 日常开发结束前更新 `docs/dev-progress.md`
